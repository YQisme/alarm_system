from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import cv2
import threading
import queue
import time
import json
import os
import base64
import numpy as np
from datetime import datetime
from ultralytics import YOLO
from PIL import Image, ImageDraw, ImageFont
import subprocess
import signal
import re
import socket

# 获取项目根目录路径（backend/ 的父目录）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, 'frontend')
MODELS_DIR = os.path.join(BASE_DIR, 'models')
CONFIG_DIR = os.path.join(BASE_DIR, 'config')

# 确保config目录存在
os.makedirs(CONFIG_DIR, exist_ok=True)

# 检查是否为开发模式（Vite 开发服务器）
VITE_DEV_MODE = os.environ.get('VITE_DEV', 'false').lower() == 'true'
FRONTEND_DIST_DIR = os.path.join(FRONTEND_DIR, 'dist')

if VITE_DEV_MODE:
    # 开发模式：只提供 API，前端由 Vite 开发服务器提供
    app = Flask(__name__)
    # 允许所有来源的跨域请求（开发模式，支持IP访问）
    CORS(app, origins="*")  # 允许所有来源，包括IP地址
else:
    # 生产模式：提供静态文件
    app = Flask(__name__, static_folder=FRONTEND_DIST_DIR, static_url_path='')
    CORS(app)  # 允许跨域请求

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# 设置日志系统（必须在其他模块之前初始化）
from logging_config import setup_logging
backend_logger, yolo_logger, log_queue = setup_logging(BASE_DIR, socketio)

# 全局变量（必须在日志发送线程之前定义）
frame_queue = queue.Queue(maxsize=2)
stop_flag = threading.Event()

# 日志发送线程
def log_sender():
    """后台线程，将日志队列中的日志通过WebSocket发送给前端"""
    import time
    while not stop_flag.is_set():
        try:
            log_entry = log_queue.get(timeout=1)
            # 使用socketio.emit发送日志，room=None表示广播给所有连接的客户端
            socketio.emit('log', log_entry, room=None)
        except queue.Empty:
            continue
        except Exception as e:
            # 使用print避免循环依赖
            try:
                backend_logger.error(f"发送日志失败: {e}")
            except:
                print(f"发送日志失败: {e}")
            time.sleep(0.1)

# 启动日志发送线程
log_sender_thread = threading.Thread(target=log_sender, daemon=True)
log_sender_thread.start()

# GPU检测
def check_gpu_available():
    """检测GPU是否可用"""
    try:
        import torch
        if torch.cuda.is_available():
            gpu_count = torch.cuda.device_count()
            gpu_name = torch.cuda.get_device_name(0) if gpu_count > 0 else "Unknown"
            backend_logger.info(f"✅ 检测到 {gpu_count} 个GPU设备: {gpu_name}")
            return True, 0  # 返回True和设备ID
        else:
            backend_logger.warning("⚠️  未检测到CUDA GPU，将使用CPU模式")
            return False, 'cpu'
    except ImportError:
        backend_logger.warning("⚠️  PyTorch未安装，无法检测GPU，将使用CPU模式")
        return False, 'cpu'
    except Exception as e:
        backend_logger.warning(f"⚠️  GPU检测失败: {e}，将使用CPU模式")
        return False, 'cpu'

# 初始化时检测GPU
gpu_available, device = check_gpu_available()
# 多区域管理：每个区域包含 id, name, points, enabled, color
zones = []  # 区域列表，格式：[{"id": "uuid", "name": "区域1", "points": [[x,y],...], "enabled": True, "color": {"fill": [0,255,255], "border": [0,255,255]}}, ...]
next_zone_id = 1  # 下一个区域ID（用于生成唯一ID）
alarm_triggered = {}  # 记录已触发报警的跟踪ID，格式：{(track_id, class_id, zone_id): timestamp}

# 报警配置
alarm_config = {
    "debounce_time": 5.0,  # 防抖时间（秒），同一目标在此时间内只报警一次
    "detection_mode": "center",  # 检测模式："center"=中心点，"edge"=边框任意点
    "once_per_id": False,  # 相同ID是否只报警一次（True=整个生命周期只报警一次，False=允许重复报警）
    "save_event_video": True,  # 是否保存报警事件视频
    "save_event_image": True,  # 是否保存报警事件图片
    "event_video_duration": 10,  # 报警事件视频时长（秒）
    "event_save_path": os.path.join(BASE_DIR, "alarm_events")  # 报警事件保存路径
}

zones_config_file = os.path.join(CONFIG_DIR, "zones_config.json")  # 多区域配置文件
config_file = os.path.join(CONFIG_DIR, "system_config.json")  # 系统配置文件
classes_config_file = os.path.join(CONFIG_DIR, "classes_config.json")  # 类别配置文件
display_config_file = os.path.join(CONFIG_DIR, "display_config.json")  # 显示配置文件
model_classes_file = os.path.join(CONFIG_DIR, "model_classes.json")  # 模型类别映射配置文件
alarm_config_file = os.path.join(CONFIG_DIR, "alarm_config.json")  # 报警配置文件
latest_frame = None  # 最新帧
latest_results = None  # 最新检测结果
latest_annotated_frame = None  # 最新处理后的帧（包含YOLO检测结果和区域绘制）

# 录制相关变量
recording_lock = threading.Lock()  # 录制锁
is_recording = False  # 是否正在录制
recording_process = None  # ffmpeg进程对象
recording_start_time = 0  # 当前分段开始时间
recording_file_index = 0  # 文件索引（用于分割）
recording_config = {
    "save_path": os.path.join(BASE_DIR, "recordings"),  # 默认保存路径
    "segment_duration": 300  # 默认分割时长（秒），5分钟
}
recording_config_file = os.path.join(CONFIG_DIR, "recording_config.json")  # 录制配置文件

# 视频信息
video_info = {
    "width": 0,
    "height": 0,
    "fps": 0.0
}
fps_counter = {
    "frame_count": 0,
    "last_time": time.time(),
    "current_fps": 0.0
}

# 当前模型的类别映射
model_classes = []  # 英文类别名称列表
model_classes_cn = []  # 中文类别名称列表

# COCO数据集默认类别映射（80个类别）
DEFAULT_COCO_CLASSES = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat",
    "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat",
    "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "backpack",
    "umbrella", "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball",
    "kite", "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket",
    "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple",
    "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair",
    "couch", "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse",
    "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink", "refrigerator",
    "book", "clock", "vase", "scissors", "teddy bear", "hair drier", "toothbrush"
]

DEFAULT_COCO_CLASSES_CN = [
    "人", "自行车", "汽车", "摩托车", "飞机", "公交车", "火车", "卡车", "船",
    "红绿灯", "消防栓", "停止标志", "停车计时器", "长椅", "鸟", "猫",
    "狗", "马", "羊", "牛", "大象", "熊", "斑马", "长颈鹿", "背包",
    "雨伞", "手提包", "领带", "行李箱", "飞盘", "滑雪板", "滑雪板", "运动球",
    "风筝", "棒球棒", "棒球手套", "滑板", "冲浪板", "网球拍",
    "瓶子", "酒杯", "杯子", "叉子", "刀", "勺子", "碗", "香蕉", "苹果",
    "三明治", "橙子", "西兰花", "胡萝卜", "热狗", "披萨", "甜甜圈", "蛋糕", "椅子",
    "沙发", "盆栽", "床", "餐桌", "马桶", "电视", "笔记本电脑", "鼠标",
    "遥控器", "键盘", "手机", "微波炉", "烤箱", "烤面包机", "水槽", "冰箱",
    "书", "时钟", "花瓶", "剪刀", "泰迪熊", "吹风机", "牙刷"
]

# 类别配置
classes_config = {
    "enabled_classes": [0],  # 默认只启用person类（类别0）
    "custom_names": {},  # 自定义中文名称，格式：{class_id: "自定义名称"}
    "confidence_thresholds": {}  # 自定义置信度阈值，格式：{class_id: 0.5}，默认0.25
}

# 显示配置
display_config = {
    "font_size": 16,  # 字体大小
    "box_color": [0, 255, 0],  # 边框颜色 (BGR格式)
    "box_thickness": 2,  # 边框粗细
    "text_color": [0, 0, 0],  # 文字颜色 (RGB格式)
    "use_chinese": True,  # 是否使用中文显示（False时使用英文，性能更好）
    "zone_fill_color": [0, 255, 255],  # 报警区域填充颜色 (BGR格式)
    "zone_border_color": [0, 255, 255],  # 报警区域边框颜色 (BGR格式)
    "zone_fill_alpha": 0.3  # 报警区域填充透明度 (0.0-1.0)
}

# 模型和视频路径管理
model_lock = threading.Lock()  # 模型访问锁
video_lock = threading.Lock()  # 视频路径访问锁
current_model_name = "yolo26m_640_int8.engine"  # 当前模型文件名
video_path = "rtsp://admin:scyzkj123456@192.168.1.2:554/h264/ch1/main/av_stream"  # 视频路径
camera_ip = ""  # 摄像头IP地址
camera_status = "unknown"  # 摄像头状态：online/offline/unknown
camera_status_lock = threading.Lock()  # 摄像头状态锁
camera_check_interval = 5  # 摄像头检测间隔（秒）
camera_last_status = "unknown"  # 上次检测到的状态，用于判断状态变化
camera_offline_alarm_triggered = {}  # 摄像头离线报警记录，用于防抖
model = None  # 模型对象，延迟加载

# 从RTSP URL中提取IP地址
def extract_ip_from_rtsp(rtsp_url):
    """从RTSP URL中提取IP地址"""
    try:
        # 匹配 rtsp://username:password@ip:port/path 格式
        match = re.search(r'@([\d.]+):', rtsp_url)
        if match:
            return match.group(1)
        # 匹配 rtsp://ip:port/path 格式
        match = re.search(r'rtsp://([\d.]+):', rtsp_url)
        if match:
            return match.group(1)
    except Exception as e:
        backend_logger.error(f"提取IP地址失败: {e}")
    return None

# 检测IP是否在线（使用ping）
def ping_ip(ip, timeout=2):
    """使用ping检测IP是否在线"""
    try:
        # 使用ping命令检测（Linux系统）
        result = subprocess.run(
            ['ping', '-c', '1', '-W', str(timeout), ip],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout + 1
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return False
    except Exception as e:
        backend_logger.error(f"Ping检测失败: {e}")
        return False

# 触发摄像头离线报警
def trigger_camera_offline_alarm(ip):
    """触发摄像头离线报警"""
    global camera_offline_alarm_triggered, alarm_config
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    alarm_key = f"camera_offline_{ip}"
    
    # 使用防抖时间机制，避免频繁报警
    debounce_time = alarm_config.get('debounce_time', 5.0)
    if alarm_key in camera_offline_alarm_triggered:
        # 检查是否在防抖时间内
        if time.time() - camera_offline_alarm_triggered[alarm_key] < debounce_time:
            return False
    camera_offline_alarm_triggered[alarm_key] = time.time()
    
    alarm_data = {
        "time": current_time,
        "track_id": -1,
        "class_id": None,
        "class_name_cn": "摄像头离线",
        "object_name": "摄像头离线",
        "zone_id": "system",
        "zone_name": "系统报警",
        "position": {"x": 0, "y": 0},
        "event_video": None,
        "event_image": None,
        "camera_ip": ip
    }
    
    # 通过WebSocket发送报警信息
    socketio.emit('alarm', alarm_data)
    backend_logger.warning(f"⚠️  摄像头离线报警！IP: {ip}, 时间: {current_time}")
    return True

# 摄像头状态检测线程
def camera_status_checker():
    """定期检测摄像头在线状态"""
    global camera_status, camera_ip, camera_last_status, camera_check_interval
    
    while not stop_flag.is_set():
        try:
            with camera_status_lock:
                current_ip = camera_ip
                current_interval = camera_check_interval
            
            # 在锁外提取IP，避免长时间持有锁
            if not current_ip:
                # 如果没有配置IP，尝试从RTSP URL中提取
                with video_lock:
                    current_rtsp = video_path
                extracted_ip = extract_ip_from_rtsp(current_rtsp)
                if extracted_ip:
                    # 使用锁保护IP的更新
                    with camera_status_lock:
                        camera_ip = extracted_ip
                        current_ip = extracted_ip
            
            if current_ip:
                is_online = ping_ip(current_ip, timeout=2)
                previous_status = camera_last_status
                with camera_status_lock:
                    camera_status = "online" if is_online else "offline"
                    camera_last_status = camera_status
                
                # 如果状态从在线变为离线，触发报警
                if previous_status == "online" and camera_status == "offline":
                    trigger_camera_offline_alarm(current_ip)
            else:
                with camera_status_lock:
                    camera_status = "unknown"
                    camera_last_status = "unknown"
        except Exception as e:
            backend_logger.error(f"摄像头状态检测异常: {e}")
            with camera_status_lock:
                camera_status = "unknown"
                camera_last_status = "unknown"
        
        # 使用配置的检测间隔
        time.sleep(current_interval)

# 加载系统配置
def load_system_config():
    """从配置文件加载系统配置"""
    global current_model_name, video_path, camera_ip, model
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                if 'model' in config:
                    current_model_name = config['model']
                if 'video_url' in config:
                    video_path = config['video_url']
                if 'camera_ip' in config:
                    camera_ip = config['camera_ip']
                backend_logger.info(f"已从 {config_file} 加载系统配置")
        except Exception as e:
            backend_logger.error(f"加载系统配置文件失败: {e}")
    
    # 如果没有配置IP，尝试从RTSP URL中提取
    if not camera_ip:
        extracted_ip = extract_ip_from_rtsp(video_path)
        if extracted_ip:
            camera_ip = extracted_ip
            backend_logger.info(f"从RTSP URL中提取IP地址: {camera_ip}")
    
    # 加载模型
    load_model()

def save_system_config():
    """保存系统配置到文件"""
    global camera_ip, camera_check_interval
    config = {
        "model": current_model_name,
        "video_url": video_path,
        "camera_ip": camera_ip,
        "camera_check_interval": camera_check_interval
    }
    try:
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        backend_logger.info(f"系统配置已保存到 {config_file}")
    except Exception as e:
        backend_logger.error(f"保存系统配置失败: {e}")

def load_model_classes(model_name):
    """加载模型对应的类别配置"""
    global model_classes, model_classes_cn
    
    if not os.path.exists(model_classes_file):
        # 如果配置文件不存在，创建默认配置
        default_config = {
            "default": {
                "classes_en": DEFAULT_COCO_CLASSES,
                "classes_cn": DEFAULT_COCO_CLASSES_CN
            }
        }
        try:
            with open(model_classes_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            backend_logger.info(f"已创建默认类别配置文件: {model_classes_file}")
        except Exception as e:
            backend_logger.error(f"创建类别配置文件失败: {e}")
    
    try:
        with open(model_classes_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 优先查找模型名称匹配的配置
        if model_name in config:
            model_classes = config[model_name].get("classes_en", DEFAULT_COCO_CLASSES)
            model_classes_cn = config[model_name].get("classes_cn", DEFAULT_COCO_CLASSES_CN)
            backend_logger.info(f"已加载模型 {model_name} 的类别配置，共 {len(model_classes)} 个类别")
        elif "default" in config:
            # 使用默认配置
            model_classes = config["default"].get("classes_en", DEFAULT_COCO_CLASSES)
            model_classes_cn = config["default"].get("classes_cn", DEFAULT_COCO_CLASSES_CN)
            backend_logger.info(f"使用默认类别配置，共 {len(model_classes)} 个类别")
        else:
            # 如果都没有，使用硬编码的默认值
            model_classes = DEFAULT_COCO_CLASSES
            model_classes_cn = DEFAULT_COCO_CLASSES_CN
            backend_logger.info(f"使用内置默认类别配置，共 {len(model_classes)} 个类别")
    except Exception as e:
        backend_logger.error(f"加载类别配置失败: {e}，使用默认配置")
        model_classes = DEFAULT_COCO_CLASSES
        model_classes_cn = DEFAULT_COCO_CLASSES_CN

def load_model():
    """加载YOLO模型"""
    global model, current_model_name, device, gpu_available
    
    # 重新检测GPU（可能在运行时发生变化）
    gpu_available, device = check_gpu_available()
    
    model_path = os.path.join(MODELS_DIR, current_model_name)
    if not os.path.exists(model_path):
        backend_logger.warning(f"模型文件 {model_path} 不存在，使用默认模型")
        current_model_name = "yolo26m_640_int8.engine"
        model_path = os.path.join(MODELS_DIR, current_model_name)
    
    try:
        with model_lock:
            if model is not None:
                # 释放旧模型（如果有的话）
                del model
            
            # YOLO初始化时不接受device参数，设备在使用时指定
            model = YOLO(model_path)
            if gpu_available:
                backend_logger.info(f"模型已加载: {current_model_name} (将使用GPU模式)")
            else:
                backend_logger.info(f"模型已加载: {current_model_name} (将使用CPU模式)")
        
        # 加载模型对应的类别配置
        load_model_classes(current_model_name)
    except Exception as e:
        backend_logger.error(f"加载模型失败: {e}")
        raise

# 类别配置管理
def load_classes_config():
    """从配置文件加载类别配置"""
    global classes_config
    if os.path.exists(classes_config_file):
        try:
            with open(classes_config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                if 'enabled_classes' in config:
                    classes_config['enabled_classes'] = config['enabled_classes']
                if 'custom_names' in config:
                    classes_config['custom_names'] = config['custom_names']
                if 'confidence_thresholds' in config:
                    classes_config['confidence_thresholds'] = config['confidence_thresholds']
                backend_logger.info(f"已从 {classes_config_file} 加载类别配置")
        except Exception as e:
            backend_logger.error(f"加载类别配置文件失败: {e}")

def save_classes_config():
    """保存类别配置到文件"""
    try:
        with open(classes_config_file, 'w', encoding='utf-8') as f:
            json.dump(classes_config, f, indent=2, ensure_ascii=False)
        backend_logger.info(f"类别配置已保存到 {classes_config_file}")
    except Exception as e:
        backend_logger.error(f"保存类别配置失败: {e}")

def get_class_name_cn(class_id):
    """获取类别的中文名称（优先使用自定义名称）"""
    if class_id in classes_config['custom_names']:
        return classes_config['custom_names'][class_id]
    elif class_id < len(model_classes_cn):
        return model_classes_cn[class_id]
    else:
        return f"类别{class_id}"

def is_class_enabled(class_id):
    """检查类别是否启用"""
    return class_id in classes_config['enabled_classes']

def get_class_confidence_threshold(class_id):
    """获取类别的置信度阈值（默认0.25）"""
    return classes_config['confidence_thresholds'].get(class_id, 0.25)

def check_confidence(class_id, confidence):
    """检查置信度是否满足阈值要求"""
    threshold = get_class_confidence_threshold(class_id)
    return confidence >= threshold

# 显示配置管理
def load_display_config():
    """从配置文件加载显示配置"""
    global display_config
    if os.path.exists(display_config_file):
        try:
            with open(display_config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                if 'font_size' in config:
                    display_config['font_size'] = config['font_size']
                if 'box_color' in config:
                    display_config['box_color'] = config['box_color']
                if 'box_thickness' in config:
                    display_config['box_thickness'] = config['box_thickness']
                if 'text_color' in config:
                    display_config['text_color'] = config['text_color']
                if 'use_chinese' in config:
                    display_config['use_chinese'] = config['use_chinese']
                if 'zone_fill_color' in config:
                    display_config['zone_fill_color'] = config['zone_fill_color']
                if 'zone_border_color' in config:
                    display_config['zone_border_color'] = config['zone_border_color']
                if 'zone_fill_alpha' in config:
                    display_config['zone_fill_alpha'] = config['zone_fill_alpha']
                backend_logger.info(f"已从 {display_config_file} 加载显示配置")
                backend_logger.info(f"报警区域颜色配置: fill={display_config.get('zone_fill_color')}, border={display_config.get('zone_border_color')}, alpha={display_config.get('zone_fill_alpha')}")
        except Exception as e:
            backend_logger.error(f"加载显示配置文件失败: {e}")
    else:
        # 如果配置文件不存在，确保默认值存在
        if 'zone_fill_color' not in display_config:
            display_config['zone_fill_color'] = [0, 255, 255]
        if 'zone_border_color' not in display_config:
            display_config['zone_border_color'] = [0, 255, 255]
        if 'zone_fill_alpha' not in display_config:
            display_config['zone_fill_alpha'] = 0.3

def save_display_config():
    """保存显示配置到文件"""
    try:
        # 确保所有必需的字段都存在（使用默认值）
        config_to_save = display_config.copy()
        if 'zone_fill_color' not in config_to_save:
            config_to_save['zone_fill_color'] = [0, 255, 255]  # BGR格式，默认青色
        if 'zone_border_color' not in config_to_save:
            config_to_save['zone_border_color'] = [0, 255, 255]  # BGR格式，默认青色
        if 'zone_fill_alpha' not in config_to_save:
            config_to_save['zone_fill_alpha'] = 0.3
        
        with open(display_config_file, 'w', encoding='utf-8') as f:
            json.dump(config_to_save, f, indent=2, ensure_ascii=False)
        backend_logger.info(f"显示配置已保存到 {display_config_file}")
    except Exception as e:
        backend_logger.error(f"保存显示配置失败: {e}")

# 报警配置管理
def load_alarm_config():
    """从配置文件加载报警配置"""
    global alarm_config
    if os.path.exists(alarm_config_file):
        try:
            with open(alarm_config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                if 'debounce_time' in config:
                    alarm_config['debounce_time'] = float(config['debounce_time'])
                if 'detection_mode' in config:
                    alarm_config['detection_mode'] = config['detection_mode']
                if 'once_per_id' in config:
                    alarm_config['once_per_id'] = bool(config['once_per_id'])
                if 'save_event_video' in config:
                    alarm_config['save_event_video'] = bool(config['save_event_video'])
                if 'save_event_image' in config:
                    alarm_config['save_event_image'] = bool(config['save_event_image'])
                if 'event_video_duration' in config:
                    alarm_config['event_video_duration'] = int(config['event_video_duration'])
                if 'event_save_path' in config:
                    alarm_config['event_save_path'] = config['event_save_path']
                backend_logger.info(f"已从 {alarm_config_file} 加载报警配置")
        except Exception as e:
            backend_logger.error(f"加载报警配置文件失败: {e}")
    
    # 确保事件保存路径存在
    if alarm_config.get('save_event_video') or alarm_config.get('save_event_image'):
        event_path = alarm_config.get('event_save_path', os.path.join(BASE_DIR, "alarm_events"))
        os.makedirs(event_path, exist_ok=True)
        os.makedirs(os.path.join(event_path, "videos"), exist_ok=True)
        os.makedirs(os.path.join(event_path, "images"), exist_ok=True)

def save_alarm_config():
    """保存报警配置到文件"""
    try:
        with open(alarm_config_file, 'w', encoding='utf-8') as f:
            json.dump(alarm_config, f, indent=2, ensure_ascii=False)
        backend_logger.info(f"报警配置已保存到 {alarm_config_file}")
    except Exception as e:
        backend_logger.error(f"保存报警配置失败: {e}")

# 初始化加载配置和模型
load_system_config()
load_classes_config()
load_display_config()
load_alarm_config()


def is_point_in_polygon(point, polygon):
    """检测点是否在多边形内"""
    if len(polygon) < 3:
        return False
    polygon_array = np.array(polygon, np.int32)
    result = cv2.pointPolygonTest(polygon_array, tuple(point), False)
    return result >= 0  # >=0 表示在内部或边界上

def is_bbox_in_polygon(bbox, polygon):
    """检测检测框是否与多边形有交集（边框任意点模式）"""
    if len(polygon) < 3:
        return False
    x1, y1, x2, y2 = bbox
    polygon_array = np.array(polygon, np.int32)
    
    # 检查检测框的四个角点
    corners = [
        [x1, y1],  # 左上角
        [x2, y1],  # 右上角
        [x2, y2],  # 右下角
        [x1, y2]   # 左下角
    ]
    
    # 如果任意一个角点在多边形内，则认为有交集
    for corner in corners:
        if is_point_in_polygon(corner, polygon):
            return True
    
    # 检查检测框的中心点
    center = [(x1 + x2) / 2, (y1 + y2) / 2]
    if is_point_in_polygon(center, polygon):
        return True
    
    return False


def save_alarm_event_video(track_id, zone_id, zone_name, class_id, class_name_cn, bbox_center):
    """保存报警事件视频（使用ffmpeg从RTSP流录制指定时长）"""
    try:
        if not alarm_config.get('save_event_video', True):
            return None
        
        event_path = alarm_config.get('event_save_path', os.path.join(BASE_DIR, "alarm_events"))
        video_dir = os.path.join(event_path, "videos")
        os.makedirs(video_dir, exist_ok=True)
        
        duration = alarm_config.get('event_video_duration', 10)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        object_name = class_name_cn if class_name_cn else f"class_{class_id}"
        # 清理文件名中的非法字符
        safe_zone_name = zone_name.replace('/', '_').replace('\\', '_').replace(':', '_')
        safe_object_name = object_name.replace('/', '_').replace('\\', '_').replace(':', '_')
        filename = f"alarm_{timestamp}_ID{track_id}_{safe_object_name}_{safe_zone_name}.mp4"
        filepath = os.path.join(video_dir, filename)
        
        # 使用ffmpeg从RTSP流录制指定时长的视频
        # 使用重新编码方式，确保兼容性
        # 先尝试使用copy，如果失败再使用编码（但这里直接使用编码以确保兼容性）
        ffmpeg_cmd = [
            'ffmpeg',
            '-rtsp_transport', 'tcp',
            '-i', video_path,
            '-t', str(duration),  # 录制时长
            '-c:v', 'libx264',  # 视频编码器
            '-preset', 'ultrafast',  # 最快编码速度
            '-crf', '23',  # 质量参数（18-28，23是默认值）
            '-an',  # 禁用音频（很多RTSP流没有音频）
            '-movflags', '+faststart',  # 优化网络播放
            '-y',  # 覆盖已存在的文件
            '-loglevel', 'error',  # 只显示错误信息
            filepath
        ]
        
        # 在后台线程中执行，避免阻塞
        def record_video():
            try:
                process = subprocess.Popen(
                    ffmpeg_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdin=subprocess.DEVNULL  # 避免等待stdin输入
                )
                stdout, stderr = process.communicate(timeout=duration + 10)  # 等待录制完成
                
                if process.returncode == 0:
                    # 检查文件是否真的存在且有内容
                    if os.path.exists(filepath) and os.path.getsize(filepath) > 1000:  # 至少1KB
                        backend_logger.info(f"报警事件视频已保存: {filename} ({os.path.getsize(filepath)} bytes)")
                    else:
                        backend_logger.error(f"报警事件视频文件异常: {filename} (大小: {os.path.getsize(filepath) if os.path.exists(filepath) else 0} bytes)")
                else:
                    error_msg = stderr.decode('utf-8', errors='ignore') if stderr else "未知错误"
                    backend_logger.error(f"ffmpeg录制失败 (返回码: {process.returncode}): {error_msg}")
                    # 删除失败的文件
                    if os.path.exists(filepath):
                        try:
                            os.remove(filepath)
                        except:
                            pass
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                backend_logger.warning(f"报警事件视频录制超时: {filename}")
                # 删除不完整的文件
                if os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                    except:
                        pass
            except Exception as e:
                backend_logger.error(f"保存报警事件视频失败: {e}")
                # 删除失败的文件
                if os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                    except:
                        pass
        
        threading.Thread(target=record_video, daemon=True).start()
        return filename
        
    except Exception as e:
        backend_logger.error(f"保存报警事件视频失败: {e}")
        return None


def save_alarm_event_image(track_id, zone_id, zone_name, class_id, class_name_cn, bbox_center):
    """保存报警事件图片"""
    try:
        if not alarm_config.get('save_event_image', True):
            return None
        
        if latest_annotated_frame is None:
            return None
        
        event_path = alarm_config.get('event_save_path', os.path.join(BASE_DIR, "alarm_events"))
        image_dir = os.path.join(event_path, "images")
        os.makedirs(image_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        object_name = class_name_cn if class_name_cn else f"class_{class_id}"
        # 清理文件名中的非法字符
        safe_zone_name = zone_name.replace('/', '_').replace('\\', '_').replace(':', '_')
        safe_object_name = object_name.replace('/', '_').replace('\\', '_').replace(':', '_')
        filename = f"alarm_{timestamp}_ID{track_id}_{safe_object_name}_{safe_zone_name}.jpg"
        filepath = os.path.join(image_dir, filename)
        
        # 保存处理后的帧（包含检测框和区域）
        frame = latest_annotated_frame.copy()
        
        # 在图片上添加报警信息文字
        pil_image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_image)
        
        # 加载字体
        font_size = display_config.get('font_size', 16)
        font = None
        font_paths = [
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
            "/usr/share/fonts/truetype/arphic/uming.ttc",
            "/usr/share/fonts/truetype/arphic/ukai.ttc",
            "/System/Library/Fonts/PingFang.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ]
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    font = ImageFont.truetype(font_path, font_size)
                    break
                except:
                    continue
        if font is None:
            font = ImageFont.load_default()
        
        # 绘制报警信息
        info_text = f"报警时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n目标: {object_name} (ID: {track_id})\n区域: {safe_zone_name}"
        bbox = draw.textbbox((0, 0), info_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        padding = 10
        
        # 绘制文字背景
        bg_x1 = 10
        bg_y1 = 10
        bg_x2 = bg_x1 + text_width + padding * 2
        bg_y2 = bg_y1 + text_height + padding * 2
        draw.rectangle([bg_x1, bg_y1, bg_x2, bg_y2], fill=(0, 0, 0, 200))
        
        # 绘制文字
        draw.text((bg_x1 + padding, bg_y1 + padding), info_text, fill=(255, 255, 255), font=font)
        
        # 转换回OpenCV格式并保存
        frame_rgb = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        cv2.imwrite(filepath, frame_rgb, [cv2.IMWRITE_JPEG_QUALITY, 95])
        
        backend_logger.info(f"报警事件图片已保存: {filename}")
        return filename
        
    except Exception as e:
        backend_logger.error(f"保存报警事件图片失败: {e}")
        return None


def trigger_alarm(track_id, bbox_center, zone_id, zone_name, class_id=None, class_name_cn=None):
    """触发报警"""
    global alarm_triggered, alarm_config
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 使用 (track_id, class_id, zone_id) 作为唯一标识，避免不同类别和区域的相同ID冲突
    alarm_key = (track_id, class_id if class_id is not None else -1, zone_id)
    
    # 检查是否已报警过（如果配置了相同ID只报警一次）
    once_per_id = alarm_config.get('once_per_id', False)
    if once_per_id:
        # 如果已报警过，直接返回（整个生命周期只报警一次）
        if alarm_key in alarm_triggered:
            return False
        # 记录已报警（使用特殊标记，表示永久报警过）
        alarm_triggered[alarm_key] = float('inf')
    else:
        # 使用防抖时间机制
        debounce_time = alarm_config.get('debounce_time', 5.0)
        if alarm_key in alarm_triggered:
            # 检查是否是永久标记（inf表示已永久报警过）
            if alarm_triggered[alarm_key] == float('inf'):
                return False
            # 检查是否在防抖时间内
            if time.time() - alarm_triggered[alarm_key] < debounce_time:
                return False
        alarm_triggered[alarm_key] = time.time()
    
    object_name = class_name_cn if class_name_cn else "对象"
    
    # 保存报警事件（视频和图片）
    event_video_filename = None
    event_image_filename = None
    if alarm_config.get('save_event_video', True):
        event_video_filename = save_alarm_event_video(track_id, zone_id, zone_name, class_id, class_name_cn, bbox_center)
    if alarm_config.get('save_event_image', True):
        event_image_filename = save_alarm_event_image(track_id, zone_id, zone_name, class_id, class_name_cn, bbox_center)
    
    alarm_data = {
        "time": current_time,
        "track_id": track_id,
        "class_id": class_id,
        "class_name_cn": class_name_cn,
        "object_name": object_name,
        "zone_id": zone_id,
        "zone_name": zone_name,
        "position": {"x": float(bbox_center[0]), "y": float(bbox_center[1])},
        "event_video": event_video_filename,
        "event_image": event_image_filename
    }
    
    # 通过WebSocket发送报警信息
    socketio.emit('alarm', alarm_data)
    backend_logger.warning(f"⚠️  报警！{object_name}进入监控区域【{zone_name}】！时间: {current_time}, ID: {track_id}")
    return True


def video_reader():
    """在单独线程中读取视频帧"""
    cap = None
    retry_count = 0
    max_retries = 5
    current_video_path = None
    
    while not stop_flag.is_set():
        # 检查视频路径是否改变
        with video_lock:
            if current_video_path != video_path:
                if cap is not None:
                    cap.release()
                    cap = None
                current_video_path = video_path
        
        if cap is None or not cap.isOpened():
            backend_logger.info(f"正在连接视频流: {current_video_path}")
            cap = cv2.VideoCapture(current_video_path)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            if not cap.isOpened():
                retry_count += 1
                if retry_count >= max_retries:
                    backend_logger.warning(f"无法连接视频流，已重试 {max_retries} 次")
                    time.sleep(5)
                    retry_count = 0
                else:
                    time.sleep(2)
                continue
            else:
                retry_count = 0
                # 获取视频分辨率
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                video_info['width'] = width
                video_info['height'] = height
                video_info['fps'] = fps if fps > 0 else 0.0
                backend_logger.info(f"视频流连接成功 - 分辨率: {width}x{height}, FPS: {fps:.2f}")
        
        success, frame = cap.read()
        if not success:
            backend_logger.warning("读取视频帧失败，尝试重新连接...")
            cap.release()
            cap = None
            time.sleep(1)
            continue
        
        # 只保留最新帧
        if not frame_queue.empty():
            try:
                frame_queue.get_nowait()
            except queue.Empty:
                pass
        
        try:
            frame_queue.put(frame, block=False)
        except queue.Full:
            pass
    
    if cap is not None:
        cap.release()
    backend_logger.info("视频读取线程已停止")


def detection_worker():
    """检测工作线程"""
    global latest_frame, latest_results, latest_annotated_frame, zones, fps_counter, display_config
    
    while not stop_flag.is_set():
        try:
            # 从队列获取最新帧
            got_new_frame = False
            try:
                frame = frame_queue.get(timeout=1)
                got_new_frame = True  # 成功从队列获取新帧
            except queue.Empty:
                # 如果没有新帧，使用上一帧（如果有）
                if latest_frame is not None:
                    frame = latest_frame.copy()
                    got_new_frame = False  # 这是重复帧，不计数
                else:
                    time.sleep(0.1)
                    continue
            
            latest_frame = frame.copy()
            
            # YOLO跟踪检测（使用锁保护模型访问）
            try:
                with model_lock:
                    if model is None:
                        time.sleep(0.1)
                        continue
                    # 在使用时指定设备，stream=True返回生成器，需要获取第一个结果
                    results_generator = model.track(frame, persist=True, stream=True, device=device,classes=[0])
                    results = next(results_generator)  # 从生成器中获取结果
                latest_results = results
            except Exception as e:
                yolo_logger.error(f"YOLO检测错误: {e}")
                time.sleep(0.1)
                continue
            
            # 检测对象是否进入任何启用的区域
            enabled_zones = [z for z in zones if z.get('enabled', True) and len(z.get('points', [])) >= 3]
            if enabled_zones:
                if results.boxes is not None and len(results.boxes) > 0:
                    boxes = results.boxes
                    track_ids = results.boxes.id
                    
                    if track_ids is not None:
                        for i, box in enumerate(boxes):
                            cls_id = int(box.cls[0])
                            
                            # 只检测启用的类别
                            if is_class_enabled(cls_id):
                                conf = float(box.conf[0])
                                # 检查置信度是否满足阈值要求
                                if check_confidence(cls_id, conf):
                                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                                    bbox_center = [(x1 + x2) / 2, (y1 + y2) / 2]
                                    
                                    # 检测是否进入任何启用的区域
                                    detection_mode = alarm_config.get('detection_mode', 'center')
                                    for zone in enabled_zones:
                                        zone_points = zone.get('points', [])
                                        if len(zone_points) < 3:
                                            continue
                                        
                                    in_zone = False
                                    if detection_mode == 'center':
                                        # 中心点模式：检查中心点是否在多边形内
                                        in_zone = is_point_in_polygon(bbox_center, zone_points)
                                    elif detection_mode == 'edge':
                                        # 边框任意点模式：检查检测框是否与多边形有交集
                                        in_zone = is_bbox_in_polygon([x1, y1, x2, y2], zone_points)
                                    
                                    if in_zone:
                                        track_id = int(track_ids[i])
                                        class_name_cn = get_class_name_cn(cls_id)
                                        zone_id = zone.get('id', 'unknown')
                                        zone_name = zone.get('name', '未知区域')
                                        trigger_alarm(track_id, bbox_center, zone_id, zone_name, cls_id, class_name_cn)
                                        break  # 只对第一个匹配的区域报警
            
            # 手动绘制检测框（只显示启用的类别）
            annotated_frame = frame.copy()
            
            if results.boxes is not None and len(results.boxes) > 0:
                boxes = results.boxes
                track_ids = results.boxes.id
                
                if track_ids is not None:
                    for i, box in enumerate(boxes):
                        cls_id = int(box.cls[0])
                        
                        # 只绘制启用的类别
                        if is_class_enabled(cls_id):
                            conf = float(box.conf[0])
                            # 检查置信度是否满足阈值要求
                            if check_confidence(cls_id, conf):
                                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                                track_id = int(track_ids[i])
                                bbox_center = [(x1 + x2) / 2, (y1 + y2) / 2]
                                
                                # 判断是否在任何一个启用的报警区域内
                                in_zone = False
                                enabled_zones = [z for z in zones if z.get('enabled', True) and len(z.get('points', [])) >= 3]
                                if enabled_zones:
                                    detection_mode = alarm_config.get('detection_mode', 'center')
                                    for zone in enabled_zones:
                                        zone_points = zone.get('points', [])
                                        if len(zone_points) < 3:
                                            continue
                                    if detection_mode == 'center':
                                        # 中心点模式：检查中心点是否在多边形内
                                            if is_point_in_polygon(bbox_center, zone_points):
                                                in_zone = True
                                                break
                                    elif detection_mode == 'edge':
                                        # 边框任意点模式：检查检测框是否与多边形有交集
                                            if is_bbox_in_polygon([x1, y1, x2, y2], zone_points):
                                                in_zone = True
                                                break
                                
                                # 绘制检测框（在区域内用红色，否则用配置的颜色）
                                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                                if in_zone:
                                    # 在报警区域内：使用红色 (BGR格式: 0, 0, 255)
                                    box_color = (0, 0, 255)
                                    # 文字颜色也使用红色 (RGB格式: 255, 0, 0)
                                    text_color_rgb = (255, 0, 0)
                                else:
                                    # 不在区域内：使用配置的默认颜色
                                    box_color = tuple(display_config['box_color'])
                                    # 文字颜色使用配置的颜色
                                    text_color_rgb = tuple(display_config['text_color'])
                                box_thickness = display_config['box_thickness']
                                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), box_color, box_thickness)
                                
                                # 获取类别名称并绘制文字
                                if display_config.get('use_chinese', True):
                                    # 使用中文显示
                                    class_name = get_class_name_cn(cls_id)
                                    label = f"{class_name} {conf:.2f} ID:{track_id}"
                                    
                                    # 使用PIL绘制中文文字（OpenCV不支持中文）
                                    # 将OpenCV图像转换为PIL图像
                                    pil_image = Image.fromarray(cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB))
                                    draw = ImageDraw.Draw(pil_image)
                                    
                                    # 尝试加载中文字体
                                    font = None
                                    font_paths = [
                                        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",  # 文泉驿微米黑
                                        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",   # 文泉驿正黑
                                        "/usr/share/fonts/truetype/arphic/uming.ttc",      # AR PL UMing
                                        "/usr/share/fonts/truetype/arphic/ukai.ttc",      # AR PL UKai
                                        "/System/Library/Fonts/PingFang.ttc",              # macOS
                                        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf" # 备用
                                    ]
                                    
                                    font_size = display_config['font_size']
                                    for font_path in font_paths:
                                        if os.path.exists(font_path):
                                            try:
                                                font = ImageFont.truetype(font_path, font_size)
                                                break
                                            except:
                                                continue
                                    
                                    if font is None:
                                        font = ImageFont.load_default()
                                    
                                    # 计算文字大小
                                    bbox = draw.textbbox((0, 0), label, font=font)
                                    text_width = bbox[2] - bbox[0]
                                    text_height = bbox[3] - bbox[1]
                                    
                                    # 在PIL图像上绘制文字（根据是否在报警区域内使用不同颜色）
                                    draw.text((x1 + 2, y1 - text_height - 3), label, fill=text_color_rgb, font=font)
                                    
                                    # 将PIL图像转换回OpenCV格式
                                    annotated_frame = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
                                else:
                                    # 使用英文显示（OpenCV原生，性能更好）
                                    class_name_en = model_classes[cls_id] if cls_id < len(model_classes) else f"class_{cls_id}"
                                    label = f"{class_name_en} {conf:.2f} ID:{track_id}"
                                    
                                    # 使用OpenCV绘制文字（需要转换为BGR格式）
                                    text_color_bgr = (text_color_rgb[2], text_color_rgb[1], text_color_rgb[0])  # RGB转BGR
                                    font_scale = display_config['font_size'] / 20.0  # 调整字体大小比例
                                    cv2.putText(annotated_frame, label, (x1 + 2, y1 - 5), 
                                               cv2.FONT_HERSHEY_SIMPLEX, font_scale, text_color_bgr, 2)
            
            # 绘制所有启用的区域
            enabled_zones = [z for z in zones if z.get('enabled', True) and len(z.get('points', [])) >= 3]
            for zone in enabled_zones:
                zone_points = zone.get('points', [])
                if len(zone_points) < 3:
                    continue
                
                polygon_array = np.array(zone_points, np.int32)
                
                # 获取区域的颜色配置（优先使用区域自己的颜色，否则使用全局配置）
                zone_color = zone.get('color', {})
                zone_border_color_list = zone_color.get('border', display_config.get('zone_border_color', [0, 255, 255]))
                zone_fill_color_list = zone_color.get('fill', display_config.get('zone_fill_color', [0, 255, 255]))
                zone_fill_alpha = display_config.get('zone_fill_alpha', 0.3)
                
                # 确保颜色值是整数元组（BGR格式）
                zone_border_color = (int(zone_border_color_list[0]), int(zone_border_color_list[1]), int(zone_border_color_list[2]))
                zone_fill_color = (int(zone_fill_color_list[0]), int(zone_fill_color_list[1]), int(zone_fill_color_list[2]))
                
                # 先绘制填充
                overlay = annotated_frame.copy()
                cv2.fillPoly(overlay, [polygon_array], zone_fill_color)
                cv2.addWeighted(overlay, zone_fill_alpha, annotated_frame, 1.0 - zone_fill_alpha, 0, annotated_frame)
                
                # 再绘制边框（在填充之后，确保边框可见）
                cv2.polylines(annotated_frame, [polygon_array], True, zone_border_color, 3)
                
                # 绘制区域名称（在区域中心）
                if zone.get('name'):
                    zone_name = zone.get('name', '')
                    # 计算区域中心点
                    center_x = int(np.mean([p[0] for p in zone_points]))
                    center_y = int(np.mean([p[1] for p in zone_points]))
                    # 使用PIL绘制中文文字
                    pil_image = Image.fromarray(cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB))
                    draw = ImageDraw.Draw(pil_image)
                    font_size = display_config['font_size']
                    font = None
                    font_paths = [
                        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
                        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
                        "/usr/share/fonts/truetype/arphic/uming.ttc",
                        "/usr/share/fonts/truetype/arphic/ukai.ttc",
                        "/System/Library/Fonts/PingFang.ttc",
                        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
                    ]
                    for font_path in font_paths:
                        if os.path.exists(font_path):
                            try:
                                font = ImageFont.truetype(font_path, font_size)
                                break
                            except:
                                continue
                    if font is None:
                        font = ImageFont.load_default()
                    
                    # 绘制文字背景（半透明黑色）
                    bbox = draw.textbbox((0, 0), zone_name, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]
                    padding = 5
                    bg_x1 = center_x - text_width // 2 - padding
                    bg_y1 = center_y - text_height // 2 - padding
                    bg_x2 = center_x + text_width // 2 + padding
                    bg_y2 = center_y + text_height // 2 + padding
                    draw.rectangle([bg_x1, bg_y1, bg_x2, bg_y2], fill=(0, 0, 0, 180))
                    
                    # 绘制文字（使用边框颜色的RGB版本）
                    text_color_rgb = (zone_border_color_list[2], zone_border_color_list[1], zone_border_color_list[0])  # BGR转RGB
                    draw.text((center_x - text_width // 2, center_y - text_height // 2), zone_name, 
                             fill=text_color_rgb, font=font)
                    annotated_frame = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            
            # 保存处理后的帧（用于MJPEG流）
            latest_annotated_frame = annotated_frame.copy()
            
            # 编码为JPEG
            _, buffer = cv2.imencode('.jpg', annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            frame_base64 = base64.b64encode(buffer).decode('utf-8')
            
            # 计算帧率（只计算新帧，不计算重复帧）
            if got_new_frame:
                fps_counter["frame_count"] += 1
                current_time = time.time()
                elapsed = current_time - fps_counter["last_time"]
                if elapsed >= 1.0:  # 每秒更新一次帧率
                    fps_counter["current_fps"] = fps_counter["frame_count"] / elapsed
                    fps_counter["frame_count"] = 0
                    fps_counter["last_time"] = current_time
            
            # 准备检测数据
            detection_data = {
                "frame": f"data:image/jpeg;base64,{frame_base64}",
                "zones": zones,  # 发送所有区域（包括禁用的）
                "detections": [],
                "fps": round(fps_counter["current_fps"], 2),
                "resolution": {
                    "width": video_info["width"],
                    "height": video_info["height"]
                }
            }
            
            # 添加检测框信息（只包含启用的类别）
            if results[0].boxes is not None and len(results[0].boxes) > 0:
                boxes = results[0].boxes
                track_ids = results[0].boxes.id
                
                if track_ids is not None:
                    for i, box in enumerate(boxes):
                        cls_id = int(box.cls[0])
                        
                        # 只处理启用的类别
                        if is_class_enabled(cls_id):
                            conf = float(box.conf[0])
                            # 检查置信度是否满足阈值要求
                            if check_confidence(cls_id, conf):
                                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                                track_id = int(track_ids[i])
                                bbox_center = [(x1 + x2) / 2, (y1 + y2) / 2]
                                
                                # 检查是否在任何一个启用的区域内
                                in_zone = False
                                zone_id = None
                                enabled_zones = [z for z in zones if z.get('enabled', True) and len(z.get('points', [])) >= 3]
                                if enabled_zones:
                                    detection_mode = alarm_config.get('detection_mode', 'center')
                                    for zone in enabled_zones:
                                        zone_points = zone.get('points', [])
                                        if len(zone_points) < 3:
                                            continue
                                        if detection_mode == 'center':
                                            if is_point_in_polygon(bbox_center, zone_points):
                                                in_zone = True
                                                zone_id = zone.get('id')
                                                break
                                        elif detection_mode == 'edge':
                                            if is_bbox_in_polygon([x1, y1, x2, y2], zone_points):
                                                in_zone = True
                                                zone_id = zone.get('id')
                                                break
                                
                                detection_data["detections"].append({
                                    "id": track_id,
                                    "class_id": cls_id,
                                    "class_name": model_classes[cls_id] if cls_id < len(model_classes) else f"class_{cls_id}",
                                    "class_name_cn": get_class_name_cn(cls_id),
                                    "bbox": [float(x1), float(y1), float(x2), float(y2)],
                                    "center": {"x": float(bbox_center[0]), "y": float(bbox_center[1])},
                                    "confidence": conf,
                                    "in_zone": in_zone,
                                    "zone_id": zone_id
                                })
            
            # 通过WebSocket发送给所有连接的客户端
            socketio.emit('frame', detection_data)
            
        except queue.Empty:
            continue
        except Exception as e:
            backend_logger.error(f"检测错误: {e}")
            time.sleep(0.1)


# 启动视频读取线程
reader_thread = threading.Thread(target=video_reader, daemon=True)
reader_thread.start()

# 启动检测线程
detection_thread = threading.Thread(target=detection_worker, daemon=True)
detection_thread.start()

# 启动摄像头状态检测线程
camera_status_thread = threading.Thread(target=camera_status_checker, daemon=True)
camera_status_thread.start()

# MJPEG视频流生成器（不经过YOLO处理）
def generate_raw_video_stream():
    """生成原始RTSP视频流的MJPEG流"""
    global latest_frame
    
    while not stop_flag.is_set():
        try:
            # 获取最新帧
            if latest_frame is not None:
                frame = latest_frame.copy()
                
                # 编码为JPEG
                success, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                if success:
                    frame_bytes = buffer.tobytes()
                    # 生成MJPEG格式的帧
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            
            # 控制发送频率（约30fps）
            time.sleep(1.0 / 30.0)
            
        except Exception as e:
            backend_logger.error(f"原始视频MJPEG流生成错误: {e}")
            time.sleep(0.1)


# MJPEG视频流生成器（经过YOLO处理）
def generate_processed_video_stream():
    """生成经过YOLO处理的视频流的MJPEG流"""
    global latest_annotated_frame
    
    while not stop_flag.is_set():
        try:
            # 获取最新处理后的帧
            if latest_annotated_frame is not None:
                frame = latest_annotated_frame.copy()
                
                # 编码为JPEG
                success, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                if success:
                    frame_bytes = buffer.tobytes()
                    # 生成MJPEG格式的帧
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            
            # 控制发送频率（约30fps）
            time.sleep(1.0 / 30.0)
            
        except Exception as e:
            backend_logger.error(f"处理后视频MJPEG流生成错误: {e}")
            time.sleep(0.1)


def load_zones_config():
    """从配置文件加载多区域配置"""
    global zones, next_zone_id
    if os.path.exists(zones_config_file):
        try:
            with open(zones_config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                zones = config.get("zones", [])
                # 确保每个区域都有必需的字段
                for zone in zones:
                    if 'id' not in zone:
                        zone['id'] = f"zone_{next_zone_id}"
                        next_zone_id += 1
                    if 'name' not in zone:
                        zone['name'] = f"区域{next_zone_id}"
                    if 'enabled' not in zone:
                        zone['enabled'] = True
                    if 'color' not in zone:
                        zone['color'] = {
                            "fill": [0, 255, 255],
                            "border": [0, 255, 255]
                        }
                # 更新next_zone_id
                if zones:
                    max_id = max([int(z.get('id', '0').split('_')[-1]) if z.get('id', '').startswith('zone_') else 0 for z in zones], default=0)
                    next_zone_id = max_id + 1
                backend_logger.info(f"已从 {zones_config_file} 加载 {len(zones)} 个区域")
                return True
        except Exception as e:
            backend_logger.error(f"加载区域配置文件失败: {e}")
    return False


def save_zones_config():
    """保存多区域配置到文件"""
    global zones
    config = {"zones": zones}
    try:
        with open(zones_config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        backend_logger.info(f"多区域配置已保存到 {zones_config_file}")
    except Exception as e:
        backend_logger.error(f"保存区域配置失败: {e}")


# 加载已保存的区域配置
load_zones_config()

# 录制配置管理
def load_recording_config():
    """从配置文件加载录制配置"""
    global recording_config
    if os.path.exists(recording_config_file):
        try:
            with open(recording_config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                if 'save_path' in config:
                    recording_config['save_path'] = config['save_path']
                if 'segment_duration' in config:
                    recording_config['segment_duration'] = int(config['segment_duration'])
                backend_logger.info(f"已从 {recording_config_file} 加载录制配置")
        except Exception as e:
            backend_logger.error(f"加载录制配置文件失败: {e}")
    else:
        # 确保默认保存路径存在
        os.makedirs(recording_config['save_path'], exist_ok=True)

def save_recording_config():
    """保存录制配置到文件"""
    try:
        with open(recording_config_file, 'w', encoding='utf-8') as f:
            json.dump(recording_config, f, indent=2, ensure_ascii=False)
        backend_logger.info(f"录制配置已保存到 {recording_config_file}")
    except Exception as e:
        backend_logger.error(f"保存录制配置失败: {e}")

# 加载录制配置
load_recording_config()

# 录制管理函数
def start_recording():
    """开始录制RTSP流（使用ffmpeg直接录制，不经过编解码）"""
    global is_recording, recording_process, recording_start_time, recording_file_index, video_path
    
    with recording_lock:
        if is_recording:
            return {"success": False, "message": "已经在录制中"}
        
        try:
            # 确保保存路径存在
            save_path = recording_config['save_path']
            os.makedirs(save_path, exist_ok=True)
            
            # 使用ffmpeg直接录制RTSP流，使用copy模式避免重新编码
            # -c copy: 直接复制流，不进行编解码（最快）
            # -f segment: 分段录制
            # -segment_time: 每段时长（秒）
            # -segment_format mp4: 输出格式
            # -reset_timestamps 1: 重置时间戳
            # -strftime 1: 使用时间戳命名
            segment_duration = recording_config['segment_duration']
            
            # 生成输出文件名模板（带时间戳和索引）
            output_template = os.path.join(save_path, "recording_%Y%m%d_%H%M%S_%04d.mp4")
            
            ffmpeg_cmd = [
                'ffmpeg',
                '-rtsp_transport', 'tcp',  # 使用TCP传输，更稳定
                '-i', video_path,  # 输入RTSP流
                '-c', 'copy',  # 直接复制，不编解码
                '-f', 'segment',  # 分段模式
                '-segment_time', str(segment_duration),  # 每段时长
                '-segment_format', 'mp4',  # 输出格式
                '-reset_timestamps', '1',  # 重置时间戳
                '-strftime', '1',  # 使用时间戳
                '-segment_atclocktime', '1',  # 按时钟时间分割
                output_template
            ]
            
            # 启动ffmpeg进程
            recording_process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE
            )
            
            is_recording = True
            recording_start_time = time.time()
            recording_file_index = 0
            
            backend_logger.info(f"开始录制RTSP流到: {save_path}, 分段时长: {segment_duration}秒")
            return {"success": True, "message": "录制已开始", "save_path": save_path}
            
        except FileNotFoundError:
            backend_logger.error("ffmpeg未找到，请确保已安装ffmpeg")
            return {"success": False, "message": "ffmpeg未安装，请先安装ffmpeg"}
        except Exception as e:
            backend_logger.error(f"启动录制失败: {e}")
            return {"success": False, "message": f"启动录制失败: {str(e)}"}

def stop_recording():
    """停止录制"""
    global is_recording, recording_process
    
    with recording_lock:
        if not is_recording:
            return {"success": False, "message": "当前没有在录制"}
        
        try:
            if recording_process:
                # 发送'q'给ffmpeg以正常结束录制
                try:
                    recording_process.stdin.write(b'q\n')
                    recording_process.stdin.flush()
                except:
                    pass
                
                # 等待进程结束（最多等待5秒）
                try:
                    recording_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # 如果5秒内没有结束，强制终止
                    recording_process.terminate()
                    try:
                        recording_process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        recording_process.kill()
                
                recording_process = None
            
            is_recording = False
            backend_logger.info("录制已停止")
            return {"success": True, "message": "录制已停止"}
            
        except Exception as e:
            backend_logger.error(f"停止录制失败: {e}")
            is_recording = False
            recording_process = None
            return {"success": False, "message": f"停止录制失败: {str(e)}"}

def get_recording_status():
    """获取录制状态"""
    global is_recording, recording_start_time, recording_config
    
    with recording_lock:
        status = {
            "is_recording": is_recording,
            "save_path": recording_config['save_path'],
            "segment_duration": recording_config['segment_duration']
        }
        
        if is_recording:
            elapsed = time.time() - recording_start_time
            status["elapsed_time"] = int(elapsed)
            status["current_segment_time"] = int(elapsed % recording_config['segment_duration'])
        
        return status


# 前端页面路由
@app.route('/')
def index():
    """返回前端页面"""
    if VITE_DEV_MODE:
        # 开发模式：重定向到 Vite 开发服务器
        from flask import redirect, request
        # 获取请求的主机名，保持协议和端口
        frontend_url = os.environ.get('VITE_FRONTEND_URL', f"http://{request.host.split(':')[0]}:5173")
        return redirect(frontend_url)
    else:
        # 生产模式：提供构建后的静态文件
        if os.path.exists(os.path.join(FRONTEND_DIST_DIR, 'index.html')):
            return send_from_directory(FRONTEND_DIST_DIR, 'index.html')
        else:
            return send_from_directory(FRONTEND_DIR, 'index.html')


# REST API 路由 - 多区域管理
@app.route('/api/zones', methods=['GET'])
def get_zones():
    """获取所有区域"""
    return jsonify({
        "zones": zones,
        "count": len(zones)
    })


@app.route('/api/zones', methods=['POST'])
def create_zone():
    """创建新区域"""
    global zones, next_zone_id
    
    data = request.json
    points = data.get('points', [])
    name = data.get('name', f'区域{next_zone_id}')
    enabled = data.get('enabled', True)
    color = data.get('color', {
        "fill": [0, 255, 255],
        "border": [0, 255, 255]
    })
    
    if len(points) < 3:
        return jsonify({"success": False, "message": "至少需要3个顶点"}), 400
    
    # 生成唯一ID
    zone_id = f"zone_{next_zone_id}"
    next_zone_id += 1
    
    new_zone = {
        "id": zone_id,
        "name": name,
        "points": points,
        "enabled": enabled,
        "color": color
    }
    
    zones.append(new_zone)
    save_zones_config()
    
    return jsonify({
        "success": True,
        "message": "区域已创建",
        "zone": new_zone
    })


@app.route('/api/zones/<zone_id>', methods=['GET'])
def get_zone(zone_id):
    """获取指定区域"""
    zone = next((z for z in zones if z.get('id') == zone_id), None)
    if zone:
        return jsonify({"success": True, "zone": zone})
    else:
        return jsonify({"success": False, "message": "区域不存在"}), 404


@app.route('/api/zones/<zone_id>', methods=['PUT'])
def update_zone(zone_id):
    """更新区域"""
    global zones
    
    zone = next((z for z in zones if z.get('id') == zone_id), None)
    if not zone:
        return jsonify({"success": False, "message": "区域不存在"}), 404
    
    data = request.json
    
    # 更新区域属性
    if 'name' in data:
        zone['name'] = data['name']
    if 'points' in data:
        points = data['points']
        if len(points) < 3:
            return jsonify({"success": False, "message": "至少需要3个顶点"}), 400
        zone['points'] = points
    if 'enabled' in data:
        zone['enabled'] = bool(data['enabled'])
    if 'color' in data:
        zone['color'] = data['color']
    
    save_zones_config()
    
    return jsonify({
        "success": True,
        "message": "区域已更新",
        "zone": zone
    })


@app.route('/api/zones/<zone_id>', methods=['DELETE'])
def delete_zone(zone_id):
    """删除区域"""
    global zones, alarm_triggered
    
    zone = next((z for z in zones if z.get('id') == zone_id), None)
    if not zone:
        return jsonify({"success": False, "message": "区域不存在"}), 404
    
    zones = [z for z in zones if z.get('id') != zone_id]
    
    # 清理该区域的报警记录
    alarm_triggered = {k: v for k, v in alarm_triggered.items() if k[2] != zone_id}
    
    save_zones_config()
    
    return jsonify({
        "success": True,
        "message": "区域已删除"
    })


@app.route('/api/zones/<zone_id>/rename', methods=['POST'])
def rename_zone(zone_id):
    """重命名区域"""
    global zones
    
    zone = next((z for z in zones if z.get('id') == zone_id), None)
    if not zone:
        return jsonify({"success": False, "message": "区域不存在"}), 404
    
    data = request.json
    new_name = data.get('name', '')
    
    if not new_name or not new_name.strip():
        return jsonify({"success": False, "message": "区域名称不能为空"}), 400
    
    zone['name'] = new_name.strip()
    save_zones_config()
    
    return jsonify({
        "success": True,
        "message": "区域已重命名",
        "zone": zone
    })


@app.route('/api/status', methods=['GET'])
def get_status():
    """获取系统状态"""
    global gpu_available, device
    # 重新检测GPU状态
    gpu_available, device = check_gpu_available()
    
    enabled_zones_count = len([z for z in zones if z.get('enabled', True)])
    
    return jsonify({
        "video_connected": not frame_queue.empty() or latest_frame is not None,
        "zones_count": len(zones),
        "enabled_zones_count": enabled_zones_count,
        "current_model": current_model_name,
        "video_url": video_path,
        "gpu_available": gpu_available,
        "device": str(device)
    })


@app.route('/api/models', methods=['GET'])
def get_models():
    """获取可用的模型列表"""
    try:
        models = []
        if os.path.exists(MODELS_DIR):
            for filename in os.listdir(MODELS_DIR):
                if filename.endswith(('.engine', '.pt', '.onnx')):
                    filepath = os.path.join(MODELS_DIR, filename)
                    file_size = os.path.getsize(filepath)
                    models.append({
                        "name": filename,
                        "size": file_size,
                        "size_mb": round(file_size / (1024 * 1024), 2),
                        "current": filename == current_model_name
                    })
        models.sort(key=lambda x: x['name'])
        return jsonify({"models": models, "current": current_model_name})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/model', methods=['POST'])
def set_model():
    """切换模型"""
    global current_model_name, model
    
    data = request.json
    model_name = data.get('model')
    
    if not model_name:
        return jsonify({"success": False, "message": "未指定模型名称"}), 400
    
    model_path = os.path.join(MODELS_DIR, model_name)
    if not os.path.exists(model_path):
        return jsonify({"success": False, "message": f"模型文件不存在: {model_name}"}), 404
    
    try:
        old_model_name = current_model_name
        current_model_name = model_name
        load_model()
        save_system_config()
        return jsonify({
            "success": True,
            "message": f"模型已切换: {old_model_name} -> {model_name}",
            "current_model": current_model_name
        })
    except Exception as e:
        current_model_name = old_model_name
        return jsonify({"success": False, "message": f"切换模型失败: {str(e)}"}), 500


@app.route('/api/video', methods=['GET'])
def get_video():
    """获取当前视频URL和摄像头状态"""
    with video_lock:
        video_url = video_path
    with camera_status_lock:
        status = camera_status
        ip = camera_ip
        interval = camera_check_interval
    
    return jsonify({
        "video_url": video_url,
        "camera_ip": ip,
        "camera_status": status,
        "camera_check_interval": interval
    })


@app.route('/api/video', methods=['POST'])
def set_video():
    """设置视频URL、摄像头IP和检测间隔"""
    global video_path, camera_ip, camera_check_interval
    
    data = request.json
    new_video_url = data.get('video_url')
    new_camera_ip = data.get('camera_ip', '')
    new_check_interval = data.get('camera_check_interval')
    
    if not new_video_url:
        return jsonify({"success": False, "message": "未指定视频URL"}), 400
    
    try:
        with video_lock:
            video_path = new_video_url
        
        # 使用锁保护IP和间隔的修改，避免与检测线程冲突
        with camera_status_lock:
            # 处理摄像头IP：如果请求中明确提供了camera_ip字段，使用提供的值（即使是空字符串）
            # 否则从RTSP URL中提取
            if 'camera_ip' in data:
                # 明确提供了IP字段，使用提供的值（允许为空字符串）
                camera_ip = new_camera_ip.strip() if new_camera_ip else ""
            else:
                # 没有提供IP字段，从RTSP URL中提取
                extracted_ip = extract_ip_from_rtsp(new_video_url)
                if extracted_ip:
                    camera_ip = extracted_ip
                else:
                    camera_ip = ""
            
            # 更新检测间隔
            if new_check_interval is not None:
                interval = int(new_check_interval)
                if interval < 1:
                    interval = 1  # 最小1秒
                camera_check_interval = interval
        
        save_system_config()
        
        # 立即检测一次状态（在锁外执行ping，避免阻塞）
        if camera_ip:
            is_online = ping_ip(camera_ip, timeout=2)
            with camera_status_lock:
                camera_status = "online" if is_online else "offline"
                camera_last_status = camera_status
        
        return jsonify({
            "success": True,
            "message": "视频配置已更新",
            "video_url": video_path,
            "camera_ip": camera_ip,
            "camera_status": camera_status,
            "camera_check_interval": camera_check_interval
        })
    except Exception as e:
        return jsonify({"success": False, "message": f"设置视频配置失败: {str(e)}"}), 500


@app.route('/api/classes', methods=['GET'])
def get_classes():
    """获取所有类别信息"""
    try:
        classes_list = []
        for i in range(len(model_classes)):
            classes_list.append({
                "id": i,
                "name_en": model_classes[i],
                "name_cn": get_class_name_cn(i),
                "enabled": is_class_enabled(i),
                "custom": i in classes_config['custom_names'],
                "confidence_threshold": get_class_confidence_threshold(i)
            })
        return jsonify({
            "classes": classes_list,
            "enabled_classes": classes_config['enabled_classes'],
            "custom_names": classes_config['custom_names'],
            "confidence_thresholds": classes_config['confidence_thresholds']
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/classes/enabled', methods=['POST'])
def set_enabled_classes():
    """设置启用的类别"""
    global classes_config
    
    data = request.json
    enabled_classes = data.get('enabled_classes')
    
    if enabled_classes is None:
        return jsonify({"success": False, "message": "未指定启用的类别"}), 400
    
    # 验证类别ID是否有效
    if not isinstance(enabled_classes, list):
        return jsonify({"success": False, "message": "启用的类别必须是列表"}), 400
    
    try:
        # 确保所有ID都是整数且在有效范围内
        enabled_classes = [int(cid) for cid in enabled_classes if 0 <= int(cid) < len(model_classes)]
        classes_config['enabled_classes'] = enabled_classes
        save_classes_config()
        return jsonify({
            "success": True,
            "message": f"已启用 {len(enabled_classes)} 个类别",
            "enabled_classes": enabled_classes
        })
    except Exception as e:
        return jsonify({"success": False, "message": f"设置失败: {str(e)}"}), 500


@app.route('/api/classes/custom-name', methods=['POST'])
def set_custom_name():
    """设置自定义中文名称"""
    global classes_config
    
    data = request.json
    class_id = data.get('class_id')
    custom_name = data.get('custom_name')
    
    if class_id is None:
        return jsonify({"success": False, "message": "未指定类别ID"}), 400
    
    if class_id < 0 or class_id >= len(model_classes):
        return jsonify({"success": False, "message": "无效的类别ID"}), 400
    
    try:
        class_id = int(class_id)
        if custom_name and custom_name.strip():
            classes_config['custom_names'][class_id] = custom_name.strip()
        else:
            # 如果名称为空，删除自定义名称
            classes_config['custom_names'].pop(class_id, None)
        
        save_classes_config()
        return jsonify({
            "success": True,
            "message": f"类别 {class_id} 的自定义名称已更新",
            "class_id": class_id,
            "custom_name": classes_config['custom_names'].get(class_id)
        })
    except Exception as e:
        return jsonify({"success": False, "message": f"设置失败: {str(e)}"}), 500


@app.route('/api/classes/confidence', methods=['POST'])
def set_confidence_threshold():
    """设置自定义置信度阈值"""
    global classes_config
    
    data = request.json
    class_id = data.get('class_id')
    confidence_threshold = data.get('confidence_threshold')
    
    if class_id is None:
        return jsonify({"success": False, "message": "未指定类别ID"}), 400
    
    if class_id < 0 or class_id >= len(model_classes):
        return jsonify({"success": False, "message": "无效的类别ID"}), 400
    
    if confidence_threshold is None:
        return jsonify({"success": False, "message": "未指定置信度阈值"}), 400
    
    try:
        class_id = int(class_id)
        confidence_threshold = float(confidence_threshold)
        
        # 验证置信度阈值范围（0-1）
        if confidence_threshold < 0 or confidence_threshold > 1:
            return jsonify({"success": False, "message": "置信度阈值必须在0-1之间"}), 400
        
        classes_config['confidence_thresholds'][class_id] = confidence_threshold
        save_classes_config()
        return jsonify({
            "success": True,
            "message": f"类别 {class_id} 的置信度阈值已更新为 {confidence_threshold:.2f}",
            "class_id": class_id,
            "confidence_threshold": confidence_threshold
        })
    except ValueError:
        return jsonify({"success": False, "message": "置信度阈值必须是数字"}), 400
    except Exception as e:
        return jsonify({"success": False, "message": f"设置失败: {str(e)}"}), 500


@app.route('/api/display', methods=['GET'])
def get_display_config():
    """获取显示配置"""
    # 返回给前端时，需要将BGR转换为RGB
    config = display_config.copy()
    if 'box_color' in config:
        # BGR -> RGB 转换
        bgr_color = config['box_color']
        config['box_color'] = [bgr_color[2], bgr_color[1], bgr_color[0]]
    if 'zone_fill_color' in config:
        # BGR -> RGB 转换
        bgr_color = config['zone_fill_color']
        config['zone_fill_color'] = [bgr_color[2], bgr_color[1], bgr_color[0]]
    if 'zone_border_color' in config:
        # BGR -> RGB 转换
        bgr_color = config['zone_border_color']
        config['zone_border_color'] = [bgr_color[2], bgr_color[1], bgr_color[0]]
    return jsonify(config)


@app.route('/api/display', methods=['POST'])
def set_display_config():
    """设置显示配置"""
    global display_config
    
    data = request.json
    
    try:
        if 'font_size' in data:
            font_size = int(data['font_size'])
            if font_size < 8 or font_size > 72:
                return jsonify({"success": False, "message": "字体大小必须在8-72之间"}), 400
            display_config['font_size'] = font_size
        
        if 'box_color' in data:
            box_color = data['box_color']
            if not isinstance(box_color, list) or len(box_color) != 3:
                return jsonify({"success": False, "message": "边框颜色必须是RGB格式的数组，如[0,255,0]"}), 400
            if not all(0 <= c <= 255 for c in box_color):
                return jsonify({"success": False, "message": "颜色值必须在0-255之间"}), 400
            # 前端发送的是RGB格式，需要转换为BGR格式（OpenCV使用BGR）
            display_config['box_color'] = [box_color[2], box_color[1], box_color[0]]  # RGB -> BGR
        
        if 'box_thickness' in data:
            box_thickness = int(data['box_thickness'])
            if box_thickness < 1 or box_thickness > 10:
                return jsonify({"success": False, "message": "边框粗细必须在1-10之间"}), 400
            display_config['box_thickness'] = box_thickness
        
        if 'text_color' in data:
            text_color = data['text_color']
            if not isinstance(text_color, list) or len(text_color) != 3:
                return jsonify({"success": False, "message": "文字颜色必须是RGB格式的数组，如[0,0,0]"}), 400
            if not all(0 <= c <= 255 for c in text_color):
                return jsonify({"success": False, "message": "颜色值必须在0-255之间"}), 400
            display_config['text_color'] = text_color
        
        if 'use_chinese' in data:
            use_chinese = data['use_chinese']
            if not isinstance(use_chinese, bool):
                return jsonify({"success": False, "message": "use_chinese必须是布尔值"}), 400
            display_config['use_chinese'] = use_chinese
        
        if 'zone_fill_color' in data:
            zone_fill_color = data['zone_fill_color']
            if not isinstance(zone_fill_color, list) or len(zone_fill_color) != 3:
                return jsonify({"success": False, "message": "报警区域填充颜色必须是RGB格式的数组，如[0,255,255]"}), 400
            if not all(0 <= c <= 255 for c in zone_fill_color):
                return jsonify({"success": False, "message": "颜色值必须在0-255之间"}), 400
            # 前端发送的是RGB格式，需要转换为BGR格式（OpenCV使用BGR）
            display_config['zone_fill_color'] = [int(zone_fill_color[2]), int(zone_fill_color[1]), int(zone_fill_color[0])]  # RGB -> BGR
            backend_logger.info(f"报警区域填充颜色已更新: RGB={zone_fill_color} -> BGR={display_config['zone_fill_color']}")
        
        if 'zone_border_color' in data:
            zone_border_color = data['zone_border_color']
            if not isinstance(zone_border_color, list) or len(zone_border_color) != 3:
                return jsonify({"success": False, "message": "报警区域边框颜色必须是RGB格式的数组，如[0,255,255]"}), 400
            if not all(0 <= c <= 255 for c in zone_border_color):
                return jsonify({"success": False, "message": "颜色值必须在0-255之间"}), 400
            # 前端发送的是RGB格式，需要转换为BGR格式（OpenCV使用BGR）
            display_config['zone_border_color'] = [int(zone_border_color[2]), int(zone_border_color[1]), int(zone_border_color[0])]  # RGB -> BGR
            backend_logger.info(f"报警区域边框颜色已更新: RGB={zone_border_color} -> BGR={display_config['zone_border_color']}")
        
        if 'zone_fill_alpha' in data:
            zone_fill_alpha = float(data['zone_fill_alpha'])
            if zone_fill_alpha < 0.0 or zone_fill_alpha > 1.0:
                return jsonify({"success": False, "message": "透明度必须在0.0-1.0之间"}), 400
            display_config['zone_fill_alpha'] = zone_fill_alpha
            backend_logger.info(f"报警区域填充透明度已更新: {zone_fill_alpha}")
        
        save_display_config()
        
        # 返回给前端时，需要将BGR转换为RGB
        response_config = display_config.copy()
        if 'box_color' in response_config:
            # BGR -> RGB 转换
            bgr_color = response_config['box_color']
            response_config['box_color'] = [bgr_color[2], bgr_color[1], bgr_color[0]]
        if 'zone_fill_color' in response_config:
            # BGR -> RGB 转换
            bgr_color = response_config['zone_fill_color']
            response_config['zone_fill_color'] = [bgr_color[2], bgr_color[1], bgr_color[0]]
        if 'zone_border_color' in response_config:
            # BGR -> RGB 转换
            bgr_color = response_config['zone_border_color']
            response_config['zone_border_color'] = [bgr_color[2], bgr_color[1], bgr_color[0]]
        
        return jsonify({
            "success": True,
            "message": "显示配置已更新",
            "config": response_config
        })
    except ValueError:
        return jsonify({"success": False, "message": "参数格式错误"}), 400
    except Exception as e:
        return jsonify({"success": False, "message": f"设置失败: {str(e)}"}), 500


# WebSocket 事件
@socketio.on('connect')
def handle_connect():
    """客户端连接"""
    print(f"客户端已连接: {request.sid}")
    emit('connected', {'message': '已连接到服务器'})


@socketio.on('disconnect')
def handle_disconnect():
    """客户端断开连接"""
    backend_logger.info(f"客户端已断开: {request.sid}")


@app.route('/api/video/stream')
def video_stream():
    """原始RTSP视频流（MJPEG格式，不经过YOLO处理）"""
    return Response(
        generate_raw_video_stream(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@app.route('/api/video/processed_stream')
def processed_video_stream():
    """经过YOLO处理的视频流（MJPEG格式，包含检测框和区域）"""
    return Response(
        generate_processed_video_stream(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


# 录制相关API
@app.route('/api/recording/status', methods=['GET'])
def get_recording_status_api():
    """获取录制状态"""
    return jsonify(get_recording_status())


@app.route('/api/recording/start', methods=['POST'])
def start_recording_api():
    """开始录制"""
    result = start_recording()
    return jsonify(result)


@app.route('/api/recording/stop', methods=['POST'])
def stop_recording_api():
    """停止录制"""
    result = stop_recording()
    return jsonify(result)


@app.route('/api/recording/config', methods=['GET'])
def get_recording_config_api():
    """获取录制配置"""
    return jsonify(recording_config)


@app.route('/api/recording/config', methods=['POST'])
def set_recording_config_api():
    """设置录制配置"""
    global recording_config
    
    data = request.json
    
    try:
        if 'save_path' in data:
            save_path = data['save_path'].strip()
            if not save_path:
                return jsonify({"success": False, "message": "保存路径不能为空"}), 400
            # 确保路径存在
            os.makedirs(save_path, exist_ok=True)
            recording_config['save_path'] = save_path
        
        if 'segment_duration' in data:
            segment_duration = int(data['segment_duration'])
            if segment_duration < 60:
                return jsonify({"success": False, "message": "分割时长不能少于60秒"}), 400
            if segment_duration > 3600:
                return jsonify({"success": False, "message": "分割时长不能超过3600秒"}), 400
            recording_config['segment_duration'] = segment_duration
        
        save_recording_config()
        return jsonify({
            "success": True,
            "message": "录制配置已更新",
            "config": recording_config
        })
    except ValueError:
        return jsonify({"success": False, "message": "参数格式错误"}), 400
    except Exception as e:
        return jsonify({"success": False, "message": f"设置失败: {str(e)}"}), 500


@app.route('/api/recording/videos', methods=['GET'])
def list_recording_videos():
    """列出所有录制的视频文件"""
    try:
        save_path = recording_config.get('save_path', '')
        if not save_path or not os.path.exists(save_path):
            return jsonify({
                "success": True,
                "videos": [],
                "count": 0,
                "save_path": save_path
            })
        
        videos = []
        for filename in os.listdir(save_path):
            if filename.endswith(('.mp4', '.avi', '.mkv', '.mov')):
                filepath = os.path.join(save_path, filename)
                try:
                    file_stat = os.stat(filepath)
                    file_size = file_stat.st_size
                    modified_time = datetime.fromtimestamp(file_stat.st_mtime)
                    
                    videos.append({
                        "filename": filename,
                        "size": file_size,
                        "size_mb": round(file_size / (1024 * 1024), 2),
                        "size_gb": round(file_size / (1024 * 1024 * 1024), 2),
                        "modified_time": modified_time.strftime("%Y-%m-%d %H:%M:%S"),
                        "modified_timestamp": file_stat.st_mtime
                    })
                except Exception as e:
                    backend_logger.warning(f"获取文件信息失败 {filename}: {e}")
                    continue
        
        # 按修改时间倒序排列（最新的在前）
        videos.sort(key=lambda x: x['modified_timestamp'], reverse=True)
        
        return jsonify({
            "success": True,
            "videos": videos,
            "count": len(videos),
            "save_path": save_path
        })
    except Exception as e:
        backend_logger.error(f"列出录制视频失败: {e}")
        return jsonify({"success": False, "message": f"列出视频失败: {str(e)}"}), 500


@app.route('/api/recording/videos/<filename>', methods=['GET'])
def download_recording_video(filename):
    """下载录制的视频文件"""
    try:
        save_path = recording_config.get('save_path', '')
        if not save_path:
            return jsonify({"success": False, "message": "保存路径未配置"}), 400
        
        # 安全检查：防止路径遍历攻击
        filename = os.path.basename(filename)  # 只保留文件名，去除路径
        filepath = os.path.join(save_path, filename)
        
        # 确保文件在保存路径内
        if not os.path.abspath(filepath).startswith(os.path.abspath(save_path)):
            return jsonify({"success": False, "message": "无效的文件路径"}), 400
        
        if not os.path.exists(filepath):
            return jsonify({"success": False, "message": "文件不存在"}), 404
        
        # 使用send_from_directory发送文件
        return send_from_directory(
            save_path,
            filename,
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        backend_logger.error(f"下载录制视频失败: {e}")
        return jsonify({"success": False, "message": f"下载失败: {str(e)}"}), 500


@app.route('/api/recording/videos/<filename>', methods=['DELETE'])
def delete_recording_video(filename):
    """删除录制的视频文件"""
    try:
        save_path = recording_config.get('save_path', '')
        if not save_path:
            return jsonify({"success": False, "message": "保存路径未配置"}), 400
        
        # 安全检查：防止路径遍历攻击
        filename = os.path.basename(filename)
        filepath = os.path.join(save_path, filename)
        
        # 确保文件在保存路径内
        if not os.path.abspath(filepath).startswith(os.path.abspath(save_path)):
            return jsonify({"success": False, "message": "无效的文件路径"}), 400
        
        if not os.path.exists(filepath):
            return jsonify({"success": False, "message": "文件不存在"}), 404
        
        # 删除文件
        os.remove(filepath)
        backend_logger.info(f"已删除录制视频: {filename}")
        
        return jsonify({
            "success": True,
            "message": "视频已删除"
        })
    except Exception as e:
        backend_logger.error(f"删除录制视频失败: {e}")
        return jsonify({"success": False, "message": f"删除失败: {str(e)}"}), 500


@app.route('/api/recording/videos/<filename>/rename', methods=['POST'])
def rename_recording_video(filename):
    """重命名录制的视频文件"""
    try:
        save_path = recording_config.get('save_path', '')
        if not save_path:
            return jsonify({"success": False, "message": "保存路径未配置"}), 400
        
        data = request.json
        new_filename = data.get('new_filename', '').strip()
        
        if not new_filename:
            return jsonify({"success": False, "message": "新文件名不能为空"}), 400
        
        # 安全检查
        filename = os.path.basename(filename)
        new_filename = os.path.basename(new_filename)  # 只保留文件名
        
        # 确保新文件名有正确的扩展名
        old_ext = os.path.splitext(filename)[1]
        if not new_filename.endswith(old_ext):
            new_filename = new_filename + old_ext
        
        old_filepath = os.path.join(save_path, filename)
        new_filepath = os.path.join(save_path, new_filename)
        
        # 确保文件在保存路径内
        if not os.path.abspath(old_filepath).startswith(os.path.abspath(save_path)):
            return jsonify({"success": False, "message": "无效的文件路径"}), 400
        
        if not os.path.exists(old_filepath):
            return jsonify({"success": False, "message": "文件不存在"}), 404
        
        if os.path.exists(new_filepath):
            return jsonify({"success": False, "message": "目标文件名已存在"}), 400
        
        # 重命名文件
        os.rename(old_filepath, new_filepath)
        backend_logger.info(f"已重命名录制视频: {filename} -> {new_filename}")
        
        return jsonify({
            "success": True,
            "message": "视频已重命名",
            "new_filename": new_filename
        })
    except Exception as e:
        backend_logger.error(f"重命名录制视频失败: {e}")
        return jsonify({"success": False, "message": f"重命名失败: {str(e)}"}), 500


@app.route('/api/recording/videos/<filename>/preview', methods=['GET'])
def preview_recording_video(filename):
    """获取视频预览（返回视频的第一帧）"""
    try:
        save_path = recording_config.get('save_path', '')
        if not save_path:
            return jsonify({"success": False, "message": "保存路径未配置"}), 400
        
        # 安全检查
        filename = os.path.basename(filename)
        filepath = os.path.join(save_path, filename)
        
        # 确保文件在保存路径内
        if not os.path.abspath(filepath).startswith(os.path.abspath(save_path)):
            return jsonify({"success": False, "message": "无效的文件路径"}), 400
        
        if not os.path.exists(filepath):
            return jsonify({"success": False, "message": "文件不存在"}), 404
        
        # 使用OpenCV读取视频第一帧
        cap = cv2.VideoCapture(filepath)
        if not cap.isOpened():
            return jsonify({"success": False, "message": "无法打开视频文件"}), 500
        
        ret, frame = cap.read()
        cap.release()
        
        if not ret or frame is None:
            return jsonify({"success": False, "message": "无法读取视频帧"}), 500
        
        # 编码为JPEG
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        frame_bytes = buffer.tobytes()
        
        # 返回图片
        from flask import Response
        return Response(
            frame_bytes,
            mimetype='image/jpeg',
            headers={'Content-Disposition': f'inline; filename=preview_{filename}.jpg'}
        )
    except Exception as e:
        backend_logger.error(f"获取视频预览失败: {e}")
        return jsonify({"success": False, "message": f"获取预览失败: {str(e)}"}), 500


@app.route('/api/alarm', methods=['GET'])
def get_alarm_config():
    """获取报警配置"""
    return jsonify(alarm_config)

@app.route('/api/alarm', methods=['POST'])
def set_alarm_config():
    """设置报警配置"""
    global alarm_config
    
    data = request.json
    
    try:
        if 'debounce_time' in data:
            debounce_time = float(data['debounce_time'])
            if debounce_time < 0:
                return jsonify({"success": False, "message": "防抖时间不能为负数"}), 400
            alarm_config['debounce_time'] = debounce_time
        
        if 'detection_mode' in data:
            detection_mode = data['detection_mode']
            if detection_mode not in ['center', 'edge']:
                return jsonify({"success": False, "message": "检测模式必须是'center'或'edge'"}), 400
            alarm_config['detection_mode'] = detection_mode
        
        if 'once_per_id' in data:
            once_per_id = data['once_per_id']
            if not isinstance(once_per_id, bool):
                return jsonify({"success": False, "message": "once_per_id必须是布尔值"}), 400
            alarm_config['once_per_id'] = once_per_id
            # 如果启用"相同ID只报警一次"，清空之前的报警记录
            if once_per_id:
                alarm_triggered.clear()
        
        if 'save_event_video' in data:
            alarm_config['save_event_video'] = bool(data['save_event_video'])
        
        if 'save_event_image' in data:
            alarm_config['save_event_image'] = bool(data['save_event_image'])
        
        if 'event_video_duration' in data:
            duration = int(data['event_video_duration'])
            if duration < 5 or duration > 60:
                return jsonify({"success": False, "message": "事件视频时长必须在5-60秒之间"}), 400
            alarm_config['event_video_duration'] = duration
        
        if 'event_save_path' in data:
            event_path = data['event_save_path'].strip()
            if event_path:
                # 验证路径是否有效
                try:
                    os.makedirs(event_path, exist_ok=True)
                    os.makedirs(os.path.join(event_path, "videos"), exist_ok=True)
                    os.makedirs(os.path.join(event_path, "images"), exist_ok=True)
                    alarm_config['event_save_path'] = event_path
                except Exception as e:
                    return jsonify({"success": False, "message": f"保存路径无效: {str(e)}"}), 400
            else:
                # 使用默认路径
                alarm_config['event_save_path'] = os.path.join(BASE_DIR, "alarm_events")
        
        save_alarm_config()
        return jsonify({
            "success": True,
            "message": "报警配置已更新",
            "config": alarm_config
        })
    except ValueError:
        return jsonify({"success": False, "message": "参数格式错误"}), 400
    except Exception as e:
        return jsonify({"success": False, "message": f"设置失败: {str(e)}"}), 500

if __name__ == '__main__':
    backend_logger.info("="*60)
    backend_logger.info("启动后端服务...")
    backend_logger.info("访问 http://localhost:5000 查看前端界面")
    backend_logger.info("="*60)
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)

