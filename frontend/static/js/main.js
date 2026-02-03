// WebSocket连接
const socket = io();

// DOM元素
const videoCanvas = document.getElementById('video-canvas');
const drawCanvas = document.getElementById('draw-canvas');
const videoCtx = videoCanvas.getContext('2d');
const drawCtx = drawCanvas.getContext('2d');
const connectionStatus = document.getElementById('connection-status');
const polygonStatus = document.getElementById('polygon-status');
const alarmList = document.getElementById('alarm-list');
const detectionInfo = document.getElementById('detection-info');
const drawPolygonBtn = document.getElementById('draw-polygon-btn');
const clearPolygonBtn = document.getElementById('clear-polygon-btn');
const savePolygonBtn = document.getElementById('save-polygon-btn');
const drawingHint = document.getElementById('drawing-hint');
const toggleConfigBtn = document.getElementById('toggle-config-btn');
const configContent = document.getElementById('config-content');
const modelSelect = document.getElementById('model-select');
const applyModelBtn = document.getElementById('apply-model-btn');
const videoUrlInput = document.getElementById('video-url-input');
const applyVideoBtn = document.getElementById('apply-video-btn');
const classesListContainer = document.getElementById('classes-list');
const selectAllClassesBtn = document.getElementById('select-all-classes-btn');
const deselectAllClassesBtn = document.getElementById('deselect-all-classes-btn');
const applyClassesBtn = document.getElementById('apply-classes-btn');
const fontSizeInput = document.getElementById('font-size-input');
const boxThicknessInput = document.getElementById('box-thickness-input');
const boxColorInput = document.getElementById('box-color-input');
const boxColorRgb = document.getElementById('box-color-rgb');
const textColorInput = document.getElementById('text-color-input');
const textColorRgb = document.getElementById('text-color-rgb');
const applyDisplayBtn = document.getElementById('apply-display-btn');
const toggleLanguageBtn = document.getElementById('toggle-language-btn');
const languageStatus = document.getElementById('language-status');
const logContainer = document.getElementById('log-container');
const clearLogsBtn = document.getElementById('clear-logs-btn');
const autoScrollLogs = document.getElementById('auto-scroll-logs');
const debounceTimeInput = document.getElementById('debounce-time-input');
const detectionModeSelect = document.getElementById('detection-mode-select');
const oncePerIdCheckbox = document.getElementById('once-per-id-checkbox');
const applyAlarmBtn = document.getElementById('apply-alarm-btn');

// 类别数据
let classesData = [];
let enabledClasses = [];

// 状态变量
let isDrawing = false;
let polygonPoints = [];
let currentPolygon = [];
let videoWidth = 0;
let videoHeight = 0;
let detections = [];
let mouseX = 0;
let mouseY = 0;
const SNAP_DISTANCE = 20; // 吸附距离（像素）

// 初始化画布大小
function resizeCanvases() {
    const container = document.querySelector('.video-container');
    const width = container.clientWidth;
    const height = container.clientHeight;
    
    videoCanvas.width = width;
    videoCanvas.height = height;
    drawCanvas.width = width;
    drawCanvas.height = height;
}

window.addEventListener('resize', resizeCanvases);
resizeCanvases();

// WebSocket事件
socket.on('connect', () => {
    console.log('已连接到服务器');
    connectionStatus.textContent = '已连接';
    connectionStatus.className = 'status-indicator connected';
    loadPolygon();
    loadModels();
    loadVideoUrl();
    loadClasses();
    loadDisplayConfig();
});

socket.on('disconnect', () => {
    console.log('与服务器断开连接');
    connectionStatus.textContent = '未连接';
    connectionStatus.className = 'status-indicator disconnected';
});

socket.on('connected', (data) => {
    console.log('服务器消息:', data.message);
});

socket.on('frame', (data) => {
    // 显示视频帧
    const img = new Image();
    img.onload = () => {
        videoCtx.clearRect(0, 0, videoCanvas.width, videoCanvas.height);
        videoCtx.drawImage(img, 0, 0, videoCanvas.width, videoCanvas.height);
        
        // 更新视频尺寸
        if (videoWidth !== img.width || videoHeight !== img.height) {
            videoWidth = img.width;
            videoHeight = img.height;
        }
    };
    img.src = data.frame;
    
    // 更新帧率和分辨率显示
    if (data.fps !== undefined) {
        const fpsDisplay = document.getElementById('fps-display');
        if (fpsDisplay) {
            fpsDisplay.textContent = `FPS: ${data.fps.toFixed(1)}`;
        }
    }
    if (data.resolution) {
        const resolutionDisplay = document.getElementById('resolution-display');
        if (resolutionDisplay) {
            resolutionDisplay.textContent = `分辨率: ${data.resolution.width}x${data.resolution.height}`;
        }
    }
    
    // 更新多边形状态（仅在非绘制模式下更新）
    if (!isDrawing) {
        if (data.polygon && data.polygon.length >= 3) {
            currentPolygon = data.polygon;
            updatePolygonStatus(true);
            drawPolygonOnCanvas(data.polygon);
        } else {
            currentPolygon = [];
            updatePolygonStatus(false);
            drawCtx.clearRect(0, 0, drawCanvas.width, drawCanvas.height);
        }
    }
    
    // 更新检测信息
    detections = data.detections || [];
    updateDetectionInfo(detections);
});

socket.on('alarm', (data) => {
    console.log('报警:', data);
    addAlarmItem(data);
});

// 接收日志
socket.on('log', (data) => {
    console.log('收到日志:', data);  // 调试信息
    addLogEntry(data);
});

// 添加日志条目
function addLogEntry(logData) {
    if (!logContainer) return;
    
    // 移除空消息提示
    const emptyMsg = logContainer.querySelector('.empty-message');
    if (emptyMsg) {
        emptyMsg.remove();
    }
    
    const logEntry = document.createElement('div');
    logEntry.className = `log-entry log-${logData.logger} log-${logData.level}`;
    
    const timestamp = document.createElement('span');
    timestamp.className = 'log-timestamp';
    timestamp.textContent = logData.timestamp;
    
    const level = document.createElement('span');
    level.className = 'log-level';
    level.textContent = `[${logData.level}]`;
    
    const message = document.createElement('span');
    message.textContent = logData.message;
    
    logEntry.appendChild(timestamp);
    logEntry.appendChild(level);
    logEntry.appendChild(message);
    
    logContainer.appendChild(logEntry);
    
    // 自动滚动到底部
    if (autoScrollLogs && autoScrollLogs.checked) {
        logContainer.scrollTop = logContainer.scrollHeight;
    }
    
    // 限制日志条数，避免内存占用过大
    const maxLogs = 1000;
    while (logContainer.children.length > maxLogs) {
        logContainer.removeChild(logContainer.firstChild);
    }
}

// 清空日志
if (clearLogsBtn) {
    clearLogsBtn.addEventListener('click', () => {
        if (logContainer) {
            logContainer.innerHTML = '<p class="empty-message">日志已清空</p>';
        }
    });
}

// 绘制多边形到画布
function drawPolygonOnCanvas(points) {
    if (!points || points.length < 3) return;
    
    drawCtx.clearRect(0, 0, drawCanvas.width, drawCanvas.height);
    
    // 计算缩放比例
    const scaleX = drawCanvas.width / videoWidth;
    const scaleY = drawCanvas.height / videoHeight;
    
    drawCtx.strokeStyle = '#00FFFF';
    drawCtx.lineWidth = 3;
    drawCtx.fillStyle = 'rgba(0, 255, 255, 0.3)';
    
    drawCtx.beginPath();
    points.forEach((point, index) => {
        const x = point[0] * scaleX;
        const y = point[1] * scaleY;
        if (index === 0) {
            drawCtx.moveTo(x, y);
        } else {
            drawCtx.lineTo(x, y);
        }
    });
    drawCtx.closePath();
    drawCtx.fill();
    drawCtx.stroke();
    
    // 绘制顶点
    points.forEach(point => {
        const x = point[0] * scaleX;
        const y = point[1] * scaleY;
        drawCtx.fillStyle = '#00FFFF';
        drawCtx.beginPath();
        drawCtx.arc(x, y, 5, 0, Math.PI * 2);
        drawCtx.fill();
    });
}

// 更新多边形状态显示
function updatePolygonStatus(defined) {
    if (defined) {
        polygonStatus.textContent = `已设置区域 (${currentPolygon.length}个顶点)`;
        polygonStatus.style.background = 'rgba(76, 175, 80, 0.3)';
    } else {
        polygonStatus.textContent = '未设置区域';
        polygonStatus.style.background = 'rgba(255, 255, 255, 0.2)';
    }
}

// 添加报警项
function addAlarmItem(alarmData) {
    const emptyMsg = alarmList.querySelector('.empty-message');
    if (emptyMsg) {
        emptyMsg.remove();
    }
    
    const objectName = alarmData.object_name || alarmData.class_name_cn || '对象';
    const trackId = alarmData.track_id !== undefined ? alarmData.track_id : alarmData.person_id;
    
    const alarmItem = document.createElement('div');
    alarmItem.className = 'alarm-item';
    alarmItem.innerHTML = `
        <div class="time">${alarmData.time}</div>
        <div class="info">
            <span class="object-name">${objectName}</span> <span class="person-id">ID: ${trackId}</span> 进入监控区域
            <br>位置: (${alarmData.position.x.toFixed(0)}, ${alarmData.position.y.toFixed(0)})
        </div>
    `;
    
    alarmList.insertBefore(alarmItem, alarmList.firstChild);
    
    // 限制最多显示20条报警记录
    const items = alarmList.querySelectorAll('.alarm-item');
    if (items.length > 20) {
        items[items.length - 1].remove();
    }
}

// 更新检测信息
function updateDetectionInfo(detections) {
    if (detections.length === 0) {
        detectionInfo.innerHTML = '<p class="empty-message">等待检测数据...</p>';
        return;
    }
    
    detectionInfo.innerHTML = '';
    detections.forEach(det => {
        const className = det.class_name_cn || det.class_name || '对象';
        const item = document.createElement('div');
        item.className = `detection-item ${det.in_zone ? 'in-zone' : ''}`;
        item.innerHTML = `
            <div>
                <span class="class-name">${className}</span>
                <span class="id"> ID: ${det.id}</span>
                ${det.in_zone ? '<span style="color: #f44336; margin-left: 10px;">⚠️ 在区域内</span>' : ''}
            </div>
            <div class="details">
                置信度: ${(det.confidence * 100).toFixed(1)}% | 
                位置: (${det.center.x.toFixed(0)}, ${det.center.y.toFixed(0)})
            </div>
        `;
        detectionInfo.appendChild(item);
    });
}

// 绘制多边形按钮
drawPolygonBtn.addEventListener('click', () => {
    if (isDrawing) {
        cancelDrawing();
    } else {
        startDrawing();
    }
});

// 开始绘制
function startDrawing() {
    isDrawing = true;
    polygonPoints = [];
    drawPolygonBtn.textContent = '取消绘制 (ESC)';
    drawPolygonBtn.classList.add('btn-secondary');
    drawingHint.style.display = 'block';
    
    drawCanvas.addEventListener('click', handleCanvasClick);
    drawCanvas.addEventListener('mousemove', handleCanvasMouseMove);
    drawCanvas.addEventListener('dblclick', finishDrawing);
    document.addEventListener('keydown', handleKeyPress);
}

// 取消绘制
function cancelDrawing() {
    isDrawing = false;
    polygonPoints = [];
    drawPolygonBtn.textContent = '绘制监控区域';
    drawPolygonBtn.classList.remove('btn-secondary');
    drawingHint.style.display = 'none';
    
    drawCtx.clearRect(0, 0, drawCanvas.width, drawCanvas.height);
    drawCanvas.removeEventListener('click', handleCanvasClick);
    drawCanvas.removeEventListener('mousemove', handleCanvasMouseMove);
    drawCanvas.removeEventListener('dblclick', finishDrawing);
    document.removeEventListener('keydown', handleKeyPress);
}

// 完成绘制
function finishDrawing() {
    if (polygonPoints.length < 3) {
        alert('至少需要3个顶点才能形成多边形');
        return;
    }
    
    // 将画布坐标转换为视频坐标
    const scaleX = videoWidth / drawCanvas.width;
    const scaleY = videoHeight / drawCanvas.height;
    
    const videoPolygon = polygonPoints.map(point => [
        point[0] * scaleX,
        point[1] * scaleY
    ]);
    
    savePolygonToServer(videoPolygon);
    cancelDrawing();
}

// 处理画布点击
function handleCanvasClick(event) {
    if (!isDrawing) return;
    
    const rect = drawCanvas.getBoundingClientRect();
    let x = event.clientX - rect.left;
    let y = event.clientY - rect.top;
    
    // 检查是否接近第一个点（吸附功能）
    if (polygonPoints.length >= 2) {
        const firstPoint = polygonPoints[0];
        const distance = Math.sqrt(
            Math.pow(x - firstPoint[0], 2) + Math.pow(y - firstPoint[1], 2)
        );
        
        if (distance < SNAP_DISTANCE) {
            // 吸附到第一个点，闭合多边形
            finishDrawing();
            return;
        }
    }
    
    polygonPoints.push([x, y]);
    drawPolygonPreview();
}

// 处理鼠标移动
function handleCanvasMouseMove(event) {
    if (!isDrawing) return;
    
    const rect = drawCanvas.getBoundingClientRect();
    mouseX = event.clientX - rect.left;
    mouseY = event.clientY - rect.top;
    
    // 重绘预览（包括鼠标位置）
    drawPolygonPreview();
}

// 绘制多边形预览
function drawPolygonPreview() {
    drawCtx.clearRect(0, 0, drawCanvas.width, drawCanvas.height);
    
    if (polygonPoints.length === 0) {
        // 即使没有点，也显示鼠标位置
        drawCtx.fillStyle = '#00FF00';
        drawCtx.beginPath();
        drawCtx.arc(mouseX, mouseY, 6, 0, Math.PI * 2);
        drawCtx.fill();
        drawCtx.strokeStyle = '#FFFFFF';
        drawCtx.lineWidth = 2;
        drawCtx.stroke();
        return;
    }
    
    // 设置更明显的线条样式
    drawCtx.strokeStyle = '#00FF00';
    drawCtx.lineWidth = 4;
    drawCtx.lineJoin = 'round';
    drawCtx.lineCap = 'round';
    drawCtx.shadowColor = 'rgba(0, 255, 0, 0.8)';
    drawCtx.shadowBlur = 10;
    drawCtx.shadowOffsetX = 0;
    drawCtx.shadowOffsetY = 0;
    
    // 绘制已完成的线段
    drawCtx.beginPath();
    polygonPoints.forEach((point, index) => {
        if (index === 0) {
            drawCtx.moveTo(point[0], point[1]);
        } else {
            drawCtx.lineTo(point[0], point[1]);
        }
    });
    drawCtx.stroke();
    
    // 绘制从最后一个点到鼠标的预览线
    if (polygonPoints.length > 0) {
        const lastPoint = polygonPoints[polygonPoints.length - 1];
        let previewX = mouseX;
        let previewY = mouseY;
        let snapToFirst = false;
        
        // 检查是否应该吸附到第一个点
        if (polygonPoints.length >= 2) {
            const firstPoint = polygonPoints[0];
            const distance = Math.sqrt(
                Math.pow(mouseX - firstPoint[0], 2) + Math.pow(mouseY - firstPoint[1], 2)
            );
            
            if (distance < SNAP_DISTANCE) {
                previewX = firstPoint[0];
                previewY = firstPoint[1];
                snapToFirst = true;
            }
        }
        
        // 绘制预览线（虚线）
        drawCtx.setLineDash([5, 5]);
        drawCtx.strokeStyle = snapToFirst ? '#FFD700' : '#00FF00';
        drawCtx.lineWidth = 3;
        drawCtx.shadowColor = snapToFirst ? 'rgba(255, 215, 0, 0.8)' : 'rgba(0, 255, 0, 0.5)';
        drawCtx.beginPath();
        drawCtx.moveTo(lastPoint[0], lastPoint[1]);
        drawCtx.lineTo(previewX, previewY);
        drawCtx.stroke();
        drawCtx.setLineDash([]);
        
        // 如果吸附到第一个点，绘制闭合预览
        if (snapToFirst) {
            drawCtx.beginPath();
            drawCtx.moveTo(lastPoint[0], lastPoint[1]);
            drawCtx.lineTo(firstPoint[0], firstPoint[1]);
            drawCtx.stroke();
        }
    }
    
    // 重置阴影
    drawCtx.shadowColor = 'transparent';
    drawCtx.shadowBlur = 0;
    
    // 绘制顶点（更明显）
    polygonPoints.forEach((point, index) => {
        // 第一个点用不同颜色标记
        drawCtx.fillStyle = index === 0 ? '#FFD700' : '#00FF00';
        drawCtx.strokeStyle = '#FFFFFF';
        drawCtx.lineWidth = 2;
        drawCtx.beginPath();
        drawCtx.arc(point[0], point[1], 8, 0, Math.PI * 2);
        drawCtx.fill();
        drawCtx.stroke();
        
        // 在第一个点上显示"起点"标记
        if (index === 0) {
            drawCtx.fillStyle = '#FFFFFF';
            drawCtx.font = 'bold 12px Arial';
            drawCtx.textAlign = 'center';
            drawCtx.fillText('起点', point[0], point[1] - 15);
        }
    });
    
    // 绘制鼠标位置指示器
    if (polygonPoints.length > 0) {
        const lastPoint = polygonPoints[polygonPoints.length - 1];
        let previewX = mouseX;
        let previewY = mouseY;
        let snapToFirst = false;
        
        // 检查吸附
        if (polygonPoints.length >= 2) {
            const firstPoint = polygonPoints[0];
            const distance = Math.sqrt(
                Math.pow(mouseX - firstPoint[0], 2) + Math.pow(mouseY - firstPoint[1], 2)
            );
            
            if (distance < SNAP_DISTANCE) {
                previewX = firstPoint[0];
                previewY = firstPoint[1];
                snapToFirst = true;
            }
        }
        
        // 鼠标位置圆圈
        drawCtx.fillStyle = snapToFirst ? '#FFD700' : '#00FF00';
        drawCtx.strokeStyle = '#FFFFFF';
        drawCtx.lineWidth = 2;
        drawCtx.beginPath();
        drawCtx.arc(previewX, previewY, 6, 0, Math.PI * 2);
        drawCtx.fill();
        drawCtx.stroke();
        
        // 如果吸附，显示提示
        if (snapToFirst) {
            drawCtx.fillStyle = '#FFD700';
            drawCtx.font = 'bold 14px Arial';
            drawCtx.textAlign = 'center';
            drawCtx.fillText('点击闭合', previewX, previewY - 20);
        }
    }
}

// 处理键盘按键
function handleKeyPress(event) {
    if (event.key === 'Escape' && isDrawing) {
        cancelDrawing();
    }
}

// 保存多边形到服务器
function savePolygonToServer(polygon) {
    fetch('/api/polygon', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ polygon: polygon })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('多边形区域已保存');
        } else {
            alert('保存失败: ' + data.message);
        }
    })
    .catch(error => {
        console.error('保存失败:', error);
        alert('保存失败，请检查网络连接');
    });
}

// 清除多边形
clearPolygonBtn.addEventListener('click', () => {
    if (confirm('确定要清除监控区域吗？')) {
        fetch('/api/polygon', {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('监控区域已清除');
                currentPolygon = [];
                updatePolygonStatus(false);
                drawCtx.clearRect(0, 0, drawCanvas.width, drawCanvas.height);
            }
        })
        .catch(error => {
            console.error('清除失败:', error);
            alert('清除失败，请检查网络连接');
        });
    }
});

// 保存按钮（与绘制完成时自动保存功能相同）
savePolygonBtn.addEventListener('click', () => {
    if (currentPolygon.length >= 3) {
        savePolygonToServer(currentPolygon);
    } else {
        alert('请先绘制监控区域');
    }
});

// 加载多边形
function loadPolygon() {
    fetch('/api/polygon')
        .then(response => response.json())
        .then(data => {
            if (data.defined && data.polygon.length >= 3) {
                currentPolygon = data.polygon;
                updatePolygonStatus(true);
            }
        })
        .catch(error => {
            console.error('加载多边形失败:', error);
        });
}

// 配置面板切换
toggleConfigBtn.addEventListener('click', () => {
    const isHidden = configContent.style.display === 'none';
    configContent.style.display = isHidden ? 'block' : 'none';
    toggleConfigBtn.textContent = isHidden ? '▲' : '▼';
});

// 加载模型列表
function loadModels() {
    fetch('/api/models')
        .then(response => response.json())
        .then(data => {
            modelSelect.innerHTML = '';
            if (data.models && data.models.length > 0) {
                data.models.forEach(model => {
                    const option = document.createElement('option');
                    option.value = model.name;
                    option.textContent = `${model.name} (${model.size_mb} MB)`;
                    if (model.current) {
                        option.selected = true;
                    }
                    modelSelect.appendChild(option);
                });
            } else {
                const option = document.createElement('option');
                option.value = '';
                option.textContent = '未找到模型文件';
                modelSelect.appendChild(option);
            }
        })
        .catch(error => {
            console.error('加载模型列表失败:', error);
            modelSelect.innerHTML = '<option value="">加载失败</option>';
        });
}

// 应用模型
applyModelBtn.addEventListener('click', () => {
    const selectedModel = modelSelect.value;
    if (!selectedModel) {
        alert('请选择一个模型');
        return;
    }
    
    if (confirm(`确定要切换到模型 "${selectedModel}" 吗？切换后检测将使用新模型。`)) {
        applyModelBtn.disabled = true;
        applyModelBtn.textContent = '切换中...';
        
        fetch('/api/model', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ model: selectedModel })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert(data.message);
                // 更新下拉框选中状态
                loadModels();
            } else {
                alert('切换失败: ' + data.message);
            }
        })
        .catch(error => {
            console.error('切换模型失败:', error);
            alert('切换模型失败，请检查网络连接');
        })
        .finally(() => {
            applyModelBtn.disabled = false;
            applyModelBtn.textContent = '应用';
        });
    }
});

// 加载视频URL
function loadVideoUrl() {
    fetch('/api/video')
        .then(response => response.json())
        .then(data => {
            if (data.video_url) {
                videoUrlInput.value = data.video_url;
            }
        })
        .catch(error => {
            console.error('加载视频URL失败:', error);
        });
}

// 应用视频URL
applyVideoBtn.addEventListener('click', () => {
    const newVideoUrl = videoUrlInput.value.trim();
    if (!newVideoUrl) {
        alert('请输入视频URL');
        return;
    }
    
    if (confirm(`确定要更改视频源为 "${newVideoUrl}" 吗？更改后视频流将重新连接。`)) {
        applyVideoBtn.disabled = true;
        applyVideoBtn.textContent = '设置中...';
        
        fetch('/api/video', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ video_url: newVideoUrl })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert(data.message);
            } else {
                alert('设置失败: ' + data.message);
            }
        })
        .catch(error => {
            console.error('设置视频URL失败:', error);
            alert('设置视频URL失败，请检查网络连接');
        })
        .finally(() => {
            applyVideoBtn.disabled = false;
            applyVideoBtn.textContent = '应用';
        });
    }
});

// 加载类别列表
function loadClasses() {
    fetch('/api/classes')
        .then(response => response.json())
        .then(data => {
            classesData = data.classes || [];
            enabledClasses = data.enabled_classes || [];
            renderClassesList();
        })
        .catch(error => {
            console.error('加载类别列表失败:', error);
            classesListContainer.innerHTML = '<p class="loading-message">加载失败</p>';
        });
}

// 渲染类别列表
function renderClassesList() {
    classesListContainer.innerHTML = '';
    
    if (classesData.length === 0) {
        classesListContainer.innerHTML = '<p class="loading-message">暂无类别数据</p>';
        return;
    }
    
    classesData.forEach(cls => {
        const classItem = document.createElement('div');
        classItem.className = `class-item ${cls.enabled ? 'enabled' : ''}`;
        const confidenceThreshold = cls.confidence_threshold !== undefined ? cls.confidence_threshold : 0.25;
        classItem.innerHTML = `
            <input type="checkbox" id="class-${cls.id}" ${cls.enabled ? 'checked' : ''} 
                   onchange="toggleClass(${cls.id})">
            <label for="class-${cls.id}">
                <span class="class-name-cn">${cls.name_cn}</span>
                <span class="class-name-en">(${cls.name_en})</span>
            </label>
            <input type="text" class="class-custom-input" id="custom-name-${cls.id}" 
                   value="${cls.custom ? cls.name_cn : ''}" 
                   placeholder="自定义名称">
            <button class="class-custom-btn" onclick="saveCustomName(${cls.id})">保存名称</button>
            <input type="number" class="class-confidence-input" id="confidence-${cls.id}" 
                   value="${confidenceThreshold.toFixed(2)}" 
                   min="0" max="1" step="0.01" 
                   placeholder="0.25">
            <button class="class-custom-btn" onclick="saveConfidence(${cls.id})">保存阈值</button>
        `;
        classesListContainer.appendChild(classItem);
    });
}

// 切换类别启用状态
window.toggleClass = function(classId) {
    const checkbox = document.getElementById(`class-${classId}`);
    const classItem = checkbox.closest('.class-item');
    
    if (checkbox.checked) {
        if (!enabledClasses.includes(classId)) {
            enabledClasses.push(classId);
        }
        classItem.classList.add('enabled');
    } else {
        enabledClasses = enabledClasses.filter(id => id !== classId);
        classItem.classList.remove('enabled');
    }
};

// 保存自定义名称
window.saveCustomName = function(classId) {
    const input = document.getElementById(`custom-name-${classId}`);
    const customName = input.value.trim();
    
    fetch('/api/classes/custom-name', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            class_id: classId,
            custom_name: customName || null
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // 重新加载类别列表以更新显示
            loadClasses();
        } else {
            alert('保存失败: ' + data.message);
        }
    })
    .catch(error => {
        console.error('保存自定义名称失败:', error);
        alert('保存失败，请检查网络连接');
    });
};

// 保存置信度阈值
window.saveConfidence = function(classId) {
    const input = document.getElementById(`confidence-${classId}`);
    const confidenceValue = parseFloat(input.value);
    
    if (isNaN(confidenceValue) || confidenceValue < 0 || confidenceValue > 1) {
        alert('置信度阈值必须在0-1之间');
        return;
    }
    
    fetch('/api/classes/confidence', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            class_id: classId,
            confidence_threshold: confidenceValue
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert(data.message);
            // 重新加载类别列表以更新显示
            loadClasses();
        } else {
            alert('保存失败: ' + data.message);
        }
    })
    .catch(error => {
        console.error('保存置信度阈值失败:', error);
        alert('保存失败，请检查网络连接');
    });
};

// 全选类别
selectAllClassesBtn.addEventListener('click', () => {
    enabledClasses = classesData.map(cls => cls.id);
    classesData.forEach(cls => {
        const checkbox = document.getElementById(`class-${cls.id}`);
        if (checkbox) {
            checkbox.checked = true;
            checkbox.closest('.class-item').classList.add('enabled');
        }
    });
});

// 全不选类别
deselectAllClassesBtn.addEventListener('click', () => {
    enabledClasses = [];
    classesData.forEach(cls => {
        const checkbox = document.getElementById(`class-${cls.id}`);
        if (checkbox) {
            checkbox.checked = false;
            checkbox.closest('.class-item').classList.remove('enabled');
        }
    });
});

// 应用类别选择
applyClassesBtn.addEventListener('click', () => {
    if (enabledClasses.length === 0) {
        alert('请至少选择一个类别');
        return;
    }
    
    if (confirm(`确定要启用 ${enabledClasses.length} 个类别吗？`)) {
        applyClassesBtn.disabled = true;
        applyClassesBtn.textContent = '应用中...';
        
        fetch('/api/classes/enabled', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ enabled_classes: enabledClasses })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert(data.message);
                // 重新加载类别列表
                loadClasses();
            } else {
                alert('设置失败: ' + data.message);
            }
        })
        .catch(error => {
            console.error('设置类别失败:', error);
            alert('设置类别失败，请检查网络连接');
        })
        .finally(() => {
            applyClassesBtn.disabled = false;
            applyClassesBtn.textContent = '应用';
        });
    }
});

// RGB转十六进制
function rgbToHex(r, g, b) {
    return "#" + [r, g, b].map(x => {
        const hex = x.toString(16);
        return hex.length === 1 ? "0" + hex : hex;
    }).join("");
}

// 十六进制转RGB
function hexToRgb(hex) {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? [
        parseInt(result[1], 16),
        parseInt(result[2], 16),
        parseInt(result[3], 16)
    ] : null;
}

// 加载显示配置
function loadDisplayConfig() {
    fetch('/api/display')
        .then(response => response.json())
        .then(data => {
            if (data.font_size) {
                fontSizeInput.value = data.font_size;
            }
            if (data.box_thickness) {
                boxThicknessInput.value = data.box_thickness;
            }
            if (data.box_color) {
                // OpenCV使用BGR，前端显示用RGB
                const rgb = [data.box_color[2], data.box_color[1], data.box_color[0]];
                boxColorInput.value = rgbToHex(rgb[0], rgb[1], rgb[2]);
                boxColorRgb.value = rgb.join(',');
            }
            if (data.text_color) {
                textColorInput.value = rgbToHex(data.text_color[0], data.text_color[1], data.text_color[2]);
                textColorRgb.value = data.text_color.join(',');
            }
            // 更新语言切换按钮状态
            if (data.use_chinese !== undefined) {
                updateLanguageButton(data.use_chinese);
            }
        })
        .catch(error => {
            console.error('加载显示配置失败:', error);
        });
}

function updateLanguageButton(useChinese) {
    if (toggleLanguageBtn && languageStatus) {
        if (useChinese) {
            toggleLanguageBtn.textContent = '切换为英文';
            toggleLanguageBtn.className = 'btn btn-secondary btn-small';
            languageStatus.textContent = '当前: 中文';
        } else {
            toggleLanguageBtn.textContent = '切换为中文';
            toggleLanguageBtn.className = 'btn btn-primary btn-small';
            languageStatus.textContent = '当前: 英文';
        }
    }
}

// 颜色选择器变化时更新RGB输入框
boxColorInput.addEventListener('input', (e) => {
    const rgb = hexToRgb(e.target.value);
    if (rgb) {
        boxColorRgb.value = rgb.join(',');
    }
});

textColorInput.addEventListener('input', (e) => {
    const rgb = hexToRgb(e.target.value);
    if (rgb) {
        textColorRgb.value = rgb.join(',');
    }
});

// RGB输入框变化时更新颜色选择器
boxColorRgb.addEventListener('input', (e) => {
    const rgb = e.target.value.split(',').map(x => parseInt(x.trim()));
    if (rgb.length === 3 && rgb.every(x => !isNaN(x) && x >= 0 && x <= 255)) {
        boxColorInput.value = rgbToHex(rgb[0], rgb[1], rgb[2]);
    }
});

textColorRgb.addEventListener('input', (e) => {
    const rgb = e.target.value.split(',').map(x => parseInt(x.trim()));
    if (rgb.length === 3 && rgb.every(x => !isNaN(x) && x >= 0 && x <= 255)) {
        textColorInput.value = rgbToHex(rgb[0], rgb[1], rgb[2]);
    }
});

// 应用显示设置
applyDisplayBtn.addEventListener('click', () => {
    const fontSize = parseInt(fontSizeInput.value);
    const boxThickness = parseInt(boxThicknessInput.value);
    
    // 解析边框颜色（BGR格式）
    const boxColorRgbArray = boxColorRgb.value.split(',').map(x => parseInt(x.trim()));
    if (boxColorRgbArray.length !== 3 || !boxColorRgbArray.every(x => !isNaN(x) && x >= 0 && x <= 255)) {
        alert('边框颜色格式错误，请输入RGB格式，如: 0,255,0');
        return;
    }
    // 转换为BGR（OpenCV格式）
    const boxColor = [boxColorRgbArray[2], boxColorRgbArray[1], boxColorRgbArray[0]];
    
    // 解析文字颜色（RGB格式）
    const textColorArray = textColorRgb.value.split(',').map(x => parseInt(x.trim()));
    if (textColorArray.length !== 3 || !textColorArray.every(x => !isNaN(x) && x >= 0 && x <= 255)) {
        alert('文字颜色格式错误，请输入RGB格式，如: 0,0,0');
        return;
    }
    
    applyDisplayBtn.disabled = true;
    applyDisplayBtn.textContent = '设置中...';
    
    fetch('/api/display', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            font_size: fontSize,
            box_thickness: boxThickness,
            box_color: boxColor,
            text_color: textColorArray
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert(data.message);
        } else {
            alert('设置失败: ' + data.message);
        }
    })
    .catch(error => {
        console.error('设置显示配置失败:', error);
        alert('设置失败，请检查网络连接');
    })
    .finally(() => {
        applyDisplayBtn.disabled = false;
        applyDisplayBtn.textContent = '应用显示设置';
    });
});

// 语言切换按钮事件
if (toggleLanguageBtn) {
    toggleLanguageBtn.addEventListener('click', () => {
        // 获取当前配置
        fetch('/api/display')
            .then(response => response.json())
            .then(data => {
                const currentUseChinese = data.use_chinese !== false; // 默认为true
                const newUseChinese = !currentUseChinese;
                
                // 发送更新请求
                fetch('/api/display', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        use_chinese: newUseChinese
                    })
                })
                .then(response => response.json())
                .then(result => {
                    if (result.success) {
                        updateLanguageButton(newUseChinese);
                        console.log('语言切换成功:', newUseChinese ? '中文' : '英文');
                    } else {
                        alert('切换失败: ' + result.message);
                    }
                })
                .catch(error => {
                    console.error('切换语言失败:', error);
                    alert('切换失败: ' + error.message);
                });
            })
            .catch(error => {
                console.error('获取配置失败:', error);
            });
    });
}

// 加载报警配置
function loadAlarmConfig() {
    fetch('/api/alarm')
        .then(response => response.json())
        .then(data => {
            if (debounceTimeInput && data.debounce_time !== undefined) {
                debounceTimeInput.value = data.debounce_time;
            }
            if (detectionModeSelect && data.detection_mode !== undefined) {
                detectionModeSelect.value = data.detection_mode;
            }
            if (oncePerIdCheckbox && data.once_per_id !== undefined) {
                oncePerIdCheckbox.checked = data.once_per_id;
            }
        })
        .catch(error => {
            console.error('加载报警配置失败:', error);
        });
}

// 应用报警设置
if (applyAlarmBtn) {
    applyAlarmBtn.addEventListener('click', () => {
        const debounceTime = parseFloat(debounceTimeInput.value);
        const detectionMode = detectionModeSelect.value;
        const oncePerId = oncePerIdCheckbox ? oncePerIdCheckbox.checked : false;
        
        if (isNaN(debounceTime) || debounceTime < 0) {
            alert('防抖时间必须是大于等于0的数字');
            return;
        }
        
        applyAlarmBtn.disabled = true;
        applyAlarmBtn.textContent = '设置中...';
        
        fetch('/api/alarm', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                debounce_time: debounceTime,
                detection_mode: detectionMode,
                once_per_id: oncePerId
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert(data.message);
            } else {
                alert('设置失败: ' + data.message);
            }
        })
        .catch(error => {
            console.error('设置报警配置失败:', error);
            alert('设置失败，请检查网络连接');
        })
        .finally(() => {
            applyAlarmBtn.disabled = false;
            applyAlarmBtn.textContent = '应用报警设置';
        });
    });
}
