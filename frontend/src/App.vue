<template>
  <div class="app-container">
    <el-container>
      <!-- 头部 -->
      <el-header class="app-header">
        <div class="header-content">
          <h1>YOLO 人员检测与区域报警系统</h1>
          <div class="status-bar">
            <el-tag :type="connectionStatus === 'connected' ? 'success' : 'danger'" effect="dark">
              {{ connectionStatus === 'connected' ? '已连接' : '未连接' }}
            </el-tag>
            <el-tag :type="polygonDefined ? 'success' : 'info'" effect="dark">
              {{ polygonDefined ? `已设置区域 (${polygonPoints}个顶点)` : '未设置区域' }}
            </el-tag>
          </div>
        </div>
      </el-header>

      <!-- 配置面板 -->
      <el-collapse v-model="activeConfigPanels" class="config-panel">
        <el-collapse-item title="系统配置" name="config">
          <ConfigPanel
            @model-changed="handleModelChanged"
            @video-changed="handleVideoChanged"
            @classes-changed="handleClassesChanged"
            @display-changed="handleDisplayChanged"
            @alarm-changed="handleAlarmChanged"
          />
        </el-collapse-item>
      </el-collapse>

      <!-- 主内容区 -->
      <el-main class="main-content">
        <el-row :gutter="20">
          <!-- 视频面板 -->
          <el-col :span="16">
            <VideoPanel
              ref="videoPanelRef"
              :polygon="currentPolygon"
              @polygon-updated="handlePolygonUpdated"
            />
          </el-col>

          <!-- 侧边栏 -->
          <el-col :span="8">
            <el-space direction="vertical" :size="20" style="width: 100%">
              <!-- 报警记录 -->
              <el-card shadow="hover">
                <template #header>
                  <div class="card-header">
                    <span>报警记录</span>
                  </div>
                </template>
                <AlarmList :alarms="alarms" />
              </el-card>

              <!-- 检测信息 -->
              <el-card shadow="hover">
                <template #header>
                  <div class="card-header">
                    <span>检测信息</span>
                  </div>
                </template>
                <DetectionInfo :detections="detections" />
              </el-card>

              <!-- 系统日志 -->
              <el-card shadow="hover">
                <template #header>
                  <div class="card-header">
                    <span>系统日志</span>
                    <div>
                      <el-button size="small" @click="clearLogs">清空日志</el-button>
                      <el-checkbox v-model="autoScrollLogs" size="small" style="margin-left: 10px">
                        自动滚动
                      </el-checkbox>
                    </div>
                  </div>
                </template>
                <LogPanel :logs="logs" :auto-scroll="autoScrollLogs" />
              </el-card>
            </el-space>
          </el-col>
        </el-row>
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { io } from 'socket.io-client'
import ConfigPanel from './components/ConfigPanel.vue'
import VideoPanel from './components/VideoPanel.vue'
import AlarmList from './components/AlarmList.vue'
import DetectionInfo from './components/DetectionInfo.vue'
import LogPanel from './components/LogPanel.vue'

// 状态
const connectionStatus = ref('disconnected')
const polygonDefined = ref(false)
const polygonPoints = ref(0)
const currentPolygon = ref([])
const alarms = ref([])
const detections = ref([])
const logs = ref([])
const autoScrollLogs = ref(true)
const activeConfigPanels = ref(['config'])
const videoPanelRef = ref(null)

// Socket.IO 连接
let socket = null

onMounted(() => {
  // 根据环境配置 Socket.IO 连接地址
  const socketUrl = import.meta.env.DEV 
    ? (import.meta.env.VITE_API_URL || `http://${window.location.hostname}:5000`)  // 开发模式：使用环境变量或当前主机名
    : window.location.origin     // 生产模式：使用当前域名
  
  socket = io(socketUrl, {
    transports: ['websocket', 'polling'],
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionAttempts: 5
  })

  socket.on('connect', () => {
    console.log('已连接到服务器', socket.id)
    connectionStatus.value = 'connected'
  })

  socket.on('disconnect', () => {
    console.log('与服务器断开连接')
    connectionStatus.value = 'disconnected'
  })

  socket.on('frame', (data) => {
    if (!data) {
      console.warn('收到空的 frame 数据')
      return
    }
    
    if (videoPanelRef.value) {
      videoPanelRef.value.updateFrame(data)
    } else {
      console.warn('videoPanelRef 未初始化')
    }
    
    // 更新多边形状态
    if (data.polygon && data.polygon.length >= 3) {
      currentPolygon.value = data.polygon
      polygonDefined.value = true
      polygonPoints.value = data.polygon.length
    } else {
      currentPolygon.value = []
      polygonDefined.value = false
      polygonPoints.value = 0
    }
    
    // 更新检测信息
    detections.value = data.detections || []
  })
  
  socket.on('connect_error', (error) => {
    console.error('Socket.IO 连接错误:', error)
    connectionStatus.value = 'disconnected'
  })

  socket.on('alarm', (data) => {
    console.log('报警:', data)
    alarms.value.unshift(data)
    if (alarms.value.length > 20) {
      alarms.value.pop()
    }
  })

  socket.on('log', (data) => {
    logs.value.push(data)
    if (logs.value.length > 1000) {
      logs.value.shift()
    }
  })
})

onUnmounted(() => {
  if (socket) {
    socket.disconnect()
  }
})

// 事件处理
const handleModelChanged = () => {
  // 模型切换后的处理
}

const handleVideoChanged = () => {
  // 视频源切换后的处理
}

const handleClassesChanged = () => {
  // 类别配置更新后的处理
}

const handleDisplayChanged = () => {
  // 显示配置更新后，通知VideoPanel重新加载配置
  if (videoPanelRef.value && videoPanelRef.value.reloadDisplayConfig) {
    videoPanelRef.value.reloadDisplayConfig()
  }
}

const handleAlarmChanged = () => {
  // 报警配置更新后的处理
}

const handlePolygonUpdated = (polygon) => {
  currentPolygon.value = polygon
  if (polygon && polygon.length >= 3) {
    polygonDefined.value = true
    polygonPoints.value = polygon.length
  } else {
    polygonDefined.value = false
    polygonPoints.value = 0
  }
}

const clearLogs = () => {
  logs.value = []
}
</script>

<style scoped>
.app-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.app-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 20px 30px;
  height: auto !important;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.header-content h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
}

.status-bar {
  display: flex;
  gap: 15px;
}

.config-panel {
  background: #f8f9fa;
  border-bottom: 1px solid #dee2e6;
}

.main-content {
  padding: 20px;
  background: white;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>

