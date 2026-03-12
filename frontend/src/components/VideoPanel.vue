<template>
  <el-card shadow="hover">
    <template #header>
      <div class="card-header">
        <span>区域报警</span>
        <div class="video-stats">
          <span>FPS: {{ fps.toFixed(1) }}</span>
          <span>分辨率: {{ resolution }}</span>
        </div>
      </div>
    </template>
    
    <div class="video-container" ref="containerRef">
      <img ref="videoImgRef" class="video-img" :src="processedVideoStreamUrl" @load="onVideoImageLoad" @error="onVideoImageError" />
      <canvas ref="drawCanvasRef" class="draw-canvas" @click="handleCanvasClick" @mousemove="handleCanvasMouseMove" @dblclick="finishDrawing"></canvas>
      
    </div>
    
    <div class="video-controls">
      <el-button
        :type="isDrawing ? 'warning' : 'primary'"
        @click="toggleDrawing"
      >
        {{ isDrawing ? '取消绘制 (ESC)' : '新建区域' }}
      </el-button>
    </div>
  </el-card>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'

const props = defineProps({
  zones: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['zones-updated'])

const containerRef = ref(null)
const videoImgRef = ref(null)
const drawCanvasRef = ref(null)

let drawCtx = null

// 构建处理后视频流URL
const processedVideoStreamUrl = computed(() => {
  const baseUrl = import.meta.env.DEV 
    ? (import.meta.env.VITE_API_URL || `http://${window.location.hostname}:5000`)
    : window.location.origin
  return `${baseUrl}/api/video/processed_stream`
})

const isDrawing = ref(false)
const polygonPoints = ref([])
const editingZoneId = ref(null)  // 正在编辑的区域ID
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
  if (drawCanvasRef.value) {
    drawCtx = drawCanvasRef.value.getContext('2d')
    
    if (!drawCtx) {
      console.error('无法获取 Canvas 上下文')
      return
    }
    
    resizeCanvases()
    window.addEventListener('resize', resizeCanvases)
    window.addEventListener('keydown', handleKeyPress)
    loadZones()
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

watch(() => props.zones, (newZones) => {
  if (!isDrawing.value) {
    drawAllZones()
  }
}, { deep: true })

// 监听颜色配置变化，自动重新绘制
watch([zoneFillColor, zoneBorderColor, zoneFillAlpha], () => {
  if (!isDrawing.value) {
    drawAllZones()
  }
}, { deep: true })

const resizeCanvases = () => {
  if (!containerRef.value) return
  
  const width = containerRef.value.clientWidth
  const height = containerRef.value.clientHeight
  
  drawCanvasRef.value.width = width
  drawCanvasRef.value.height = height
  
  drawAllZones()
}

const onVideoImageLoad = () => {
  if (videoImgRef.value) {
    const img = videoImgRef.value
    if (videoWidth !== img.naturalWidth || videoHeight !== img.naturalHeight) {
      videoWidth = img.naturalWidth
      videoHeight = img.naturalHeight
      // 视频尺寸变化时重新绘制区域
      drawAllZones()
    }
    resolution.value = `${img.naturalWidth}x${img.naturalHeight}`
  }
}

const onVideoImageError = (error) => {
  console.error('视频流加载错误:', error)
  resolution.value = '连接失败'
}

// 保留updateFrame方法以兼容WebSocket（如果需要检测数据）
const updateFrame = (data) => {
  // 如果使用MJPEG流，这个方法不再需要，但保留以兼容
  if (data && data.fps !== undefined) {
    fps.value = data.fps
  }
  if (data && data.resolution) {
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

const drawAllZones = () => {
  if (!drawCtx) return
  
  drawCtx.clearRect(0, 0, drawCanvasRef.value.width, drawCanvasRef.value.height)
  
  if (!props.zones || props.zones.length === 0) return
  if (videoWidth === 0 || videoHeight === 0) return
  
  const scaleX = drawCanvasRef.value.width / videoWidth
  const scaleY = drawCanvasRef.value.height / videoHeight
  
  // 绘制所有启用的区域
  props.zones.forEach(zone => {
    if (!zone.enabled || !zone.points || zone.points.length < 3) return
    
    // 获取区域颜色（优先使用区域自己的颜色）
    const zoneColor = zone.color || {}
    const fillColor = zoneColor.fill || zoneFillColor.value
    const borderColor = zoneColor.border || zoneBorderColor.value
    const alpha = zoneFillAlpha.value
    
    const borderHex = rgbToHex(borderColor[0], borderColor[1], borderColor[2])
  drawCtx.strokeStyle = borderHex
  drawCtx.lineWidth = 3
  
    // 使用区域的填充颜色和透明度
    drawCtx.fillStyle = rgbToRgba(fillColor, alpha)
  
  drawCtx.beginPath()
    zone.points.forEach((point, index) => {
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
  
    // 绘制区域名称
    if (zone.name) {
      const centerX = zone.points.reduce((sum, p) => sum + p[0], 0) / zone.points.length * scaleX
      const centerY = zone.points.reduce((sum, p) => sum + p[1], 0) / zone.points.length * scaleY
      
      drawCtx.fillStyle = borderHex
      drawCtx.font = 'bold 14px Arial'
      drawCtx.textAlign = 'center'
      drawCtx.textBaseline = 'middle'
      
      // 绘制文字背景
      const textWidth = drawCtx.measureText(zone.name).width
      const padding = 5
      drawCtx.fillStyle = 'rgba(0, 0, 0, 0.7)'
      drawCtx.fillRect(centerX - textWidth / 2 - padding, centerY - 10 - padding, textWidth + padding * 2, 20 + padding * 2)
      
      // 绘制文字
    drawCtx.fillStyle = borderHex
      drawCtx.fillText(zone.name, centerX, centerY)
    }
  })
}

const toggleDrawing = () => {
  if (isDrawing.value) {
    cancelDrawing()
  } else {
    ElMessageBox.alert(
      '🖱️ 点击画面绘制多边形区域<br><br>✨ 接近起点时自动吸附，点击闭合<br><br>⌨️ 按 ESC 取消，双击完成',
      '绘制多边形区域',
      {
        confirmButtonText: '确定',
        dangerouslyUseHTMLString: true,
        callback: () => {
          startDrawing()
        }
      }
    )
  }
}

const startDrawing = (zone = null) => {
  isDrawing.value = true
  polygonPoints.value = []
  editingZoneId.value = zone ? zone.id : null
}

const cancelDrawing = () => {
  isDrawing.value = false
  polygonPoints.value = []
  editingZoneId.value = null
  drawAllZones()
}

const finishDrawing = async () => {
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
  
  if (editingZoneId.value) {
    // 更新现有区域
    await updateZoneToServer(editingZoneId.value, videoPolygon)
  } else {
    // 创建新区域
    await createZoneToServer(videoPolygon)
  }
  
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
  
  // 先绘制已存在的区域（半透明）
  if (props.zones && props.zones.length > 0 && videoWidth > 0 && videoHeight > 0) {
    const scaleX = drawCanvasRef.value.width / videoWidth
    const scaleY = drawCanvasRef.value.height / videoHeight
    
    props.zones.forEach(zone => {
      if (!zone.enabled || !zone.points || zone.points.length < 3) return
      
      const zoneColor = zone.color || {}
      const fillColor = zoneColor.fill || zoneFillColor.value
      const borderColor = zoneColor.border || zoneBorderColor.value
      
      const borderHex = rgbToHex(borderColor[0], borderColor[1], borderColor[2])
      drawCtx.strokeStyle = borderHex
      drawCtx.lineWidth = 2
      drawCtx.globalAlpha = 0.3
      
      drawCtx.fillStyle = rgbToRgba(fillColor, 0.2)
      
      drawCtx.beginPath()
      zone.points.forEach((point, index) => {
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
      drawCtx.globalAlpha = 1.0
    })
  }
  
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

const loadZones = async () => {
  try {
    const res = await axios.get('/api/zones')
    if (res.data.zones) {
      emit('zones-updated', res.data.zones)
    }
  } catch (error) {
    console.error('加载区域失败:', error)
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
    // 如果区域已存在，重新绘制以应用新颜色
    drawAllZones()
  } catch (error) {
    console.error('加载显示配置失败:', error)
  }
}

const createZoneToServer = async (points) => {
  try {
    const res = await axios.post('/api/zones', {
      points: points,
      name: `区域${props.zones.length + 1}`,
      enabled: true,
      color: {
        fill: zoneFillColor.value,
        border: zoneBorderColor.value
      }
    })
    if (res.data.success) {
      ElMessage.success('区域已创建')
      await loadZones()
    } else {
      ElMessage.error('创建失败: ' + res.data.message)
    }
  } catch (error) {
    console.error('创建失败:', error)
    ElMessage.error('创建失败，请检查网络连接')
  }
}

const updateZoneToServer = async (zoneId, points) => {
  try {
    const res = await axios.put(`/api/zones/${zoneId}`, {
      points: points
    })
    if (res.data.success) {
      ElMessage.success('区域已更新')
      await loadZones()
    } else {
      ElMessage.error('更新失败: ' + res.data.message)
    }
  } catch (error) {
    console.error('更新失败:', error)
    ElMessage.error('更新失败，请检查网络连接')
  }
}

// 暴露方法给父组件（必须在所有函数定义之后）
defineExpose({
  updateFrame,
  reloadDisplayConfig: loadDisplayConfig,  // 暴露重新加载显示配置的方法
  startDrawing  // 暴露开始绘制方法
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

.video-img,
.draw-canvas {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: block;
}

.video-img {
  object-fit: contain;
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

.video-controls {
  display: flex;
  gap: 10px;
  justify-content: center;
}
</style>

