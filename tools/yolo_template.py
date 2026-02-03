import cv2
import threading
import queue
import time
import signal
import sys

from ultralytics import YOLO

# Load the YOLO model
# model = YOLO("yolo26m.pt")
# model = YOLO("yolo26m.onnx")
model = YOLO("yolo26m.engine")

# 视频路径
video_path = "rtsp://admin:scyzkj123456@192.168.1.2:554/h264/ch1/main/av_stream"

# 用于线程间通信的队列（只保留最新帧，避免堆积）
frame_queue = queue.Queue(maxsize=2)
stop_flag = threading.Event()


def signal_handler(sig, frame):
    """处理 Ctrl+C 信号"""
    print("\n收到中断信号，正在停止...")
    stop_flag.set()
    sys.exit(0)


# 注册信号处理器
signal.signal(signal.SIGINT, signal_handler)


def video_reader():
    """在单独线程中读取视频帧，保持最新帧"""
    cap = cv2.VideoCapture(video_path)
    
    # 设置缓冲区大小，减少延迟
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    while not stop_flag.is_set():
        success, frame = cap.read()
        
        if not success:
            break
        
        # 只保留最新帧，丢弃旧帧
        if not frame_queue.empty():
            try:
                frame_queue.get_nowait()
            except queue.Empty:
                pass
        
        try:
            frame_queue.put(frame, block=False)
        except queue.Full:
            pass
    
    cap.release()
    print("视频读取线程已停止")


# 启动视频读取线程
reader_thread = threading.Thread(target=video_reader, daemon=True)
reader_thread.start()

# 主线程处理YOLO推理和显示
print("开始处理视频流，按 'q' 键退出或 Ctrl+C 停止...")

try:
    while not stop_flag.is_set():
        try:
            # 从队列获取最新帧（超时1秒）
            frame = frame_queue.get(timeout=1)
            
            # Run YOLO tracking on the frame, persisting tracks between frames
            results = model.track(frame, persist=True)
            
            # Visualize the results on the frame
            annotated_frame = results[0].plot()
            
            # Display the annotated frame
            cv2.imshow("YOLO Tracking", annotated_frame)
            
            # Break the loop if 'q' is pressed
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
                
        except queue.Empty:
            # 如果队列为空，继续等待
            continue
        except KeyboardInterrupt:
            # 捕获 Ctrl+C
            print("\n收到中断信号，正在停止...")
            break
            
except KeyboardInterrupt:
    # 捕获 Ctrl+C（包括在 YOLO 推理过程中）
    print("\n收到中断信号，正在停止...")

# 停止视频读取线程
stop_flag.set()
reader_thread.join(timeout=2)

# 清理资源
cv2.destroyAllWindows()
print("程序已退出")