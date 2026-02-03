#!/bin/bash

echo "=========================================="
echo "启动 YOLO 人员检测与区域报警系统"
echo "=========================================="
echo ""
echo "请确保已安装以下依赖："
echo "  pip install -r requirements.txt"
echo ""
echo "启动后端服务..."
# 获取主机IP地址
HOST_IP=$(hostname -I | awk '{print $1}')
if [ -z "$HOST_IP" ]; then
    HOST_IP="localhost"
fi
echo "访问地址: http://${HOST_IP}:5000"
echo ""
echo "按 Ctrl+C 停止服务"
echo "=========================================="
echo ""

python3 backend/server.py

