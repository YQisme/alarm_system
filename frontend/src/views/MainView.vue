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
            <el-tag :type="zonesCount > 0 ? 'success' : 'info'" effect="dark">
              {{ zonesCount > 0 ? `已设置 ${zonesCount} 个区域` : '未设置区域' }}
            </el-tag>
            <el-button type="primary" size="small" @click="goToMonitor">视频监控</el-button>
            <el-button type="danger" size="small" @click="handleLogout" v-if="loginEnabled">登出</el-button>
          </div>
        </div>
      </el-header>

      <!-- 顶部导航栏：区域管理、日志、设置 -->
      <div class="top-nav-bar">
        <el-tabs v-model="activeTopTab" type="card" class="top-tabs">
          <el-tab-pane label="区域管理" name="zones">
            <div class="tab-content">
              <ZoneManager
                :zones="zones"
                @zone-selected="handleZoneSelected"
                @start-drawing="handleStartDrawing"
                @zone-updated="handleZoneUpdated"
              />
            </div>
          </el-tab-pane>
          <el-tab-pane label="日志" name="logs">
            <div class="tab-content">
              <el-tabs v-model="activeLogTab" type="border-card" class="log-tabs">
                <el-tab-pane label="操作日志" name="operation">
                  <div class="log-container">
                    <div class="log-header">
                      <el-button size="small" @click="clearOperationLogs">清空日志</el-button>
                      <el-checkbox v-model="autoScrollOperationLogs" size="small" style="margin-left: 10px">
                        自动滚动
                      </el-checkbox>
                    </div>
                    <LogPanel :logs="operationLogs" :auto-scroll="autoScrollOperationLogs" />
                  </div>
                </el-tab-pane>
                <el-tab-pane label="系统日志" name="system">
                  <div class="log-container">
                    <div class="log-header">
                      <el-button size="small" @click="clearLogs">清空日志</el-button>
                      <el-checkbox v-model="autoScrollLogs" size="small" style="margin-left: 10px">
                        自动滚动
                      </el-checkbox>
                    </div>
                    <LogPanel :logs="logs" :auto-scroll="autoScrollLogs" />
                  </div>
                </el-tab-pane>
              </el-tabs>
            </div>
          </el-tab-pane>
          <el-tab-pane label="设置" name="config">
            <div class="tab-content">
              <ConfigPanel
                @model-changed="handleModelChanged"
                @video-changed="handleVideoChanged"
                @classes-changed="handleClassesChanged"
                @display-changed="handleDisplayChanged"
                @alarm-changed="handleAlarmChanged"
              />
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>

      <!-- 主内容区 -->
      <el-main class="main-content">
        <el-row :gutter="20">
          <!-- 视频面板 -->
          <el-col :span="16">
            <VideoPanel
              ref="videoPanelRef"
              :zones="zones"
              @zones-updated="handleZonesUpdated"
            />
          </el-col>

          <!-- 侧边栏 -->
          <el-col :span="8">
            <el-card shadow="hover" class="info-card">
              <template #header>
                <div class="card-header">
                  <span class="card-title">监控信息</span>
                </div>
              </template>
              <el-tabs v-model="activeInfoTab" type="border-card" class="info-tabs">
                <el-tab-pane label="报警记录" name="alarm">
                  <AlarmList :alarms="alarms" />
                </el-tab-pane>
                <el-tab-pane label="检测信息" name="detection">
                  <DetectionInfo :detections="detections" />
                </el-tab-pane>
              </el-tabs>
            </el-card>
          </el-col>
        </el-row>
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { io } from 'socket.io-client'
import axios from 'axios'
import ConfigPanel from '../components/ConfigPanel.vue'
import VideoPanel from '../components/VideoPanel.vue'
import AlarmList from '../components/AlarmList.vue'
import DetectionInfo from '../components/DetectionInfo.vue'
import LogPanel from '../components/LogPanel.vue'
import ZoneManager from '../components/ZoneManager.vue'

const router = useRouter()

// 状态
const connectionStatus = ref('disconnected')
const zones = ref([])
const zonesCount = ref(0)
const alarms = ref([])
const detections = ref([])
const logs = ref([])  // 系统日志
const operationLogs = ref([])  // 操作日志
const autoScrollLogs = ref(true)
const autoScrollOperationLogs = ref(true)
const activeTopTab = ref('zones')  // 顶部标签：zones/logs/config
const activeLogTab = ref('operation')  // 日志子标签：operation/system
const activeInfoTab = ref('alarm')  // 信息标签：alarm/detection
const videoPanelRef = ref(null)
const loginEnabled = ref(true)  // 是否启用登录

// Socket.IO 连接
let socket = null

onMounted(() => {
  // 检查登录状态
  checkLoginStatus()

  // 根据环境配置 Socket.IO 连接地址
  const socketUrl = import.meta.env.DEV 
    ? (import.meta.env.VITE_API_URL || `http://${window.location.hostname}:5000`)
    : window.location.origin
  
  socket = io(socketUrl, {
    transports: ['websocket', 'polling'],
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionAttempts: 5
  })

  socket.on('connect', () => {
    console.log('已连接到服务器', socket.id)
    connectionStatus.value = 'connected'
    // 连接后加载区域列表
    handleZonesUpdated()
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
    
    // 更新区域状态
    if (data.zones) {
      zones.value = data.zones
      zonesCount.value = data.zones.length
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
    // 系统日志
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

const handleZonesUpdated = async () => {
  // 重新加载区域列表
  try {
    const res = await axios.get('/api/zones')
    if (res.data.zones) {
      zones.value = res.data.zones
      zonesCount.value = res.data.zones.length
    }
  } catch (error) {
    console.error('加载区域失败:', error)
  }
}

const handleZoneSelected = (zoneId) => {
  // 区域选择处理（可选）
}

const handleStartDrawing = (zone = null) => {
  // 开始绘制区域
  if (videoPanelRef.value && videoPanelRef.value.startDrawing) {
    videoPanelRef.value.startDrawing(zone)
    if (zone) {
      addOperationLog(`开始编辑区域: ${zone.name}`, 'INFO')
    } else {
      addOperationLog('开始绘制新区域', 'INFO')
    }
  }
}

const handleZoneUpdated = () => {
  handleZonesUpdated()
  addOperationLog('区域配置已更新', 'INFO')
}

const clearLogs = () => {
  logs.value = []
}

const clearOperationLogs = () => {
  operationLogs.value = []
}

// 记录操作日志
const addOperationLog = (message, level = 'INFO') => {
  const timestamp = new Date().toLocaleString('zh-CN')
  operationLogs.value.push({
    timestamp,
    level,
    message,
    logger: 'operation'
  })
  if (operationLogs.value.length > 1000) {
    operationLogs.value.shift()
  }
}

// 监听各种操作，记录到操作日志
const handleModelChanged = () => {
  addOperationLog('检测模型已切换', 'INFO')
}

const handleVideoChanged = () => {
  addOperationLog('视频源已切换', 'INFO')
}

const handleClassesChanged = () => {
  addOperationLog('检测类别配置已更新', 'INFO')
}

const handleDisplayChanged = () => {
  // 显示配置更新后，通知VideoPanel重新加载配置
  if (videoPanelRef.value && videoPanelRef.value.reloadDisplayConfig) {
    videoPanelRef.value.reloadDisplayConfig()
  }
  addOperationLog('显示配置已更新', 'INFO')
}

const handleAlarmChanged = () => {
  addOperationLog('报警配置已更新', 'INFO')
}

const goToMonitor = () => {
  router.push('/monitor')
}
// 检查登录状态
const checkLoginStatus = async () => {
  try {
    const res = await axios.get('/api/login/status')
    loginEnabled.value = res.data.login_enabled
  } catch (error) {
    console.error('检查登录状态失败:', error)
  }
}

// 登出
const handleLogout = async () => {
  try {
    const res = await axios.post('/api/logout')
    if (res.data.success) {
      // 跳转到登录页
      router.push('/login')
    }
  } catch (error) {
    console.error('登出失败:', error)
    // 即使失败也跳转到登录页
    router.push('/login')
  }
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
  align-items: center;
}

/* 顶部导航栏 */
.top-nav-bar {
  background: white;
  border-bottom: 2px solid #e4e7ed;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.top-tabs {
  margin: 0;
}

.top-tabs :deep(.el-tabs__header) {
  margin: 0;
  background: #f5f7fa;
  padding: 0 20px;
}

.top-tabs :deep(.el-tabs__item) {
  height: 50px;
  line-height: 50px;
  font-size: 15px;
  font-weight: 500;
  padding: 0 30px;
  border-bottom: 3px solid transparent;
  transition: all 0.3s;
}

.top-tabs :deep(.el-tabs__item.is-active) {
  color: #409eff;
  border-bottom-color: #409eff;
  background: white;
}

.top-tabs :deep(.el-tabs__item:hover) {
  color: #409eff;
}

.tab-content {
  padding: 20px;
  background: white;
  min-height: 400px;
  max-height: 600px;
  overflow-y: auto;
}

.log-tabs {
  border: none;
}

.log-tabs :deep(.el-tabs__header) {
  margin-bottom: 15px;
}

.main-content {
  padding: 20px;
  background: #f5f7fa;
}

.info-card {
  height: 100%;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.info-card :deep(.el-card__body) {
  padding: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 8px 8px 0 0;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
}

.info-tabs {
  border: none;
}

.info-tabs :deep(.el-tabs__header) {
  margin: 0;
  background: #f5f7fa;
  padding: 0 15px;
}

.info-tabs :deep(.el-tabs__content) {
  padding: 15px;
  min-height: 400px;
  max-height: 600px;
  overflow-y: auto;
}

.log-container {
  padding: 10px;
}

.log-header {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  margin-bottom: 10px;
  padding-bottom: 10px;
  border-bottom: 1px solid #e4e7ed;
}
</style>

