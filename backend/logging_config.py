"""
日志配置模块
提供后端日志和YOLO推理日志的分离配置
"""
import os
import logging
from logging.handlers import RotatingFileHandler
import queue
from datetime import datetime
from flask_socketio import SocketIO

# 日志队列，用于向前端发送日志
log_queue = queue.Queue()

# 自定义日志处理器，将日志发送到WebSocket
class WebSocketLogHandler(logging.Handler):
    def __init__(self, socketio_instance):
        super().__init__()
        self.socketio = socketio_instance
    
    def emit(self, record):
        try:
            log_entry = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'level': record.levelname,
                'logger': record.name,
                'message': self.format(record)
            }
            # 将日志放入队列，由后台线程发送
            try:
                log_queue.put(log_entry, block=False)
            except queue.Full:
                pass  # 如果队列满了，丢弃日志（避免阻塞）
            except Exception as e:
                # 如果队列操作失败，至少打印出来
                print(f"日志队列操作失败: {e}")
        except Exception:
            pass  # 忽略日志处理错误

def setup_logging(base_dir, socketio_instance):
    """设置日志系统"""
    logs_dir = os.path.join(base_dir, 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    # 配置后端日志
    backend_logger = logging.getLogger('backend')
    backend_logger.setLevel(logging.INFO)
    backend_logger.propagate = False
    
    # 后端日志文件处理器
    backend_file_handler = RotatingFileHandler(
        os.path.join(logs_dir, 'backend.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    backend_file_handler.setLevel(logging.INFO)
    backend_file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    backend_file_handler.setFormatter(backend_file_formatter)
    
    # 后端日志WebSocket处理器
    backend_ws_handler = WebSocketLogHandler(socketio_instance)
    backend_ws_handler.setLevel(logging.INFO)
    backend_ws_formatter = logging.Formatter('%(message)s')
    backend_ws_handler.setFormatter(backend_ws_formatter)
    
    backend_logger.addHandler(backend_file_handler)
    backend_logger.addHandler(backend_ws_handler)
    
    # 配置YOLO推理日志
    yolo_logger = logging.getLogger('yolo')
    yolo_logger.setLevel(logging.INFO)
    yolo_logger.propagate = False
    
    # YOLO日志文件处理器
    yolo_file_handler = RotatingFileHandler(
        os.path.join(logs_dir, 'yolo.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    yolo_file_handler.setLevel(logging.INFO)
    yolo_file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    yolo_file_handler.setFormatter(yolo_file_formatter)
    
    # YOLO日志WebSocket处理器
    yolo_ws_handler = WebSocketLogHandler(socketio_instance)
    yolo_ws_handler.setLevel(logging.INFO)
    yolo_ws_formatter = logging.Formatter('%(message)s')
    yolo_ws_handler.setFormatter(yolo_ws_formatter)
    
    yolo_logger.addHandler(yolo_file_handler)
    yolo_logger.addHandler(yolo_ws_handler)
    
    # 重定向ultralytics的日志到yolo_logger
    ultralytics_logger = logging.getLogger('ultralytics')
    ultralytics_logger.setLevel(logging.INFO)
    ultralytics_logger.addHandler(yolo_file_handler)
    ultralytics_logger.addHandler(yolo_ws_handler)
    ultralytics_logger.propagate = False
    
    return backend_logger, yolo_logger, log_queue

