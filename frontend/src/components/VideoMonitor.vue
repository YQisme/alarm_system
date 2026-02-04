<template>
  <div class="video-monitor-page">
    <!-- 左侧录制控制面板 -->
    <div class="recording-panel">
      <el-card shadow="hover" class="recording-card">
        <template #header>
          <div class="card-header">
            <span>录制控制</span>
          </div>
        </template>
        
        <el-form :model="recordingConfig" label-width="120px" size="small">
          <el-form-item label="保存路径:">
            <el-input
              v-model="recordingConfig.save_path"
              placeholder="请输入保存路径"
              @blur="saveRecordingConfig"
            >
              <template #append>
                <el-button @click="selectSavePath">选择</el-button>
              </template>
            </el-input>
          </el-form-item>
          
          <el-form-item label="分割时长:">
            <el-input-number
              v-model="recordingConfig.segment_duration"
              :min="60"
              :max="3600"
              :step="60"
              @change="saveRecordingConfig"
            />
            <span style="margin-left: 10px; color: #909399;">秒</span>
          </el-form-item>
        </el-form>
        
        <div class="recording-controls">
          <el-button
            :type="isRecording ? 'danger' : 'success'"
            :icon="isRecording ? 'VideoPause' : 'VideoPlay'"
            @click="toggleRecording"
            :loading="recordingLoading"
            size="large"
            style="width: 100%;"
          >
            {{ isRecording ? '停止录制' : '开始录制' }}
          </el-button>
        </div>
        
        <div v-if="isRecording" class="recording-status">
          <el-divider />
          <div class="status-info">
            <div class="status-item">
              <span class="status-label">录制状态:</span>
              <el-tag type="danger" effect="dark">
                <span class="recording-dot">●</span> 录制中
              </el-tag>
            </div>
            <div class="status-item">
              <span class="status-label">已录制:</span>
              <span class="status-value">{{ formatTime(elapsedTime) }}</span>
            </div>
            <div class="status-item">
              <span class="status-label">当前分段:</span>
              <span class="status-value">{{ formatTime(currentSegmentTime) }}</span>
            </div>
            <div class="status-item">
              <span class="status-label">保存路径:</span>
              <span class="status-value path">{{ recordingConfig.save_path }}</span>
            </div>
          </div>
        </div>
      </el-card>
      
      <el-button type="primary" @click="goBack" style="width: 100%; margin-top: 10px;">
        返回主页面
      </el-button>
      
      <!-- 录制视频列表 -->
      <el-card shadow="hover" class="recording-card" style="margin-top: 10px;">
        <template #header>
          <div class="card-header">
            <span>录制视频</span>
            <el-button size="small" @click="loadVideoList" :loading="loadingVideos">
              刷新
            </el-button>
          </div>
        </template>
        
        <div class="video-list">
          <el-empty v-if="videos.length === 0 && !loadingVideos" description="暂无录制视频" :image-size="60" />
          <el-scrollbar height="400px" v-else>
            <div v-for="video in videos" :key="video.filename" class="video-item">
              <div class="video-info">
                <div class="video-name" :title="video.filename">
                  <el-icon style="margin-right: 5px;"><VideoPlay /></el-icon>
                  {{ video.filename }}
                </div>
                <div class="video-meta">
                  <span>{{ formatFileSize(video.size) }}</span>
                  <span>{{ video.modified_time }}</span>
                </div>
              </div>
              <div class="video-actions">
                <el-button
                  type="primary"
                  size="small"
                  link
                  @click.stop="downloadVideo(video.filename)"
                >
                  下载后播放
                </el-button>
                <el-button
                  type="primary"
                  size="small"
                  link
                  @click.stop="renameVideo(video)"
                >
                  重命名
                </el-button>
                <el-button
                  type="danger"
                  size="small"
                  link
                  @click.stop="deleteVideo(video.filename)"
                >
                  删除
                </el-button>
              </div>
            </div>
          </el-scrollbar>
        </div>
      </el-card>
    </div>
    
    <!-- 视频显示区域 -->
    <div class="video-container" ref="containerRef">
      <img ref="videoImgRef" class="video-img" :src="videoStreamUrl" @load="onImageLoad" @error="onImageError" />
      <div class="video-overlay">
        <div class="video-stats">
          <span>分辨率: {{ resolution }}</span>
          <span v-if="isRecording" class="recording-indicator">
            <span class="recording-dot">●</span> 录制中
          </span>
        </div>
      </div>
    </div>
    
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElButton, ElMessage, ElMessageBox, ElIcon } from 'element-plus'
import { VideoPlay, VideoPause } from '@element-plus/icons-vue'
import axios from 'axios'

const router = useRouter()

const containerRef = ref(null)
const videoImgRef = ref(null)
const resolution = ref('--')

// 录制相关状态
const isRecording = ref(false)
const recordingLoading = ref(false)
const elapsedTime = ref(0)
const currentSegmentTime = ref(0)
const recordingConfig = ref({
  save_path: '',
  segment_duration: 300  // 默认5分钟
})

// 视频列表相关状态
const videos = ref([])
const loadingVideos = ref(false)

let statusTimer = null

// 构建视频流URL
const videoStreamUrl = computed(() => {
  const baseUrl = import.meta.env.DEV 
    ? (import.meta.env.VITE_API_URL || `http://${window.location.hostname}:5000`)
    : window.location.origin
  return `${baseUrl}/api/video/stream`
})

onMounted(() => {
  // 加载视频信息和录制配置
  loadVideoInfo()
  loadRecordingConfig()
  loadRecordingStatus()
  loadVideoList()
  
  // 如果正在录制，启动状态更新定时器
  if (isRecording.value) {
    startStatusTimer()
  }
})

onUnmounted(() => {
  if (statusTimer) {
    clearInterval(statusTimer)
  }
})

const loadVideoInfo = async () => {
  try {
    const res = await axios.get('/api/status')
    if (res.data && res.data.video_url) {
      resolution.value = '加载中...'
    }
  } catch (error) {
    console.error('加载视频信息失败:', error)
  }
}

const loadRecordingConfig = async () => {
  try {
    const res = await axios.get('/api/recording/config')
    if (res.data) {
      recordingConfig.value = res.data
    }
  } catch (error) {
    console.error('加载录制配置失败:', error)
  }
}

const loadRecordingStatus = async () => {
  try {
    const res = await axios.get('/api/recording/status')
    if (res.data) {
      isRecording.value = res.data.is_recording || false
      if (res.data.is_recording) {
        elapsedTime.value = res.data.elapsed_time || 0
        currentSegmentTime.value = res.data.current_segment_time || 0
        startStatusTimer()
      }
    }
  } catch (error) {
    console.error('加载录制状态失败:', error)
  }
}

const saveRecordingConfig = async () => {
  try {
    const res = await axios.post('/api/recording/config', recordingConfig.value)
    if (res.data.success) {
      ElMessage.success('录制配置已保存')
    } else {
      ElMessage.error(res.data.message || '保存失败')
    }
  } catch (error) {
    console.error('保存录制配置失败:', error)
    ElMessage.error('保存配置失败')
  }
}

const selectSavePath = async () => {
  try {
    const { value: path } = await ElMessageBox.prompt(
      '请输入保存路径（绝对路径）',
      '选择保存路径',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        inputValue: recordingConfig.value.save_path,
        inputValidator: (value) => {
          if (!value || !value.trim()) {
            return '路径不能为空'
          }
          return true
        }
      }
    )
    
    if (path) {
      recordingConfig.value.save_path = path.trim()
      await saveRecordingConfig()
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('选择路径失败:', error)
    }
  }
}

const toggleRecording = async () => {
  if (isRecording.value) {
    // 停止录制
    try {
      recordingLoading.value = true
      const res = await axios.post('/api/recording/stop')
      if (res.data.success) {
        isRecording.value = false
        elapsedTime.value = 0
        currentSegmentTime.value = 0
        stopStatusTimer()
        // 停止录制后刷新视频列表
        loadVideoList()
        ElMessage.success('录制已停止')
      } else {
        ElMessage.error(res.data.message || '停止录制失败')
      }
    } catch (error) {
      console.error('停止录制失败:', error)
      ElMessage.error('停止录制失败')
    } finally {
      recordingLoading.value = false
    }
  } else {
    // 开始录制
    try {
      recordingLoading.value = true
      const res = await axios.post('/api/recording/start')
      if (res.data.success) {
        isRecording.value = true
        elapsedTime.value = 0
        currentSegmentTime.value = 0
        startStatusTimer()
        ElMessage.success('录制已开始')
      } else {
        ElMessage.error(res.data.message || '开始录制失败')
      }
    } catch (error) {
      console.error('开始录制失败:', error)
      ElMessage.error('开始录制失败，请检查ffmpeg是否安装')
    } finally {
      recordingLoading.value = false
    }
  }
}

const startStatusTimer = () => {
  if (statusTimer) {
    clearInterval(statusTimer)
  }
  statusTimer = setInterval(async () => {
    try {
      const res = await axios.get('/api/recording/status')
      if (res.data) {
        if (res.data.is_recording) {
          elapsedTime.value = res.data.elapsed_time || 0
          currentSegmentTime.value = res.data.current_segment_time || 0
        } else {
          // 如果状态显示未录制，但本地状态是录制中，说明录制已停止
          if (isRecording.value) {
            isRecording.value = false
            stopStatusTimer()
            // 录制停止后刷新视频列表
            loadVideoList()
          }
        }
      }
    } catch (error) {
      console.error('获取录制状态失败:', error)
    }
  }, 1000)  // 每秒更新一次
}

const stopStatusTimer = () => {
  if (statusTimer) {
    clearInterval(statusTimer)
    statusTimer = null
  }
}

const formatTime = (seconds) => {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60
  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
  }
  return `${minutes}:${String(secs).padStart(2, '0')}`
}

const loadVideoList = async () => {
  try {
    loadingVideos.value = true
    const res = await axios.get('/api/recording/videos')
    if (res.data.success) {
      videos.value = res.data.videos || []
    } else {
      ElMessage.error(res.data.message || '加载视频列表失败')
    }
  } catch (error) {
    console.error('加载视频列表失败:', error)
    ElMessage.error('加载视频列表失败')
  } finally {
    loadingVideos.value = false
  }
}

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

const downloadVideo = (filename) => {
  const baseUrl = import.meta.env.DEV 
    ? (import.meta.env.VITE_API_URL || `http://${window.location.hostname}:5000`)
    : window.location.origin
  const downloadUrl = `${baseUrl}/api/recording/videos/${encodeURIComponent(filename)}`
  
  // 创建临时链接下载
  const link = document.createElement('a')
  link.href = downloadUrl
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  
  ElMessage.success('开始下载视频')
}

const renameVideo = async (video) => {
  try {
    const { value: newName } = await ElMessageBox.prompt(
      '请输入新的文件名',
      '重命名视频',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        inputValue: video.filename,
        inputValidator: (value) => {
          if (!value || !value.trim()) {
            return '文件名不能为空'
          }
          // 检查文件名是否包含非法字符
          if (/[<>:"/\\|?*]/.test(value)) {
            return '文件名包含非法字符'
          }
          return true
        }
      }
    )
    
    const res = await axios.post(`/api/recording/videos/${encodeURIComponent(video.filename)}/rename`, {
      new_filename: newName.trim()
    })
    
    if (res.data.success) {
      ElMessage.success('视频已重命名')
      await loadVideoList()
    } else {
      ElMessage.error(res.data.message || '重命名失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('重命名失败:', error)
      ElMessage.error('重命名失败')
    }
  }
}

const deleteVideo = async (filename) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除视频"${filename}"吗？`,
      '确认删除',
      {
        type: 'warning',
        confirmButtonText: '删除',
        cancelButtonText: '取消'
      }
    )
    
    const res = await axios.delete(`/api/recording/videos/${encodeURIComponent(filename)}`)
    
    if (res.data.success) {
      ElMessage.success('视频已删除')
      await loadVideoList()
    } else {
      ElMessage.error(res.data.message || '删除失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
      ElMessage.error('删除失败')
    }
  }
}

const onImageLoad = () => {
  if (videoImgRef.value) {
    const img = videoImgRef.value
    resolution.value = `${img.naturalWidth}x${img.naturalHeight}`
  }
}

const onImageError = (error) => {
  console.error('视频流加载错误:', error)
  resolution.value = '连接失败'
}

const goBack = () => {
  router.push('/')
}
</script>

<style scoped>
.video-monitor-page {
  width: 100vw;
  height: 100vh;
  background: #000;
  display: flex;
  overflow: hidden;
}

.recording-panel {
  width: 320px;
  min-width: 320px;
  background: #1a1a1a;
  padding: 20px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.recording-card {
  background: #2a2a2a;
  border: none;
}

.recording-card :deep(.el-card__body) {
  padding: 15px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.recording-controls {
  margin-top: 15px;
}

.recording-status {
  margin-top: 10px;
}

.status-info {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
}

.status-label {
  color: #909399;
}

.status-value {
  color: #fff;
  font-weight: 500;
}

.status-value.path {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
}

.recording-dot {
  display: inline-block;
  color: #f56c6c;
  animation: blink 1s infinite;
  margin-right: 5px;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0.3; }
}

.video-container {
  position: relative;
  flex: 1;
  background: #000;
  display: flex;
  justify-content: center;
  align-items: center;
}

.video-img {
  max-width: 100%;
  max-height: 100%;
  width: auto;
  height: auto;
  object-fit: contain;
  display: block;
}

.video-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  display: flex;
  justify-content: flex-end;
  align-items: flex-start;
  padding: 20px;
}

.video-stats {
  background: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 10px 15px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 14px;
  display: flex;
  gap: 15px;
  align-items: center;
  pointer-events: auto;
}

.recording-indicator {
  display: flex;
  align-items: center;
  color: #f56c6c;
  font-weight: 600;
}

.video-list {
  min-height: 100px;
}

.video-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  margin-bottom: 8px;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  background: #fafafa;
  transition: all 0.3s;
}

.video-item:hover {
  background: #f0f2f5;
  border-color: #c0c4cc;
}

.video-info {
  flex: 1;
  min-width: 0;
}

.video-name {
  font-weight: 500;
  color: #303133;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
}

.video-meta {
  display: flex;
  gap: 10px;
  font-size: 12px;
  color: #909399;
}

.video-actions {
  display: flex;
  gap: 8px;
  margin-left: 10px;
}

</style>

