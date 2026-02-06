# YOLO 目标检测与区域报警系统

基于 YOLO 的实时目标检测系统，支持80个COCO类别检测，支持多个自定义多边形监控区域，当目标进入指定区域时自动触发报警。采用前后端分离架构（BS架构），提供 Web 界面进行可视化操作。支持用户登录认证、MQTT报警推送、视频录制、摄像头状态检测、画面遮挡检测等丰富功能。

**主要特性**：
- 🎯 支持多类别目标检测（人、车、动物等80个类别）
- 🔄 支持动态切换模型和视频源
- ⚙️ 支持类别选择、自定义名称、置信度设置
- 🎨 支持显示样式定制（字体、颜色、中英文切换）
- 📋 支持模型类别映射配置
- 🖥️ 自动GPU检测，无GPU时自动使用CPU
- 📊 实时显示帧率和分辨率
- 📝 日志系统（后端日志和YOLO推理日志分离，前端实时查看）
- 🔔 灵活的报警配置（防抖时间、检测模式、相同ID只报警一次）
- 🔐 用户登录认证系统，保护系统安全
- 📡 MQTT报警消息推送，支持第三方系统集成
- 🎥 视频录制功能，支持分段录制和管理
- 📸 报警事件自动保存（视频和图片）
- 🚨 多区域检测与报警，支持同时监控多个区域
- 📹 摄像头状态检测，自动检测摄像头在线/离线
- 👁️ 画面遮挡检测，检测摄像头被遮挡情况
- 📋 操作日志记录，记录用户操作和系统事件

## 功能特性

- 🎯 **实时目标检测**：基于 YOLO 模型进行实时目标跟踪检测（支持80个COCO类别）
- 📐 **自定义监控区域**：支持在视频画面上绘制多边形监控区域
- 🔔 **智能报警**：当检测到目标进入监控区域时自动触发报警
- 🖱️ **交互式绘制**：鼠标点击绘制，支持首尾吸附功能，便于精确闭合
- 💾 **配置持久化**：所有配置自动保存，重启后自动加载
- 📊 **实时信息显示**：显示检测到的目标信息和报警记录
- 🌐 **Web 界面**：基于 Web 的前端界面，支持跨平台访问
- 🎨 **模型管理**：支持动态切换不同的YOLO模型
- 📹 **视频源管理**：支持动态切换RTSP、本地视频文件等视频源
- 🏷️ **类别管理**：可选择检测的类别，支持自定义中文名称
- ⚙️ **置信度设置**：为每个类别单独设置置信度阈值
- 🎨 **显示定制**：自定义字体大小、边框颜色、文字颜色等显示样式
- 🌐 **中英文切换**：支持中文和英文显示切换，英文模式性能更优
- 📋 **模型类别映射**：每个模型可配置独立的类别映射（支持不同数据集）
- 🖥️ **GPU自动检测**：自动检测GPU可用性，无GPU时自动使用CPU模式
- 📊 **性能监控**：实时显示视频帧率和分辨率信息
- 📝 **日志系统**：后端日志和YOLO推理日志分离保存，前端实时查看
- 🔔 **报警配置**：可配置防抖时间、检测模式（中心点/边框）、相同ID只报警一次
- 🔐 **用户登录认证**：支持用户名密码登录，保护系统安全，支持路由守卫
- 📡 **MQTT报警推送**：支持将报警消息推送到MQTT服务器，方便第三方系统集成
- 🎥 **视频录制功能**：支持实时视频录制，自动分段保存，支持视频列表管理和预览
- 📸 **报警事件保存**：自动保存报警事件的视频和图片，便于后续查看和分析
- 🚨 **多区域管理**：支持创建、编辑、启用/禁用多个监控区域，每个区域可独立配置
- 📹 **摄像头状态检测**：自动检测摄像头在线/离线状态，支持离线报警
- 👁️ **画面遮挡检测**：检测摄像头画面是否被遮挡，支持遮挡报警
- 📋 **操作日志**：记录用户操作和系统事件，便于审计和问题排查

## 技术栈

### 后端
- **Flask**：Web 框架
- **Flask-SocketIO**：WebSocket 实时通信
- **Ultralytics YOLO**：目标检测模型
- **OpenCV**：视频处理和图像处理
- **NumPy**：数值计算
- **Pillow (PIL)**：图像处理和中文文字渲染
- **paho-mqtt**：MQTT客户端（可选，用于报警消息推送）
- **FFmpeg**：视频录制和编码（用于报警事件视频保存）

### 前端
- **Vue 3**：前端框架
- **Vite**：构建工具和开发服务器
- **Vue Router**：路由管理
- **Element Plus**：UI组件库
- **HTML5 Canvas**：视频显示和图形绘制
- **Socket.IO Client**：WebSocket 客户端
- **Axios**：HTTP客户端

## 系统要求

- Python 3.10+
- CUDA 支持的 GPU（推荐，用于加速 YOLO 推理）
- 支持 RTSP 的视频源或本地视频文件
- Node.js 和 yarn/npm（仅开发模式需要，生产模式不需要）

## 快速部署指南

### 一键部署脚本（推荐）

使用提供的部署脚本可以快速完成所有部署步骤：

```bash
# 运行部署脚本
./deploy.sh
```

脚本会自动完成：
- 检查 Python 环境
- 安装 Python 依赖
- 检查并安装 FFmpeg（可选）
- 检查模型文件
- 创建必要目录
- 设置文件权限
- 构建前端（可选）

---

### 方式一：生产环境部署（推荐）

适用于正式生产环境，前端已构建为静态文件，性能最优。

#### 步骤 1：环境准备

```bash
# 1. 确保已安装 Python 3.10+
python3 --version

# 2. 安装系统依赖（如果需要视频录制和报警事件保存功能）
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y ffmpeg

# CentOS/RHEL
sudo yum install -y ffmpeg
```

#### 步骤 2：安装 Python 依赖

```bash
cd /home/nvidia/yzkj

# 安装基础依赖
pip install -r requirements.txt

# 如果需要 MQTT 功能（可选）
pip install paho-mqtt

# 如果遇到 NumPy 版本问题
pip install "numpy>=1.24.0,<2.0.0" --force-reinstall
```

#### 步骤 3：构建前端（生产模式）

```bash
# 进入前端目录
cd frontend

# 安装前端依赖（需要 Node.js 和 yarn/npm）
# 如果没有 Node.js，可以跳过此步骤，使用已构建的 dist 目录
yarn install  # 或 npm install

# 构建前端
yarn build  # 或 npm run build

# 返回项目根目录
cd ..
```

**注意**：如果服务器上没有 Node.js，可以从其他机器构建后，将 `frontend/dist/` 目录复制到服务器。

#### 步骤 4：准备模型文件

```bash
# 确保 models/ 目录下有 YOLO 模型文件
ls models/
# 应该能看到模型文件，如：yolo11s.pt, yolo26m_640_int8.engine 等
```

#### 步骤 5：配置权限

```bash
# 确保启动脚本有执行权限
chmod +x start_server.sh

# 确保 config/ 目录有写入权限
mkdir -p config
chmod 755 config
```

#### 步骤 6：启动服务

```bash
# 使用启动脚本（推荐）
./start_server.sh

# 或直接运行
python3 backend/server.py
```

#### 步骤 7：访问系统

在浏览器中打开：
```
http://<服务器IP>:5000
```

默认登录信息：
- 用户名：`admin`
- 密码：`123456`

**首次登录后请立即修改密码！**

---

### 方式二：开发环境部署

适用于开发和测试环境，支持前端热更新。

#### 步骤 1-2：同生产环境（环境准备和安装 Python 依赖）

#### 步骤 3：安装前端依赖

```bash
cd frontend
yarn install  # 或 npm install
cd ..
```

#### 步骤 4：启动后端服务

```bash
# 终端 1：启动后端
./start_server.sh
# 或
python3 backend/server.py
```

#### 步骤 5：启动前端开发服务器

```bash
# 终端 2：启动前端开发服务器
./start_frontend.sh
# 或
cd frontend
yarn dev
```

#### 步骤 6：访问系统

- 前端地址：`http://<服务器IP>:5173` 或 `http://localhost:5173`
- 后端 API：`http://<服务器IP>:5000`

---

### 方式三：使用 systemd 服务（生产环境推荐）

适用于需要系统自动启动和管理的生产环境。

#### 步骤 1-5：同生产环境部署步骤 1-5

#### 步骤 6：创建 systemd 服务

```bash
# 创建服务文件
sudo nano /etc/systemd/system/yolo-detection.service
```

将以下内容写入文件（根据实际情况修改路径和用户名）：

```ini
[Unit]
Description=YOLO Detection and Alarm System
After=network.target

[Service]
Type=simple
User=nvidia
WorkingDirectory=/home/nvidia/yzkj
Environment="PATH=/usr/bin:/usr/local/bin"
Environment="PYTHONUNBUFFERED=1"
ExecStart=/usr/bin/python3 /home/nvidia/yzkj/backend/server.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

#### 步骤 7：启用并启动服务

```bash
# 重新加载 systemd 配置


# 启用服务（开机自启）
sudo systemctl enable yolo-detection

# 启动服务
sudo systemctl start yolo-detection

# 查看服务状态
sudo systemctl status yolo-detection

# 查看日志
sudo journalctl -u yolo-detection -f
```

#### 步骤 8：配置防火墙（如需要）

```bash
# Ubuntu/Debian (ufw)
sudo ufw allow 5000/tcp

# CentOS/RHEL (firewalld)
sudo firewall-cmd --permanent --add-port=5000/tcp
sudo firewall-cmd --reload
```

---

### 部署后配置

#### 1. 修改默认登录密码

首次登录后，在"系统配置" → "登录设置"中修改默认密码。

#### 2. 配置视频源

在"系统配置" → "视频URL"中配置 RTSP 地址或本地视频文件路径。

#### 3. 配置监控区域

在"区域管理"标签页中创建监控区域。

#### 4. 配置报警设置

在"系统配置" → "报警设置"中配置防抖时间、检测模式等。

#### 5. 配置 MQTT（可选）

如果需要 MQTT 报警推送，在"系统配置" → "MQTT设置"中配置。

---

### 部署验证清单

部署完成后，请检查以下项目：

- [ ] 服务正常启动，无错误日志
- [ ] 可以通过浏览器访问系统（`http://<IP>:5000`）
- [ ] 可以正常登录系统
- [ ] 视频流正常显示
- [ ] 模型加载成功（查看系统日志）
- [ ] GPU 检测正常（如有 GPU，查看系统状态）
- [ ] 配置文件目录有写入权限
- [ ] 模型文件存在且可读
- [ ] 防火墙端口已开放（如需要远程访问）

---

### 常见部署问题

#### 问题 1：端口被占用

```bash
# 检查端口占用
sudo netstat -tulpn | grep 5000
# 或
sudo lsof -i :5000

# 修改端口（编辑 backend/server.py）
# 找到 app.run() 或 socketio.run()，修改 port 参数
```

#### 问题 2：权限不足

```bash
# 确保目录权限正确
chmod 755 /home/nvidia/yzkj
chmod 755 /home/nvidia/yzkj/config
chmod +x /home/nvidia/yzkj/start_server.sh
```

#### 问题 3：前端构建失败

```bash
# 检查 Node.js 版本（需要 16+）
node --version

# 清除缓存重试
cd frontend
rm -rf node_modules dist
yarn install
yarn build
```

#### 问题 4：模型加载失败

```bash
# 检查模型文件是否存在
ls -lh models/

# 检查模型文件权限
chmod 644 models/*.pt models/*.engine

# 查看详细错误日志
tail -f logs/backend.log
```

#### 问题 5：systemd 服务启动失败 - Werkzeug 生产环境错误

**错误信息**：
```
RuntimeError: The Werkzeug web server is not designed to run in production. 
Pass allow_unsafe_werkzeug=True to the run() method to disable this error.
```

**原因**：Flask-SocketIO 新版本不允许在生产环境使用 Werkzeug 开发服务器。

**解决方案**：

代码已修复，`backend/server.py` 中已添加 `allow_unsafe_werkzeug=True` 参数。

如果仍遇到此问题，请检查代码是否已更新：

```bash
# 检查代码是否包含 allow_unsafe_werkzeug 参数
grep "allow_unsafe_werkzeug" backend/server.py

# 如果未找到，需要手动添加（代码已修复，通常不需要）
```

然后重启服务：

```bash
sudo systemctl restart yolo-detection
sudo systemctl status yolo-detection
```

**注意**：对于高并发生产环境，建议使用 gunicorn + gevent 作为 WSGI 服务器（见下方"生产环境最佳实践"）。

---

## 安装步骤（详细说明）

### 1. 克隆或下载项目

```bash
cd /home/nvidia/yzkj
```

### 2. 安装后端依赖

```bash
pip install -r requirements.txt
```

**注意**：
- 如果遇到 NumPy 版本兼容性问题（如 `AttributeError: _ARRAY_API not found`），请确保使用 NumPy 1.x 版本：
  ```bash
  pip install "numpy>=1.24.0,<2.0.0"
  ```
- 如果需要使用MQTT功能，需要安装 `paho-mqtt` 库：
  ```bash
  pip install paho-mqtt
  ```
- 如果需要使用视频录制和报警事件视频保存功能，需要安装 FFmpeg：
  ```bash
  # Ubuntu/Debian
  sudo apt-get install ffmpeg
  
  # CentOS/RHEL
  sudo yum install ffmpeg
  ```

### 3. 安装前端依赖（可选，仅开发模式需要）

如果使用前端开发服务器（开发模式），需要安装前端依赖：

```bash
cd frontend
yarn install
# 或使用 npm
npm install
```

**注意**：
- 生产模式不需要安装前端依赖（使用构建后的静态文件）
- 开发模式需要安装前端依赖以支持热更新

### 4. 准备 YOLO 模型

确保项目目录中的 `models/` 文件夹下有 YOLO 模型文件，支持以下格式：
- `.pt` (PyTorch 模型)
- `.onnx` (ONNX 模型)
- `.engine` (TensorRT 引擎)

默认使用 `yolo26m_640_int8.engine`，可在前端界面中切换。

### 5. 配置视频源（可选）

默认视频源可在 `backend/server.py` 中修改，或在前端界面中动态设置：

```python
video_path = "rtsp://admin:scyzkj123456@192.168.1.2:554/h264/ch1/main/av_stream"
```

支持：
- RTSP 流：`rtsp://username:password@ip:port/path`
- 本地视频文件：`/path/to/video.mp4`
- 摄像头：`0` 或 `1`（摄像头索引）

## 使用方法

### 启动服务

#### 后端服务

**方式一：使用启动脚本（推荐）**

```bash
./start_server.sh
```

**方式二：直接运行**

```bash
python3 backend/server.py
```

#### 前端开发服务器（开发模式）

如果需要使用前端开发服务器（支持热更新）：

```bash
./start_frontend.sh
```

或者手动启动：

```bash
cd frontend
yarn install  # 首次运行需要安装依赖
yarn dev
```

**前端开发服务器配置**：
- 默认监听地址：`http://0.0.0.0:5173`（支持通过IP访问）
- 自动检测本机IP地址
- 可通过环境变量 `VITE_API_URL` 指定后端地址：
  ```bash
  VITE_API_URL=http://192.168.1.100:5000 ./start_frontend.sh
  ```

### 访问 Web 界面

#### 生产模式（后端提供静态文件）

在浏览器中打开：

```
http://localhost:5000
```

如果服务器运行在其他机器上，请使用对应的 IP 地址：

```
http://<服务器IP>:5000
```

#### 开发模式（前端开发服务器）

前端开发服务器地址：

```
http://localhost:5173
```

或通过IP访问：

```
http://<服务器IP>:5173
```

**注意**：
- 开发模式下，前端由 Vite 开发服务器提供（端口5173）
- 后端API服务运行在端口5000
- 前端会自动代理 `/api` 和 `/socket.io` 请求到后端
- 支持通过IP地址访问，方便远程调试

## 生产部署

### 1. 构建前端

在生产环境中，需要先构建前端代码：

```bash
cd frontend
yarn install  # 如果还没安装依赖
yarn build
```

构建完成后，会在 `frontend/dist/` 目录生成静态文件。

### 2. 配置后端为生产模式

确保后端服务未设置 `VITE_DEV=true` 环境变量，或者直接不设置该变量：

```bash
# 确保没有设置 VITE_DEV 环境变量
unset VITE_DEV

# 或者明确设置为 false
export VITE_DEV=false
```

### 3. 启动后端服务

```bash
./start_server.sh
```

或者：

```bash
python3 backend/server.py
```

后端会自动检测 `frontend/dist/` 目录，如果存在则使用生产模式（提供静态文件），否则使用开发模式（重定向到Vite开发服务器）。

### 4. 访问系统

在浏览器中打开：

```
http://<服务器IP>:5000
```

### 部署检查清单

- [ ] 前端已构建（`frontend/dist/` 目录存在）
- [ ] 后端未设置 `VITE_DEV=true` 环境变量
- [ ] 后端服务正常启动
- [ ] 防火墙允许端口5000访问
- [ ] 模型文件已放置在 `models/` 目录
- [ ] 配置文件目录 `config/` 有写入权限

### 使用 Nginx 反向代理（可选）

如果需要使用 Nginx 作为反向代理，可以配置如下：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 使用 systemd 服务（可选）

创建 systemd 服务文件 `/etc/systemd/system/yolo-detection.service`：

```ini
[Unit]
Description=YOLO Detection and Alarm System
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/home/nvidia/yzkj
Environment="PATH=/usr/bin:/usr/local/bin"
Environment="PYTHONUNBUFFERED=1"
ExecStart=/usr/bin/python3 /home/nvidia/yzkj/backend/server.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**重要提示**：
- 请将 `User=your-user` 替换为实际运行服务的用户名（如 `nvidia`）
- 请将 `WorkingDirectory` 和 `ExecStart` 中的路径替换为实际项目路径
- 代码已修复 Werkzeug 生产环境错误，无需额外配置

启用并启动服务：

```bash
# 重新加载 systemd 配置
sudo systemctl daemon-reload

# 启用服务（开机自启）
sudo systemctl enable yolo-detection

# 启动服务
sudo systemctl start yolo-detection

# 查看服务状态
sudo systemctl status yolo-detection

# 查看日志
sudo journalctl -u yolo-detection -f
```

**如果遇到 Werkzeug 生产环境错误**，请参考"常见部署问题"章节的问题 5。

### 操作说明

#### 1. 系统配置

点击页面顶部的 **"系统配置"** 面板，可以配置：

- **检测模型**：从下拉列表选择要使用的YOLO模型，点击"应用"切换
- **视频URL**：输入新的视频源地址，点击"应用"切换视频源
- **检测类别**：
  - 勾选要检测的类别（支持多选）
  - 为每个类别设置自定义中文名称
  - 为每个类别设置置信度阈值（0-1之间）
  - 点击"全选"/"全不选"快速操作
  - 点击"应用"使配置生效
- **显示设置**：
  - 字体大小：8-72像素
  - 边框粗细：1-10像素
  - 边框颜色：使用颜色选择器或输入RGB值（如：0,255,0）
  - 文字颜色：设置检测标签的文字颜色
  - 显示语言：切换中文/英文显示（英文模式性能更好）
  - 报警区域填充颜色：设置监控区域的填充颜色（RGB格式）
  - 报警区域边框颜色：设置监控区域的边框颜色（RGB格式）
  - 报警区域透明度：设置监控区域的填充透明度（0.0-1.0）
  - 点击"应用显示设置"使配置立即生效（无需刷新页面）
- **报警设置**：
  - 防抖时间（秒）：设置同一目标在多少秒内只报警一次（0-300秒，0表示不防抖）
  - 检测模式：
    - 中心点模式：检测框中心点进入区域时才报警（更严格）
    - 边框模式：检测框任意点进入区域即报警（更敏感）
  - 相同ID只报警一次：启用后，同一ID在整个生命周期内只报警一次（即使离开后再次进入也不报警）
  - 点击"应用报警设置"使配置生效

#### 2. 区域管理（多区域）

系统支持创建和管理多个监控区域：

- **创建区域**：
  1. 在"区域管理"标签页中点击"创建区域"按钮
  2. 在视频画面上用鼠标左键点击，添加多边形顶点
  3. 当鼠标接近起点时，会自动吸附并显示金色高亮
  4. 点击吸附点或双击完成绘制
  5. 输入区域名称，设置区域颜色（填充色和边框色）
  6. 点击"保存"完成创建

- **编辑区域**：点击区域列表中的"编辑"按钮，可以修改区域形状、名称和颜色
- **启用/禁用区域**：通过区域列表中的开关控制区域是否启用
- **删除区域**：点击"删除"按钮可以删除不需要的区域
- **重命名区域**：点击"重命名"按钮可以修改区域名称

**提示**：
- 至少需要 3 个顶点才能形成多边形
- 按 `ESC` 键可以取消绘制
- 双击可以完成绘制
- 每个区域可以独立配置颜色和启用状态

#### 3. 系统配置（扩展功能）

在"系统配置"面板中，还可以配置以下功能：

- **登录设置**：
  - 设置登录用户名和密码
  - 首次使用建议修改默认密码（默认：admin/123456）

- **MQTT设置**：
  - 启用/禁用MQTT功能
  - 配置MQTT服务器地址、端口、主题
  - 配置MQTT认证信息（用户名、密码）
  - 报警消息会自动推送到MQTT服务器

- **遮挡检测设置**：
  - 启用/禁用遮挡检测
  - 设置检测间隔（秒）
  - 设置遮挡阈值（0.0-1.0，值越小越敏感）
  - 当检测到画面被遮挡时会触发报警

- **摄像头状态检测**：
  - 系统自动从RTSP URL提取摄像头IP
  - 自动检测摄像头在线/离线状态
  - 可配置检测间隔（默认5秒）
  - 摄像头离线时会触发报警

- **报警事件保存**：
  - 启用/禁用报警事件视频保存
  - 启用/禁用报警事件图片保存
  - 设置报警事件视频时长（秒）
  - 设置报警事件保存路径

#### 4. 视频录制

系统支持实时视频录制功能：

- **开始录制**：点击"开始录制"按钮开始录制视频
- **停止录制**：点击"停止录制"按钮停止录制
- **录制管理**：
  - 查看录制视频列表
  - 预览录制视频
  - 重命名录制视频
  - 删除录制视频
- **自动分段**：录制视频会自动按配置的时长分段保存（默认5分钟一段）

#### 5. 查看报警信息

- 当检测到目标进入监控区域、摄像头离线或画面被遮挡时，**"报警记录"** 面板会实时显示报警信息
- 报警信息包括：时间、报警类型、目标类别、目标 ID、位置坐标、区域名称
- **报警类型**：
  - **区域报警**：目标进入监控区域
  - **摄像头离线**：摄像头连接断开
  - **画面遮挡**：摄像头画面被遮挡
- 报警行为由报警设置控制：
  - **防抖时间**：同一目标在设定时间内只报警一次（默认5秒）
  - **检测模式**：可选择中心点模式或边框模式
  - **相同ID只报警一次**：启用后，同一ID在整个生命周期内只报警一次

#### 6. 查看检测信息

- **"检测信息"** 面板显示当前检测到的目标信息
- 包括目标类别、目标 ID、置信度、位置坐标
- 在监控区域内的目标会用特殊标记显示

#### 7. 查看系统日志

- **"系统日志"** 面板实时显示系统日志和YOLO推理日志
- 日志按级别和来源用不同颜色区分
- 支持自动滚动和手动清空日志
- 所有日志同时保存到 `logs/` 目录

#### 8. 操作日志

- **"操作日志"** 面板记录用户操作和系统事件
- 包括登录、配置修改、区域管理等操作
- 便于审计和问题排查

## API 接口

### REST API

**注意**：系统已升级为多区域管理，旧的单区域API（`/api/polygon`）已废弃，请使用区域管理API（`/api/zones`）。

#### 获取系统状态
```http
GET /api/status
```

**响应示例**：
```json
{
  "video_connected": true,
  "polygon_defined": true,
  "polygon_points_count": 4,
  "current_model": "yolo26m_640_int8.engine",
  "video_url": "rtsp://...",
  "gpu_available": true,
  "device": "0"
}
```

**字段说明**：
- `gpu_available`: GPU是否可用
- `device`: 使用的设备（"0"表示GPU，0表示第一个GPU，"cpu"表示CPU）

#### 获取模型列表
```http
GET /api/models
```

**响应示例**：
```json
{
  "models": [
    {
      "name": "yolo11n_640.engine",
      "size": 12345678,
      "size_mb": 11.78,
      "current": false
    }
  ],
  "current": "yolo26m_640_int8.engine"
}
```

#### 切换模型
```http
POST /api/model
Content-Type: application/json

{
  "model": "yolo11n_640.engine"
}
```

#### 获取/设置视频URL
```http
GET /api/video
POST /api/video
Content-Type: application/json

{
  "video_url": "rtsp://admin:password@192.168.1.2:554/stream"
}
```

#### 获取类别列表
```http
GET /api/classes
```

**响应示例**：
```json
{
  "classes": [
    {
      "id": 0,
      "name_en": "person",
      "name_cn": "人",
      "enabled": true,
      "custom": false,
      "confidence_threshold": 0.25
    }
  ],
  "enabled_classes": [0],
  "custom_names": {},
  "confidence_thresholds": {},
  "total_classes": 80
}
```

#### 设置启用的类别
```http
POST /api/classes/enabled
Content-Type: application/json

{
  "enabled_classes": [0, 2, 5]
}
```

#### 设置自定义中文名称
```http
POST /api/classes/custom-name
Content-Type: application/json

{
  "class_id": 0,
  "custom_name": "人员"
}
```

#### 设置置信度阈值
```http
POST /api/classes/confidence
Content-Type: application/json

{
  "class_id": 0,
  "confidence_threshold": 0.5
}
```

#### 获取/设置显示配置
```http
GET /api/display
POST /api/display
Content-Type: application/json

{
  "font_size": 20,
  "box_color": [0, 255, 0],
  "box_thickness": 3,
  "text_color": [255, 255, 255],
  "use_chinese": true,
  "zone_fill_color": [255, 0, 0],
  "zone_border_color": [255, 0, 0],
  "zone_fill_alpha": 0.3
}
```

**参数说明**：
- `font_size`: 字体大小（8-72）
- `box_color`: 边框颜色，RGB格式 [R, G, B]（前端发送，后端转换为BGR存储）
- `box_thickness`: 边框粗细（1-10）
- `text_color`: 文字颜色，RGB格式 [R, G, B]
- `use_chinese`: 是否使用中文显示（true=中文，false=英文，英文模式性能更好）
- `zone_fill_color`: 报警区域填充颜色，RGB格式 [R, G, B]（前端发送，后端转换为BGR存储）
- `zone_border_color`: 报警区域边框颜色，RGB格式 [R, G, B]（前端发送，后端转换为BGR存储）
- `zone_fill_alpha`: 报警区域填充透明度（0.0-1.0）

**注意**：
- 前端API返回时，所有颜色值都是RGB格式
- 前端发送时，应使用RGB格式
- 后端内部存储时，`box_color`、`zone_fill_color`、`zone_border_color` 会转换为BGR格式（OpenCV使用BGR）

#### 获取/设置模型类别映射
```http
GET /api/model-classes
POST /api/model-classes
Content-Type: application/json

{
  "model_name": "yolo11n_640.engine",
  "classes_en": ["person", "car", ...],
  "classes_cn": ["人", "汽车", ...]
}
```

#### 获取/设置报警配置
```http
GET /api/alarm
POST /api/alarm
Content-Type: application/json

{
  "debounce_time": 5.0,
  "detection_mode": "center",
  "once_per_id": false,
  "save_event_video": true,
  "save_event_image": true,
  "event_video_duration": 10,
  "event_save_path": "/path/to/alarm_events"
}
```

**参数说明**：
- `debounce_time`: 防抖时间（秒），同一目标在此时间内只报警一次，范围0-300，0表示不防抖
- `detection_mode`: 检测模式，`"center"`=中心点模式，`"edge"`=边框模式
- `once_per_id`: 相同ID是否只报警一次，`true`=整个生命周期只报警一次，`false`=允许重复报警（受防抖时间限制）
- `save_event_video`: 是否保存报警事件视频，`true`=保存，`false`=不保存
- `save_event_image`: 是否保存报警事件图片，`true`=保存，`false`=不保存
- `event_video_duration`: 报警事件视频时长（秒），默认10秒
- `event_save_path`: 报警事件保存路径，默认为项目根目录下的 `alarm_events` 目录

**响应示例**：
```json
{
  "success": true,
  "message": "报警配置已更新",
  "config": {
    "debounce_time": 5.0,
    "detection_mode": "center",
    "once_per_id": false,
    "save_event_video": true,
    "save_event_image": true,
    "event_video_duration": 10,
    "event_save_path": "/path/to/alarm_events"
  }
}
```

#### 登录认证相关API

##### 用户登录
```http
POST /api/login
Content-Type: application/json

{
  "username": "admin",
  "password": "123456"
}
```

**响应示例**：
```json
{
  "success": true,
  "message": "登录成功"
}
```

##### 用户登出
```http
POST /api/logout
```

##### 获取登录状态
```http
GET /api/login/status
```

**响应示例**：
```json
{
  "logged_in": true
}
```

##### 获取/设置登录配置
```http
GET /api/login/config
POST /api/login/config
Content-Type: application/json

{
  "username": "admin",
  "password": "123456"
}
```

#### 区域管理API（多区域）

##### 获取所有区域
```http
GET /api/zones
```

**响应示例**：
```json
{
  "zones": [
    {
      "id": "zone_1",
      "name": "区域1",
      "points": [[100, 200], [300, 200], [300, 400], [100, 400]],
      "enabled": true,
      "color": {
        "fill": [255, 0, 0],
        "border": [255, 0, 0]
      }
    }
  ]
}
```

##### 创建区域
```http
POST /api/zones
Content-Type: application/json

{
  "name": "区域1",
  "points": [[100, 200], [300, 200], [300, 400], [100, 400]],
  "enabled": true,
  "color": {
    "fill": [255, 0, 0],
    "border": [255, 0, 0]
  }
}
```

##### 获取指定区域
```http
GET /api/zones/<zone_id>
```

##### 更新区域
```http
PUT /api/zones/<zone_id>
Content-Type: application/json

{
  "name": "区域1",
  "points": [[100, 200], [300, 200], [300, 400], [100, 400]],
  "enabled": true,
  "color": {
    "fill": [255, 0, 0],
    "border": [255, 0, 0]
  }
}
```

##### 删除区域
```http
DELETE /api/zones/<zone_id>
```

##### 重命名区域
```http
POST /api/zones/<zone_id>/rename
Content-Type: application/json

{
  "name": "新区域名称"
}
```

#### MQTT配置API

##### 获取MQTT配置
```http
GET /api/mqtt
```

**响应示例**：
```json
{
  "enabled": true,
  "host": "192.168.1.100",
  "port": 1883,
  "topic": "CAM1",
  "username": "",
  "password": ""
}
```

##### 设置MQTT配置
```http
POST /api/mqtt
Content-Type: application/json

{
  "enabled": true,
  "host": "192.168.1.100",
  "port": 1883,
  "topic": "CAM1",
  "username": "mqtt_user",
  "password": "mqtt_password"
}
```

**参数说明**：
- `enabled`: 是否启用MQTT功能
- `host`: MQTT服务器地址
- `port`: MQTT服务器端口（默认1883）
- `topic`: MQTT主题名称
- `username`: MQTT用户名（可选）
- `password`: MQTT密码（可选）

**注意**：需要安装 `paho-mqtt` 库：`pip install paho-mqtt`

#### 遮挡检测配置API

##### 获取遮挡检测配置
```http
GET /api/occlusion
```

**响应示例**：
```json
{
  "enabled": true,
  "check_interval": 5.0,
  "occlusion_threshold": 0.5
}
```

##### 设置遮挡检测配置
```http
POST /api/occlusion
Content-Type: application/json

{
  "enabled": true,
  "check_interval": 5.0,
  "occlusion_threshold": 0.5
}
```

**参数说明**：
- `enabled`: 是否启用遮挡检测
- `check_interval`: 检测间隔（秒），默认5.0秒
- `occlusion_threshold`: 遮挡阈值（0.0-1.0），默认0.5，值越小越敏感

#### 视频录制API

##### 获取录制状态
```http
GET /api/recording/status
```

**响应示例**：
```json
{
  "is_recording": false
}
```

##### 开始录制
```http
POST /api/recording/start
```

##### 停止录制
```http
POST /api/recording/stop
```

##### 获取录制配置
```http
GET /api/recording/config
```

**响应示例**：
```json
{
  "save_path": "/path/to/recordings",
  "segment_duration": 300
}
```

##### 设置录制配置
```http
POST /api/recording/config
Content-Type: application/json

{
  "save_path": "/path/to/recordings",
  "segment_duration": 300
}
```

**参数说明**：
- `save_path`: 录制视频保存路径
- `segment_duration`: 分段时长（秒），默认300秒（5分钟）

##### 获取录制视频列表
```http
GET /api/recording/videos
```

##### 获取录制视频
```http
GET /api/recording/videos/<filename>
```

##### 删除录制视频
```http
DELETE /api/recording/videos/<filename>
```

##### 重命名录制视频
```http
POST /api/recording/videos/<filename>/rename
Content-Type: application/json

{
  "new_name": "新文件名.mp4"
}
```

##### 预览录制视频
```http
GET /api/recording/videos/<filename>/preview
```

#### 视频流API

##### 原始视频流（MJPEG）
```http
GET /api/video/stream
```

##### 处理后视频流（包含检测结果和区域绘制）
```http
GET /api/video/processed_stream
```

### WebSocket 事件

#### 客户端 → 服务器

- `connect`：连接服务器
- `disconnect`：断开连接

#### 服务器 → 客户端

- `connected`：连接成功确认
- `frame`：视频帧和检测结果
  ```json
  {
    "frame": "data:image/jpeg;base64,...",
    "polygon": [[100, 200], [300, 200], [300, 400], [100, 400]],
    "fps": 30.5,
    "resolution": {
      "width": 1920,
      "height": 1080
    },
    "detections": [
      {
        "id": 1,
        "class_id": 0,
        "class_name": "person",
        "class_name_cn": "人",
        "bbox": [150, 250, 200, 350],
        "center": {"x": 175, "y": 300},
        "confidence": 0.95,
        "in_zone": true
      }
    ]
  }
  ```
- `log`：系统日志
  ```json
  {
    "timestamp": "2024-01-01 12:00:00",
    "level": "INFO",
    "logger": "backend",
    "message": "模型已加载: yolo11n_640.engine (将使用GPU模式)"
  }
  ```
- `alarm`：报警信息
  ```json
  {
    "time": "2024-01-01 12:00:00",
    "track_id": 1,
    "class_id": 0,
    "class_name_cn": "人",
    "object_name": "人",
    "position": {"x": 175, "y": 300},
    "alarm_type": "zone",
    "zone_id": "zone_1",
    "zone_name": "区域1"
  }
  ```
  
  **报警类型说明**：
  - `"zone"`: 区域报警（目标进入监控区域）
  - `"camera_offline"`: 摄像头离线报警
  - `"occlusion"`: 画面遮挡报警

## 项目结构

```
yzkj/
├── backend/
│   └── server.py              # Flask 后端服务
├── frontend/                   # 前端文件（Vue3 + Vite）
│   ├── src/                    # 源代码目录
│   │   ├── components/         # Vue组件
│   │   │   ├── VideoPanel.vue  # 视频面板组件
│   │   │   ├── ConfigPanel.vue # 配置面板组件
│   │   │   ├── AlarmList.vue   # 报警列表组件
│   │   │   ├── DetectionInfo.vue # 检测信息组件
│   │   │   ├── LogPanel.vue    # 日志面板组件
│   │   │   ├── ZoneManager.vue  # 区域管理组件
│   │   │   └── VideoMonitor.vue # 视频监控组件
│   │   ├── views/              # 视图组件
│   │   │   ├── LoginView.vue   # 登录页面
│   │   │   └── MainView.vue    # 主页面
│   │   ├── router/             # 路由配置
│   │   │   └── index.js        # 路由定义
│   │   └── App.vue             # 主应用组件
│   ├── dist/                   # 构建输出目录（生产模式）
│   ├── vite.config.js          # Vite配置文件
│   ├── package.json            # 依赖配置
│   └── start_frontend.sh       # 前端启动脚本
├── models/                     # YOLO模型目录
│   ├── yolo11n_640.engine
│   ├── yolo11s.pt
│   ├── yolo11m.pt
│   ├── yolo11l.pt
│   ├── yolo11x.pt
│   └── yolo26m_640_int8.engine
├── config/                     # 配置文件目录
│   ├── zones_config.json       # 多区域配置（自动生成）
│   ├── system_config.json      # 系统配置（模型、视频URL、摄像头IP等，自动生成）
│   ├── classes_config.json     # 类别配置（启用类别、自定义名称、置信度，自动生成）
│   ├── display_config.json     # 显示配置（字体、颜色等，自动生成）
│   ├── model_classes.json      # 模型类别映射配置（自动生成）
│   ├── alarm_config.json       # 报警配置（防抖时间、检测模式、事件保存等，自动生成）
│   ├── occlusion_config.json   # 遮挡检测配置（自动生成）
│   ├── mqtt_config.json        # MQTT配置（自动生成）
│   ├── login_config.json       # 登录配置（自动生成）
│   ├── recording_config.json   # 录制配置（自动生成）
│   └── secret_key.txt          # Session密钥（自动生成）
├── logs/                       # 日志文件目录
│   ├── backend.log             # 后端系统日志
│   └── yolo.log                # YOLO推理日志
├── recordings/                 # 录制视频目录（自动生成）
│   └── *.mp4                   # 录制的视频文件
├── alarm_events/               # 报警事件目录（自动生成）
│   ├── videos/                 # 报警事件视频
│   └── images/                 # 报警事件图片
├── requirements.txt            # Python 依赖
├── start_server.sh             # 后端启动脚本
├── start_frontend.sh           # 前端开发服务器启动脚本
└── README.md                   # 本文件
```

## 配置说明

### 配置文件说明

系统使用多个JSON配置文件来保存各种设置，所有配置文件都会自动生成：

1. **config/zones_config.json** - 多区域配置
```json
{
  "zones": [
    {
      "id": "zone_1",
      "name": "区域1",
      "points": [[100, 200], [300, 200], [300, 400], [100, 400]],
      "enabled": true,
      "color": {
        "fill": [255, 0, 0],
        "border": [255, 0, 0]
      }
    }
  ]
}
```
坐标单位为像素，相对于原始视频分辨率。支持多个区域，每个区域可独立配置名称、颜色和启用状态。

2. **config/system_config.json** - 系统配置（模型、视频URL、摄像头IP等）
   ```json
   {
     "model": "yolo26m_640_int8.engine",
     "video_url": "rtsp://admin:password@192.168.1.2:554/stream",
     "camera_ip": "192.168.1.2",
     "camera_check_interval": 5.0
   }
   ```
   - `camera_ip`: 摄像头IP地址（自动从RTSP URL提取）
   - `camera_check_interval`: 摄像头状态检测间隔（秒）

3. **config/classes_config.json** - 类别配置
   ```json
   {
     "enabled_classes": [0, 2, 5],
     "custom_names": {
       "0": "人员",
       "2": "车辆"
     },
     "confidence_thresholds": {
       "0": 0.5,
       "2": 0.6
     }
   }
   ```

4. **config/display_config.json** - 显示配置
   ```json
   {
     "font_size": 16,
     "box_color": [0, 255, 0],
     "box_thickness": 2,
     "text_color": [0, 0, 0],
     "use_chinese": true,
     "zone_fill_color": [255, 0, 0],
     "zone_border_color": [255, 0, 0],
     "zone_fill_alpha": 0.3
   }
   ```
   注意：
   - `box_color` 使用BGR格式（后端存储），前端API返回时转换为RGB格式
   - `text_color` 使用RGB格式
   - `zone_fill_color` 和 `zone_border_color` 使用RGB格式（前端API返回时），后端存储时转换为BGR格式
   - `zone_fill_alpha` 为报警区域填充透明度，范围0.0-1.0
   - `use_chinese`: true=中文显示（使用PIL渲染），false=英文显示（使用OpenCV原生，性能更好）
   - 配置修改后立即生效，无需重启服务

5. **config/model_classes.json** - 模型类别映射配置
   ```json
   {
     "default": {
       "classes_en": ["person", "bicycle", ...],
       "classes_cn": ["人", "自行车", ...]
     },
     "yolo11n_640.engine": {
       "classes_en": ["person", "car", ...],
       "classes_cn": ["人", "汽车", ...]
     }
   }
   ```
   每个模型可以有自己的类别映射，如果模型没有配置，会使用 `default` 配置。

6. **config/occlusion_config.json** - 遮挡检测配置
   ```json
   {
     "enabled": true,
     "check_interval": 5.0,
     "occlusion_threshold": 0.5
   }
   ```
   - `enabled`: 是否启用遮挡检测
   - `check_interval`: 检测间隔（秒）
   - `occlusion_threshold`: 遮挡阈值（0.0-1.0），值越小越敏感

7. **config/mqtt_config.json** - MQTT配置
   ```json
   {
     "enabled": true,
     "host": "192.168.1.100",
     "port": 1883,
     "topic": "CAM1",
     "username": "",
     "password": ""
   }
   ```
   - `enabled`: 是否启用MQTT功能
   - `host`: MQTT服务器地址
   - `port`: MQTT服务器端口
   - `topic`: MQTT主题名称
   - `username`: MQTT用户名（可选）
   - `password`: MQTT密码（可选）

8. **config/login_config.json** - 登录配置
   ```json
   {
     "username": "admin",
     "password": "123456"
   }
   ```
   存储登录用户名和密码（建议首次使用后修改默认密码）

9. **config/recording_config.json** - 录制配置
   ```json
   {
     "save_path": "/path/to/recordings",
     "segment_duration": 300
   }
   ```
   - `save_path`: 录制视频保存路径
   - `segment_duration`: 分段时长（秒），默认300秒（5分钟）

### 报警配置

报警配置保存在 `config/alarm_config.json`，可通过前端界面或API进行设置：

```json
{
  "debounce_time": 5.0,
  "detection_mode": "center",
  "once_per_id": false,
  "save_event_video": true,
  "save_event_image": true,
  "event_video_duration": 10,
  "event_save_path": "/path/to/alarm_events"
}
```

**配置说明**：
- `debounce_time`: 防抖时间（秒），同一目标在此时间内只报警一次
  - 范围：0-300秒
  - 0表示不防抖，每次进入都报警
  - 默认值：5.0秒
- `detection_mode`: 检测模式
  - `"center"`: 中心点模式，检测框中心点进入区域时才报警（更严格，适合需要目标完全进入区域）
  - `"edge"`: 边框模式，检测框任意点进入区域即报警（更敏感，检测框一接触区域边界就报警）
  - 默认值：`"center"`
- `once_per_id`: 相同ID是否只报警一次
  - `true`: 同一ID在整个跟踪生命周期内只报警一次（即使离开后再次进入也不报警）
  - `false`: 允许重复报警，但受防抖时间限制
  - 默认值：`false`

**报警判断逻辑**：
- **中心点模式**：计算检测框的中心点坐标，判断中心点是否在多边形区域内
- **边框模式**：检查检测框的四个角点和中心点，任意一点在多边形内即触发报警

**使用建议**：
- 需要持续监控但避免短时间内重复报警：使用防抖时间模式（`once_per_id = false`）
- 只需要首次进入报警：启用"相同ID只报警一次"（`once_per_id = true`）
- 需要更严格的进入判断：使用中心点模式（`detection_mode = "center"`）
- 需要更敏感的报警：使用边框模式（`detection_mode = "edge"`）

**报警事件保存**：
- `save_event_video`: 是否保存报警事件视频（使用ffmpeg从RTSP流录制）
- `save_event_image`: 是否保存报警事件图片（保存当前帧）
- `event_video_duration`: 报警事件视频时长（秒），默认10秒
- `event_save_path`: 报警事件保存路径，默认为项目根目录下的 `alarm_events` 目录
- 保存的文件命名格式：`alarm_YYYYMMDD_HHMMSS_ID{track_id}_{object_name}_{zone_name}.mp4/jpg`

### GPU和性能设置

系统会自动检测GPU可用性：
- 如果检测到GPU，自动使用GPU模式
- 如果没有GPU或GPU不可用，自动切换到CPU模式
- 可通过 `/api/status` 接口查看当前使用的设备

### 日志系统

系统日志分为两类：
- **后端日志** (`logs/backend.log`)：系统运行日志、配置加载日志等
- **YOLO推理日志** (`logs/yolo.log`)：YOLO模型推理相关的日志

所有日志：
- 自动保存到 `logs/` 目录
- 支持日志轮转（每个文件最大10MB，保留5个备份）
- 前端可实时查看（在"系统日志"面板）
- 按日志级别和来源用不同颜色区分

## 常见问题

### 1. NumPy 版本兼容性错误

**错误信息**：
```
AttributeError: _ARRAY_API not found
ImportError: numpy.core.multiarray failed to import
```

**解决方案**：
```bash
pip install "numpy>=1.24.0,<2.0.0" --force-reinstall
```

### 2. 视频流连接失败

**可能原因**：
- RTSP 地址错误
- 网络连接问题
- 视频源不可用

**解决方案**：
- 检查 RTSP 地址是否正确
- 确认网络连接正常
- 查看控制台输出的错误信息

### 3. 检测不到目标

**可能原因**：
- YOLO 模型未正确加载
- 视频分辨率过低
- 目标距离过远
- 类别未启用
- 置信度阈值设置过高

**解决方案**：
- 确认模型文件存在且格式正确
- 检查视频流是否正常
- 在前端界面中检查类别是否已启用
- 调整置信度阈值（在前端界面中为每个类别设置）
- 检查模型类别映射是否正确

### 4. WebSocket 连接失败

**可能原因**：
- 防火墙阻止端口 5000
- 服务器未启动

**解决方案**：
- 检查防火墙设置
- 确认服务器正在运行
- 检查浏览器控制台的错误信息

### 5. 中文显示乱码

**可能原因**：
- 系统未安装中文字体

**解决方案**：
- 安装中文字体（见"中文字体支持"章节）
- 重启服务器

### 6. 模型类别不匹配

**可能原因**：
- 使用的模型不是COCO数据集训练的
- 模型类别映射配置错误

**解决方案**：
- 通过API或直接编辑 `config/model_classes.json` 配置模型类别映射
- 确保类别数量与模型输出一致

### 7. 帧率过低

**可能原因**：
- 使用中文显示模式（PIL渲染性能较低）
- 视频分辨率过高
- GPU未正确使用

**解决方案**：
- 切换到英文显示模式（性能更好，可提升数倍帧率）
- 降低视频分辨率
- 检查GPU是否正确检测和使用（查看系统状态API）

### 8. 日志不显示

**可能原因**：
- WebSocket连接问题
- 日志队列阻塞

**解决方案**：
- 检查浏览器控制台是否有错误
- 确认WebSocket连接正常（查看连接状态）
- 重启服务

### 9. 前端无法通过IP访问

**可能原因**：
- Vite开发服务器默认只监听localhost
- 防火墙阻止端口5173

**解决方案**：
- 使用 `./start_frontend.sh` 启动脚本（已配置为监听0.0.0.0）
- 检查防火墙设置，确保端口5173可访问
- 如果后端在不同机器，设置 `VITE_API_URL` 环境变量：
  ```bash
  VITE_API_URL=http://<后端IP>:5000 ./start_frontend.sh
  ```

### 10. 显示设置不生效

**可能原因**：
- 配置文件缓存问题
- 前端未重新加载配置

**解决方案**：
- 点击"应用显示设置"后，配置会立即生效（无需刷新页面）
- 如果仍不生效，检查浏览器控制台是否有错误
- 确认后端服务正常运行
- 检查 `config/display_config.json` 文件是否正确保存

### 11. MQTT消息发送失败

**可能原因**：
- MQTT服务器地址或端口配置错误
- 网络连接问题
- MQTT认证信息错误
- `paho-mqtt` 库未安装

**解决方案**：
- 检查MQTT配置是否正确（服务器地址、端口、主题）
- 确认网络连接正常，可以访问MQTT服务器
- 检查MQTT用户名和密码是否正确
- 安装MQTT库：`pip install paho-mqtt`
- 查看后端日志了解详细错误信息

### 12. 无法登录系统

**可能原因**：
- 用户名或密码错误
- Session配置问题

**解决方案**：
- 检查登录配置（默认用户名：admin，密码：123456）
- 首次使用建议修改默认密码
- 清除浏览器Cookie后重试
- 检查 `config/secret_key.txt` 文件是否存在

### 13. 摄像头状态检测不准确

**可能原因**：
- 摄像头IP地址配置错误
- 网络延迟或丢包
- 检测间隔设置过短

**解决方案**：
- 确认摄像头IP地址正确（系统会自动从RTSP URL提取）
- 检查网络连接质量
- 适当增加检测间隔（默认5秒）
- 查看系统日志了解详细检测信息

### 14. 遮挡检测误报

**可能原因**：
- 遮挡阈值设置过低
- 视频画面质量差
- 光照条件变化

**解决方案**：
- 适当提高遮挡阈值（默认0.5，可尝试0.6-0.8）
- 检查视频画面质量
- 如果不需要遮挡检测，可以在配置中禁用

### 15. 报警事件视频保存失败

**可能原因**：
- FFmpeg未安装
- 保存路径无写入权限
- RTSP流连接失败

**解决方案**：
- 安装FFmpeg：`sudo apt-get install ffmpeg` 或 `sudo yum install ffmpeg`
- 检查保存路径的写入权限
- 确认RTSP流连接正常
- 查看后端日志了解详细错误信息

### 16. 视频录制功能不可用

**可能原因**：
- FFmpeg未安装
- 保存路径无写入权限
- 录制配置错误

**解决方案**：
- 安装FFmpeg：`sudo apt-get install ffmpeg` 或 `sudo yum install ffmpeg`
- 检查录制保存路径的写入权限
- 检查录制配置是否正确
- 查看后端日志了解详细错误信息

## 性能优化建议

1. **使用 TensorRT 引擎**：将模型转换为 `.engine` 格式以获得最佳性能
2. **使用英文显示模式**：切换到英文显示可以显著提升帧率（避免PIL图像转换开销）
3. **调整视频分辨率**：降低视频分辨率可以提高处理速度
4. **GPU 加速**：确保使用支持 CUDA 的 GPU（系统会自动检测）
5. **网络优化**：对于 RTSP 流，确保网络带宽充足
6. **类别过滤**：只启用需要检测的类别，减少处理开销
7. **置信度阈值**：合理设置置信度阈值，过滤低置信度检测

## 开发说明

### 配置模型类别映射

如果使用非COCO数据集训练的模型，需要配置对应的类别映射：

1. **通过API配置**：
   ```bash
   curl -X POST http://localhost:5000/api/model-classes \
     -H "Content-Type: application/json" \
     -d '{
       "model_name": "your_model.engine",
       "classes_en": ["class1", "class2", ...],
       "classes_cn": ["类别1", "类别2", ...]
     }'
   ```

2. **直接编辑配置文件**：
   编辑 `config/model_classes.json`，添加或修改模型配置：
   ```json
   {
     "your_model.engine": {
       "classes_en": ["class1", "class2", ...],
       "classes_cn": ["类别1", "类别2", ...]
     }
   }
   ```

### 类别管理

- 在前端界面中可以选择要检测的类别
- 可以为每个类别设置自定义中文名称
- 可以为每个类别设置独立的置信度阈值
- 所有配置会自动保存到 `config/classes_config.json`

### 添加其他报警方式

在 `backend/server.py` 的 `trigger_alarm` 函数中可以添加：

- 播放声音
- 发送 HTTP 请求
- 保存截图
- 发送邮件/短信等

示例：

```python
def trigger_alarm(track_id, bbox_center, class_id=None, class_name_cn=None):
    # ... 现有代码 ...
    
    # 保存截图
    if latest_frame is not None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        cv2.imwrite(f"alarm_{timestamp}_id{track_id}.jpg", latest_frame)
    
    # 发送 HTTP 请求
    import requests
    requests.post("http://your-api-endpoint", json=alarm_data)
```

### 中文字体支持

如果视频画面上的中文显示为方块或乱码，需要安装中文字体：

**Ubuntu/Debian**：
```bash
sudo apt-get install fonts-wqy-microhei fonts-wqy-zenhei
```

**CentOS/RHEL**：
```bash
sudo yum install wqy-microhei-fonts wqy-zenhei-fonts
```

安装后重启服务器即可正常显示中文。

## 许可证

本项目仅供学习和研究使用。

## 更新日志

### v3.0.0
- ✨ 添加MQTT功能支持报警消息推送，支持第三方系统集成
- ✨ 添加用户登录认证功能，保护系统安全
- ✨ 实现多区域检测与报警功能，支持同时监控多个区域
- ✨ 添加摄像头状态检测功能，自动检测摄像头在线/离线
- ✨ 添加遮挡检测功能，检测摄像头画面是否被遮挡
- ✨ 添加报警事件保存功能，自动保存报警事件的视频和图片
- ✨ 重构前端架构，使用路由管理，分离登录页面和主页面
- ✨ 添加视频录制功能，支持分段录制和管理
- ✨ 添加操作日志功能，记录用户操作和系统事件
- ✨ 优化报警系统，增加报警类型区分（区域报警、摄像头离线、画面遮挡）
- 🎨 重构界面布局，将区域管理、日志和设置整合为顶部标签页导航
- 📝 完善README文档，添加新功能详细说明

### v2.3.0
- ✨ 前端支持通过IP地址访问（不再限制localhost）
- ✨ 显示设置立即生效，无需刷新页面
- ✨ 前端绘制监控区域使用配置的颜色（支持自定义报警区域颜色）
- 🐛 修复显示设置应用后不生效的问题
- 🎨 优化报警区域绘制顺序（先绘制边框再绘制填充，确保边框可见）
- 📝 更新README文档，添加前端开发服务器使用说明

### v2.2.0
- ✨ 添加报警配置功能（前端可配置防抖时间、检测模式、相同ID只报警一次）
- ✨ 支持两种检测模式：中心点模式和边框模式
- ✨ 支持相同ID只报警一次选项（整个生命周期内只报警一次）
- 🐛 修复stream=True模式下的结果处理问题
- 📝 完善README文档，添加报警配置详细说明

### v2.1.0
- ✨ 添加GPU自动检测功能，无GPU时自动使用CPU
- ✨ 添加实时帧率和分辨率显示
- ✨ 添加中英文显示切换功能（英文模式性能更优）
- ✨ 添加日志系统（后端日志和YOLO推理日志分离）
- ✨ 前端实时查看系统日志
- 📁 配置文件统一管理到config目录
- 🐛 修复FPS计算问题
- 🎨 优化日志显示界面

### v2.0.0
- ✨ 支持多类别检测（80个COCO类别）
- ✨ 支持模型动态切换
- ✨ 支持视频源动态切换
- ✨ 支持类别选择和管理
- ✨ 支持自定义中文名称
- ✨ 支持自定义置信度阈值
- ✨ 支持显示样式定制（字体、颜色等）
- ✨ 支持模型类别映射配置
- 🐛 修复中文显示乱码问题
- 🎨 优化用户界面

### v1.0.0
- 初始版本发布
- 支持实时人员检测
- 支持自定义多边形监控区域
- 支持 Web 界面操作
- 支持报警功能

## 联系方式

如有问题或建议，请提交 Issue 或联系开发者。

