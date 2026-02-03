#!/bin/bash

# 启动前端开发服务器

cd frontend

# 检查是否已安装依赖
if [ ! -d "node_modules" ]; then
    echo "正在安装依赖..."
    yarn install
fi

# 设置环境变量，告知后端使用 Vite 开发模式
export VITE_DEV=true

# 获取本机IP地址（如果可用）
HOST_IP=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "localhost")

# 设置后端API地址（可以通过环境变量覆盖）
export VITE_API_URL=${VITE_API_URL:-"http://${HOST_IP}:5000"}

echo "启动前端开发服务器..."
echo "前端地址: http://${HOST_IP}:5173 或 http://localhost:5173"
echo "后端 API: ${VITE_API_URL}"
echo ""
echo "提示：可以通过设置 VITE_API_URL 环境变量来指定后端地址"
echo "例如: VITE_API_URL=http://192.168.1.100:5000 ./start_frontend.sh"
echo ""
echo "请确保后端服务已启动！"
echo ""

yarn dev

