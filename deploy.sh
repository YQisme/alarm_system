#!/bin/bash

# YOLO 目标检测与区域报警系统 - 快速部署脚本
# 适用于生产环境部署

set -e  # 遇到错误立即退出

echo "=========================================="
echo "YOLO 目标检测与区域报警系统 - 快速部署"
echo "=========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查 Python 版本
echo "1. 检查 Python 环境..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}错误: 未找到 python3，请先安装 Python 3.10+${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo -e "${GREEN}✓ Python 版本: $(python3 --version)${NC}"

# 检查是否在项目根目录
if [ ! -f "requirements.txt" ] || [ ! -d "backend" ]; then
    echo -e "${RED}错误: 请在项目根目录运行此脚本${NC}"
    exit 1
fi

# 安装 Python 依赖
echo ""
echo "2. 安装 Python 依赖..."
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}错误: 未找到 requirements.txt${NC}"
    exit 1
fi

pip3 install -r requirements.txt

# 安装可选依赖
echo ""
read -p "是否安装 MQTT 支持？(y/n，默认n): " install_mqtt
if [[ $install_mqtt =~ ^[Yy]$ ]]; then
    echo "安装 paho-mqtt..."
    pip3 install paho-mqtt
fi

# 检查 FFmpeg
echo ""
echo "3. 检查 FFmpeg..."
if command -v ffmpeg &> /dev/null; then
    echo -e "${GREEN}✓ FFmpeg 已安装: $(ffmpeg -version | head -n1)${NC}"
else
    echo -e "${YELLOW}警告: 未找到 FFmpeg${NC}"
    echo "如果需要视频录制和报警事件保存功能，请安装 FFmpeg:"
    echo "  Ubuntu/Debian: sudo apt-get install ffmpeg"
    echo "  CentOS/RHEL: sudo yum install ffmpeg"
    read -p "是否现在安装 FFmpeg？(y/n，默认n): " install_ffmpeg
    if [[ $install_ffmpeg =~ ^[Yy]$ ]]; then
        if command -v apt-get &> /dev/null; then
            sudo apt-get update
            sudo apt-get install -y ffmpeg
        elif command -v yum &> /dev/null; then
            sudo yum install -y ffmpeg
        else
            echo -e "${RED}错误: 无法自动安装 FFmpeg，请手动安装${NC}"
        fi
    fi
fi

# 检查模型文件
echo ""
echo "4. 检查模型文件..."
if [ ! -d "models" ]; then
    mkdir -p models
    echo -e "${YELLOW}警告: models/ 目录不存在，已创建${NC}"
fi

MODEL_COUNT=$(find models -name "*.pt" -o -name "*.engine" -o -name "*.onnx" 2>/dev/null | wc -l)
if [ $MODEL_COUNT -eq 0 ]; then
    echo -e "${YELLOW}警告: models/ 目录下没有找到模型文件${NC}"
    echo "请将 YOLO 模型文件（.pt, .engine, .onnx）放入 models/ 目录"
else
    echo -e "${GREEN}✓ 找到 $MODEL_COUNT 个模型文件${NC}"
fi

# 创建必要的目录
echo ""
echo "5. 创建必要的目录..."
mkdir -p config
mkdir -p logs
mkdir -p recordings
mkdir -p alarm_events/videos
mkdir -p alarm_events/images
echo -e "${GREEN}✓ 目录创建完成${NC}"

# 设置权限
echo ""
echo "6. 设置文件权限..."
chmod +x start_server.sh 2>/dev/null || true
chmod +x start_frontend.sh 2>/dev/null || true
chmod 755 config
chmod 755 logs
echo -e "${GREEN}✓ 权限设置完成${NC}"

# 构建前端（可选）
echo ""
read -p "是否构建前端？（生产模式需要，y/n，默认y）: " build_frontend
build_frontend=${build_frontend:-y}

if [[ $build_frontend =~ ^[Yy]$ ]]; then
    if [ ! -d "frontend" ]; then
        echo -e "${YELLOW}警告: frontend/ 目录不存在，跳过前端构建${NC}"
    else
        echo ""
        echo "7. 构建前端..."
        
        # 检查 Node.js
        if ! command -v node &> /dev/null && ! command -v yarn &> /dev/null && ! command -v npm &> /dev/null; then
            echo -e "${YELLOW}警告: 未找到 Node.js/yarn/npm，跳过前端构建${NC}"
            echo "如果已有构建好的 frontend/dist/ 目录，可以继续使用"
        else
            cd frontend
            
            # 安装依赖
            if [ ! -d "node_modules" ]; then
                echo "安装前端依赖..."
                if command -v yarn &> /dev/null; then
                    yarn install
                elif command -v npm &> /dev/null; then
                    npm install
                fi
            fi
            
            # 构建
            echo "构建前端..."
            if command -v yarn &> /dev/null; then
                yarn build
            elif command -v npm &> /dev/null; then
                npm run build
            fi
            
            cd ..
            
            if [ -d "frontend/dist" ]; then
                echo -e "${GREEN}✓ 前端构建完成${NC}"
            else
                echo -e "${RED}错误: 前端构建失败${NC}"
            fi
        fi
    fi
fi

# 显示部署信息
echo ""
echo "=========================================="
echo -e "${GREEN}部署完成！${NC}"
echo "=========================================="
echo ""

# 获取本机IP
HOST_IP=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "localhost")

echo "部署信息："
echo "  项目目录: $(pwd)"
echo "  访问地址: http://${HOST_IP}:5000"
echo "  默认登录: admin / 123456"
echo ""
echo "启动服务："
echo "  ./start_server.sh"
echo ""
echo "或使用 systemd 服务（推荐生产环境）："
echo "  sudo systemctl start yolo-detection"
echo ""
echo "查看日志："
echo "  tail -f logs/backend.log"
echo ""
echo -e "${YELLOW}重要提示：${NC}"
echo "  1. 首次登录后请立即修改默认密码"
echo "  2. 在系统配置中设置视频源地址"
echo "  3. 创建监控区域"
echo "  4. 配置报警设置"
echo ""
echo "=========================================="

