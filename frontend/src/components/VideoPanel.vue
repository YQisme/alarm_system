<template>
  <el-card shadow="hover">
    <template #header>
      <div class="card-header">
        <span>视频监控</span>
        <div class="video-stats">
          <span>FPS: {{ fps.toFixed(1) }}</span>
          <span>分辨率: {{ resolution }}</span>
        </div>
      </div>
    </template>
    
    <div class="video-container" ref="containerRef">
      <canvas ref="videoCanvasRef" class="video-canvas"></canvas>
      <canvas ref="drawCanvasRef" class="draw-canvas" @click="handleCanvasClick" @mousemove="handleCanvasMouseMove" @dblclick="finishDrawing"></canvas>
      
      <div v-if="isDrawing" class="drawing-hint">
        <p>🖱️ 点击画面绘制多边形区域</p>
        <p>✨ 接近起点时自动吸附，点击闭合</p>
        <p>⌨️ 按 ESC 取消，双击完成</p>
      </div>
    </div>
    
    <div class="video-controls">
      <el-button
        :type="isDrawing ? 'warning' : 'primary'"
        @click="toggleDrawing"
      >
        {{ isDrawing ? '取消绘制 (ESC)' : '绘制监控区域' }}
      </el-button>
      <el-button @click="clearPolygon">清除区域</el-button>
      <el-button type="success" @click="savePolygon">保存区域</el-button>
    </div>
  </el-card>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'

const props = defineProps({
  polygon: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['polygon-updated'])

const containerRef = ref(null)
const videoCanvasRef = ref(null)
const drawCanvasRef = ref(null)

let videoCtx = null
let drawCtx = null

const isDrawing = ref(false)
const polygonPoints = ref([])
const mouseX = ref(0)
const mouseY = ref(0)
const fps = ref(0)
const resolution = ref('--')

// 显示配置
const zoneFillColor = ref([0, 255, 255])  // RGB格式，默认青色
const zoneBorderColor = ref([0, 255, 255])  // RGB格式，默认青色
const zoneFillAlpha = ref(0.3)  // 默认透明度

const SNAP_DISTANCE = 20
let videoWidth = 0
let videoHeight = 0

onMounted(() => {
  if (videoCanvasRef.value && drawCanvasRef.value) {
    videoCtx = videoCanvasRef.value.getContext('2d')
    drawCtx = drawCanvasRef.value.getContext('2d')
    
    if (!videoCtx || !drawCtx) {
      console.error('无法获取 Canvas 上下文')
      return
    }
    
    resizeCanvases()
    window.addEventListener('resize', resizeCanvases)
    window.addEventListener('keydown', handleKeyPress)
    loadPolygon()
    loadDisplayConfig()
    
    console.log('VideoPanel 已初始化')
  } else {
    console.error('Canvas 元素未找到')
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeCanvases)
  window.removeEventListener('keydown', handleKeyPress)
})

watch(() => props.polygon, (newPolygon) => {
  if (!isDrawing.value && newPolygon && newPolygon.length >= 3) {
    drawPolygonOnCanvas(newPolygon)
  }
}, { deep: true })

// 监听颜色配置变化，自动重新绘制
watch([zoneFillColor, zoneBorderColor, zoneFillAlpha], () => {
  if (!isDrawing.value && props.polygon && props.polygon.length >= 3) {
    drawPolygonOnCanvas(props.polygon)
  }
}, { deep: true })

const resizeCanvases = () => {
  if (!containerRef.value) return
  
  const width = containerRef.value.clientWidth
  const height = containerRef.value.clientHeight
  
  videoCanvasRef.value.width = width
  videoCanvasRef.value.height = height
  drawCanvasRef.value.width = width
  drawCanvasRef.value.height = height
  
  if (props.polygon && props.polygon.length >= 3) {
    drawPolygonOnCanvas(props.polygon)
  }
}

const updateFrame = (data) => {
  if (!videoCtx || !videoCanvasRef.value) return
  
  if (!data || !data.frame) {
    console.warn('收到空的视频帧数据')
    return
  }
  
  const img = new Image()
  img.onload = () => {
    try {
      videoCtx.clearRect(0, 0, videoCanvasRef.value.width, videoCanvasRef.value.height)
      videoCtx.drawImage(img, 0, 0, videoCanvasRef.value.width, videoCanvasRef.value.height)
      
      if (videoWidth !== img.width || videoHeight !== img.height) {
        videoWidth = img.width
        videoHeight = img.height
      }
    } catch (error) {
      console.error('绘制视频帧失败:', error)
    }
  }
  img.onerror = (error) => {
    console.error('加载视频帧图片失败:', error, data.frame.substring(0, 50))
  }
  img.src = data.frame
  
  if (data.fps !== undefined) {
    fps.value = data.fps
  }
  if (data.resolution) {
    resolution.value = `${data.resolution.width}x${data.resolution.height}`
  }
}

// RGB数组转十六进制颜色
const rgbToHex = (r, g, b) => {
  return '#' + [r, g, b].map(x => {
    const hex = x.toString(16)
    return hex.length === 1 ? '0' + hex : hex
  }).join('')
}

// RGB数组转rgba字符串
const rgbToRgba = (rgb, alpha) => {
  return `rgba(${rgb[0]}, ${rgb[1]}, ${rgb[2]}, ${alpha})`
}

const drawPolygonOnCanvas = (points) => {
  if (!drawCtx || !points || points.length < 3) return
  
  drawCtx.clearRect(0, 0, drawCanvasRef.value.width, drawCanvasRef.value.height)
  
  const scaleX = drawCanvasRef.value.width / videoWidth
  const scaleY = drawCanvasRef.value.height / videoHeight
  
  // 使用配置的边框颜色
  const borderHex = rgbToHex(zoneBorderColor.value[0], zoneBorderColor.value[1], zoneBorderColor.value[2])
  drawCtx.strokeStyle = borderHex
  drawCtx.lineWidth = 3
  
  // 使用配置的填充颜色和透明度
  drawCtx.fillStyle = rgbToRgba(zoneFillColor.value, zoneFillAlpha.value)
  
  drawCtx.beginPath()
  points.forEach((point, index) => {
    const x = point[0] * scaleX
    const y = point[1] * scaleY
    if (index === 0) {
      drawCtx.moveTo(x, y)
    } else {
      drawCtx.lineTo(x, y)
    }
  })
  drawCtx.closePath()
  drawCtx.fill()
  drawCtx.stroke()
  
  // 绘制顶点，使用边框颜色
  points.forEach(point => {
    const x = point[0] * scaleX
    const y = point[1] * scaleY
    drawCtx.fillStyle = borderHex
    drawCtx.beginPath()
    drawCtx.arc(x, y, 5, 0, Math.PI * 2)
    drawCtx.fill()
  })
}

const toggleDrawing = () => {
  if (isDrawing.value) {
    cancelDrawing()
  } else {
    startDrawing()
  }
}

const startDrawing = () => {
  isDrawing.value = true
  polygonPoints.value = []
}

const cancelDrawing = () => {
  isDrawing.value = false
  polygonPoints.value = []
  drawCtx.clearRect(0, 0, drawCanvasRef.value.width, drawCanvasRef.value.height)
}

const finishDrawing = () => {
  if (polygonPoints.value.length < 3) {
    ElMessage.warning('至少需要3个顶点才能形成多边形')
    return
  }
  
  const scaleX = videoWidth / drawCanvasRef.value.width
  const scaleY = videoHeight / drawCanvasRef.value.height
  
  const videoPolygon = polygonPoints.value.map(point => [
    point[0] * scaleX,
    point[1] * scaleY
  ])
  
  savePolygonToServer(videoPolygon)
  cancelDrawing()
}

const handleCanvasClick = (event) => {
  if (!isDrawing.value) return
  
  const rect = drawCanvasRef.value.getBoundingClientRect()
  let x = event.clientX - rect.left
  let y = event.clientY - rect.top
  
  if (polygonPoints.value.length >= 2) {
    const firstPoint = polygonPoints.value[0]
    const distance = Math.sqrt(
      Math.pow(x - firstPoint[0], 2) + Math.pow(y - firstPoint[1], 2)
    )
    
    if (distance < SNAP_DISTANCE) {
      finishDrawing()
      return
    }
  }
  
  polygonPoints.value.push([x, y])
  drawPolygonPreview()
}

const handleCanvasMouseMove = (event) => {
  if (!isDrawing.value) return
  
  const rect = drawCanvasRef.value.getBoundingClientRect()
  mouseX.value = event.clientX - rect.left
  mouseY.value = event.clientY - rect.top
  
  drawPolygonPreview()
}

const drawPolygonPreview = () => {
  if (!drawCtx) return
  
  drawCtx.clearRect(0, 0, drawCanvasRef.value.width, drawCanvasRef.value.height)
  
  if (polygonPoints.value.length === 0) {
    drawCtx.fillStyle = '#00FF00'
    drawCtx.beginPath()
    drawCtx.arc(mouseX.value, mouseY.value, 6, 0, Math.PI * 2)
    drawCtx.fill()
    drawCtx.strokeStyle = '#FFFFFF'
    drawCtx.lineWidth = 2
    drawCtx.stroke()
    return
  }
  
  drawCtx.strokeStyle = '#00FF00'
  drawCtx.lineWidth = 4
  drawCtx.lineJoin = 'round'
  drawCtx.lineCap = 'round'
  
  drawCtx.beginPath()
  polygonPoints.value.forEach((point, index) => {
    if (index === 0) {
      drawCtx.moveTo(point[0], point[1])
    } else {
      drawCtx.lineTo(point[0], point[1])
    }
  })
  drawCtx.stroke()
  
  if (polygonPoints.value.length > 0) {
    const lastPoint = polygonPoints.value[polygonPoints.value.length - 1]
    let previewX = mouseX.value
    let previewY = mouseY.value
    let snapToFirst = false
    
    if (polygonPoints.value.length >= 2) {
      const firstPoint = polygonPoints.value[0]
      const distance = Math.sqrt(
        Math.pow(mouseX.value - firstPoint[0], 2) + Math.pow(mouseY.value - firstPoint[1], 2)
      )
      
      if (distance < SNAP_DISTANCE) {
        previewX = firstPoint[0]
        previewY = firstPoint[1]
        snapToFirst = true
      }
    }
    
    drawCtx.setLineDash([5, 5])
    drawCtx.strokeStyle = snapToFirst ? '#FFD700' : '#00FF00'
    drawCtx.lineWidth = 3
    drawCtx.beginPath()
    drawCtx.moveTo(lastPoint[0], lastPoint[1])
    drawCtx.lineTo(previewX, previewY)
    drawCtx.stroke()
    drawCtx.setLineDash([])
    
    if (snapToFirst) {
      drawCtx.beginPath()
      drawCtx.moveTo(lastPoint[0], lastPoint[1])
      drawCtx.lineTo(polygonPoints.value[0][0], polygonPoints.value[0][1])
      drawCtx.stroke()
    }
  }
  
  polygonPoints.value.forEach((point, index) => {
    drawCtx.fillStyle = index === 0 ? '#FFD700' : '#00FF00'
    drawCtx.strokeStyle = '#FFFFFF'
    drawCtx.lineWidth = 2
    drawCtx.beginPath()
    drawCtx.arc(point[0], point[1], 8, 0, Math.PI * 2)
    drawCtx.fill()
    drawCtx.stroke()
    
    if (index === 0) {
      drawCtx.fillStyle = '#FFFFFF'
      drawCtx.font = 'bold 12px Arial'
      drawCtx.textAlign = 'center'
      drawCtx.fillText('起点', point[0], point[1] - 15)
    }
  })
  
  if (polygonPoints.value.length > 0) {
    const lastPoint = polygonPoints.value[polygonPoints.value.length - 1]
    let previewX = mouseX.value
    let previewY = mouseY.value
    let snapToFirst = false
    
    if (polygonPoints.value.length >= 2) {
      const firstPoint = polygonPoints.value[0]
      const distance = Math.sqrt(
        Math.pow(mouseX.value - firstPoint[0], 2) + Math.pow(mouseY.value - firstPoint[1], 2)
      )
      
      if (distance < SNAP_DISTANCE) {
        previewX = firstPoint[0]
        previewY = firstPoint[1]
        snapToFirst = true
      }
    }
    
    drawCtx.fillStyle = snapToFirst ? '#FFD700' : '#00FF00'
    drawCtx.strokeStyle = '#FFFFFF'
    drawCtx.lineWidth = 2
    drawCtx.beginPath()
    drawCtx.arc(previewX, previewY, 6, 0, Math.PI * 2)
    drawCtx.fill()
    drawCtx.stroke()
    
    if (snapToFirst) {
      drawCtx.fillStyle = '#FFD700'
      drawCtx.font = 'bold 14px Arial'
      drawCtx.textAlign = 'center'
      drawCtx.fillText('点击闭合', previewX, previewY - 20)
    }
  }
}

const handleKeyPress = (event) => {
  if (event.key === 'Escape' && isDrawing.value) {
    cancelDrawing()
  }
}

const loadPolygon = async () => {
  try {
    const res = await axios.get('/api/polygon')
    if (res.data.defined && res.data.polygon.length >= 3) {
      emit('polygon-updated', res.data.polygon)
    }
  } catch (error) {
    console.error('加载多边形失败:', error)
  }
}

const loadDisplayConfig = async () => {
  try {
    const res = await axios.get('/api/display')
    if (res.data.zone_fill_color) {
      // 后端返回的是RGB格式
      zoneFillColor.value = res.data.zone_fill_color
    }
    if (res.data.zone_border_color) {
      // 后端返回的是RGB格式
      zoneBorderColor.value = res.data.zone_border_color
    }
    if (res.data.zone_fill_alpha !== undefined) {
      zoneFillAlpha.value = res.data.zone_fill_alpha
    }
    // 如果多边形已存在，重新绘制以应用新颜色
    if (props.polygon && props.polygon.length >= 3) {
      drawPolygonOnCanvas(props.polygon)
    }
  } catch (error) {
    console.error('加载显示配置失败:', error)
  }
}

const savePolygonToServer = async (polygon) => {
  try {
    const res = await axios.post('/api/polygon', { polygon })
    if (res.data.success) {
      ElMessage.success('多边形区域已保存')
      emit('polygon-updated', polygon)
    } else {
      ElMessage.error('保存失败: ' + res.data.message)
    }
  } catch (error) {
    console.error('保存失败:', error)
    ElMessage.error('保存失败，请检查网络连接')
  }
}

const clearPolygon = async () => {
  try {
    await ElMessageBox.confirm('确定要清除监控区域吗？', '确认清除', { type: 'warning' })
    
    const res = await axios.delete('/api/polygon')
    if (res.data.success) {
      ElMessage.success('监控区域已清除')
      emit('polygon-updated', [])
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('清除失败:', error)
      ElMessage.error('清除失败')
    }
  }
}

const savePolygon = async () => {
  if (props.polygon && props.polygon.length >= 3) {
    await savePolygonToServer(props.polygon)
  } else {
    ElMessage.warning('请先绘制监控区域')
  }
}

// 暴露方法给父组件（必须在所有函数定义之后）
defineExpose({
  updateFrame,
  reloadDisplayConfig: loadDisplayConfig  // 暴露重新加载显示配置的方法
})
</script>

<style scoped>
.video-container {
  position: relative;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 15px;
  aspect-ratio: 16/9;
}

.video-canvas,
.draw-canvas {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: block;
}

.draw-canvas {
  cursor: crosshair;
  z-index: 10;
}

.video-stats {
  display: flex;
  gap: 15px;
  font-family: 'Courier New', monospace;
  font-size: 13px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.drawing-hint {
  position: absolute;
  top: 20px;
  left: 20px;
  background: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 15px 20px;
  border-radius: 8px;
  z-index: 20;
  backdrop-filter: blur(10px);
}

.drawing-hint p {
  margin: 5px 0;
  font-size: 14px;
}

.video-controls {
  display: flex;
  gap: 10px;
  justify-content: center;
}
</style>

