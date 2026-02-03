from flask import Flask, request, jsonify, send_from_directory
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
polygon_points = []  # 多边形顶点列表
polygon_defined = False  # 多边形是否已定义
alarm_triggered = {}  # 记录已触发报警的跟踪ID

# 报警配置
alarm_config = {
    "debounce_time": 5.0,  # 防抖时间（秒），同一目标在此时间内只报警一次
    "detection_mode": "center",  # 检测模式："center"=中心点，"edge"=边框任意点
    "once_per_id": False  # 相同ID是否只报警一次（True=整个生命周期只报警一次，False=允许重复报警）
}

polygon_config_file = os.path.join(CONFIG_DIR, "polygon_zone.json")  # 多边形区域配置文件
config_file = os.path.join(CONFIG_DIR, "system_config.json")  # 系统配置文件
classes_config_file = os.path.join(CONFIG_DIR, "classes_config.json")  # 类别配置文件
display_config_file = os.path.join(CONFIG_DIR, "display_config.json")  # 显示配置文件
model_classes_file = os.path.join(CONFIG_DIR, "model_classes.json")  # 模型类别映射配置文件
alarm_config_file = os.path.join(CONFIG_DIR, "alarm_config.json")  # 报警配置文件
latest_frame = None  # 最新帧
latest_results = None  # 最新检测结果

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
model = None  # 模型对象，延迟加载

# 加载系统配置
def load_system_config():
    """从配置文件加载系统配置"""
    global current_model_name, video_path, model
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                if 'model' in config:
                    current_model_name = config['model']
                if 'video_url' in config:
                    video_path = config['video_url']
                backend_logger.info(f"已从 {config_file} 加载系统配置")
        except Exception as e:
            backend_logger.error(f"加载系统配置文件失败: {e}")
    
    # 加载模型
    load_model()

def save_system_config():
    """保存系统配置到文件"""
    config = {
        "model": current_model_name,
        "video_url": video_path
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
                backend_logger.info(f"已从 {alarm_config_file} 加载报警配置")
        except Exception as e:
            backend_logger.error(f"加载报警配置文件失败: {e}")

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


def trigger_alarm(track_id, bbox_center, class_id=None, class_name_cn=None):
    """触发报警"""
    global alarm_triggered, alarm_config
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 使用 (track_id, class_id) 作为唯一标识，避免不同类别的相同ID冲突
    alarm_key = f"{track_id}_{class_id}" if class_id is not None else str(track_id)
    
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
    
    alarm_data = {
        "time": current_time,
        "track_id": track_id,
        "class_id": class_id,
        "class_name_cn": class_name_cn,
        "object_name": object_name,
        "position": {"x": float(bbox_center[0]), "y": float(bbox_center[1])}
    }
    
    # 通过WebSocket发送报警信息
    socketio.emit('alarm', alarm_data)
    backend_logger.warning(f"⚠️  报警！{object_name}进入监控区域！时间: {current_time}, ID: {track_id}")
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
    global latest_frame, latest_results, polygon_points, polygon_defined, fps_counter, display_config
    
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
                    results_generator = model.track(frame, persist=True, stream=True, device=device)
                    results = next(results_generator)  # 从生成器中获取结果
                latest_results = results
            except Exception as e:
                yolo_logger.error(f"YOLO检测错误: {e}")
                time.sleep(0.1)
                continue
            
            # 如果多边形已定义，检测对象是否进入区域
            if polygon_defined and len(polygon_points) >= 3:
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
                                    
                                    # 根据配置的检测模式判断是否进入区域
                                    detection_mode = alarm_config.get('detection_mode', 'center')
                                    in_zone = False
                                    if detection_mode == 'center':
                                        # 中心点模式：检查中心点是否在多边形内
                                        in_zone = is_point_in_polygon(bbox_center, polygon_points)
                                    elif detection_mode == 'edge':
                                        # 边框任意点模式：检查检测框是否与多边形有交集
                                        in_zone = is_bbox_in_polygon([x1, y1, x2, y2], polygon_points)
                                    
                                    if in_zone:
                                        track_id = int(track_ids[i])
                                        class_name_cn = get_class_name_cn(cls_id)
                                        trigger_alarm(track_id, bbox_center, cls_id, class_name_cn)
            
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
                                
                                # 判断是否在报警区域内
                                in_zone = False
                                if polygon_defined:
                                    detection_mode = alarm_config.get('detection_mode', 'center')
                                    if detection_mode == 'center':
                                        # 中心点模式：检查中心点是否在多边形内
                                        in_zone = is_point_in_polygon(bbox_center, polygon_points)
                                    elif detection_mode == 'edge':
                                        # 边框任意点模式：检查检测框是否与多边形有交集
                                        in_zone = is_bbox_in_polygon([x1, y1, x2, y2], polygon_points)
                                
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
            
            # 绘制多边形区域
            if polygon_defined and len(polygon_points) >= 3:
                polygon_array = np.array(polygon_points, np.int32)
                
                # 先绘制边框（在填充之前，确保边框可见）
                zone_border_color_list = display_config.get('zone_border_color', [0, 255, 255])
                # 确保颜色值是整数元组
                zone_border_color = (int(zone_border_color_list[0]), int(zone_border_color_list[1]), int(zone_border_color_list[2]))
                cv2.polylines(annotated_frame, [polygon_array], True, zone_border_color, 3)
                
                # 再绘制填充
                overlay = annotated_frame.copy()
                # 使用配置的填充颜色（直接从display_config读取，不使用默认值）
                zone_fill_color_list = display_config.get('zone_fill_color', [0, 255, 255])
                zone_fill_alpha = display_config.get('zone_fill_alpha', 0.3)
                # 确保颜色值是整数元组
                zone_fill_color = (int(zone_fill_color_list[0]), int(zone_fill_color_list[1]), int(zone_fill_color_list[2]))
                cv2.fillPoly(overlay, [polygon_array], zone_fill_color)
                cv2.addWeighted(overlay, zone_fill_alpha, annotated_frame, 1.0 - zone_fill_alpha, 0, annotated_frame)
                
                # 调试日志（每100帧输出一次，避免日志过多）
                if got_new_frame:
                    frame_count = fps_counter.get("frame_count", 0)
                    if frame_count % 100 == 0:
                        backend_logger.info(f"绘制报警区域 - 填充颜色: {zone_fill_color}, 边框颜色: {zone_border_color}, 透明度: {zone_fill_alpha}, display_config中的值: fill={display_config.get('zone_fill_color')}, border={display_config.get('zone_border_color')}, alpha={display_config.get('zone_fill_alpha')}")
            
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
                "polygon": polygon_points if polygon_defined else [],
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
                                
                                in_zone = is_point_in_polygon(bbox_center, polygon_points) if polygon_defined else False
                                
                                detection_data["detections"].append({
                                    "id": track_id,
                                    "class_id": cls_id,
                                    "class_name": model_classes[cls_id] if cls_id < len(model_classes) else f"class_{cls_id}",
                                    "class_name_cn": get_class_name_cn(cls_id),
                                    "bbox": [float(x1), float(y1), float(x2), float(y2)],
                                    "center": {"x": float(bbox_center[0]), "y": float(bbox_center[1])},
                                    "confidence": conf,
                                    "in_zone": in_zone
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


def load_polygon_config():
    """从配置文件加载多边形区域"""
    global polygon_points, polygon_defined
    if os.path.exists(polygon_config_file):
        try:
            with open(polygon_config_file, 'r') as f:
                config = json.load(f)
                polygon_points = config.get("polygon_points", [])
                if len(polygon_points) >= 3:
                    polygon_defined = True
                    backend_logger.info(f"已从 {polygon_config_file} 加载多边形区域，共 {len(polygon_points)} 个顶点")
                    return True
        except Exception as e:
            backend_logger.error(f"加载配置文件失败: {e}")
    return False


def save_polygon_config():
    """保存多边形区域到配置文件"""
    global polygon_points
    if polygon_points:
        config = {"polygon_points": polygon_points}
        with open(polygon_config_file, 'w') as f:
            json.dump(config, f)
        backend_logger.info(f"多边形区域已保存到 {polygon_config_file}")


# 加载已保存的多边形区域
load_polygon_config()


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


# REST API 路由
@app.route('/api/polygon', methods=['GET'])
def get_polygon():
    """获取当前多边形区域"""
    return jsonify({
        "polygon": polygon_points,
        "defined": polygon_defined
    })


@app.route('/api/polygon', methods=['POST'])
def set_polygon():
    """设置多边形区域"""
    global polygon_points, polygon_defined
    
    data = request.json
    points = data.get('polygon', [])
    
    if len(points) >= 3:
        polygon_points = points
        polygon_defined = True
        save_polygon_config()
        return jsonify({"success": True, "message": "多边形区域已设置"})
    else:
        return jsonify({"success": False, "message": "至少需要3个顶点"}), 400


@app.route('/api/polygon', methods=['DELETE'])
def clear_polygon():
    """清除多边形区域"""
    global polygon_points, polygon_defined, alarm_triggered
    
    polygon_points = []
    polygon_defined = False
    alarm_triggered.clear()
    
    if os.path.exists(polygon_config_file):
        os.remove(polygon_config_file)
    
    return jsonify({"success": True, "message": "多边形区域已清除"})


@app.route('/api/status', methods=['GET'])
def get_status():
    """获取系统状态"""
    global gpu_available, device
    # 重新检测GPU状态
    gpu_available, device = check_gpu_available()
    
    return jsonify({
        "video_connected": not frame_queue.empty() or latest_frame is not None,
        "polygon_defined": polygon_defined,
        "polygon_points_count": len(polygon_points),
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
    """获取当前视频URL"""
    with video_lock:
        return jsonify({"video_url": video_path})


@app.route('/api/video', methods=['POST'])
def set_video():
    """设置视频URL"""
    global video_path
    
    data = request.json
    new_video_url = data.get('video_url')
    
    if not new_video_url:
        return jsonify({"success": False, "message": "未指定视频URL"}), 400
    
    try:
        with video_lock:
            video_path = new_video_url
        save_system_config()
        return jsonify({
            "success": True,
            "message": "视频URL已更新",
            "video_url": video_path
        })
    except Exception as e:
        return jsonify({"success": False, "message": f"设置视频URL失败: {str(e)}"}), 500


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

