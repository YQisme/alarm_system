<template>
  <div class="config-panel">
    <el-tabs v-model="activeTab" type="border-card">
      <!-- 模型配置 -->
      <el-tab-pane label="模型配置" name="model">
        <el-form :model="modelForm" label-width="120px">
          <el-form-item label="检测模型">
            <el-select v-model="modelForm.model" placeholder="加载中..." style="width: 100%">
              <el-option
                v-for="model in models"
                :key="model.name"
                :label="`${model.name} (${model.size_mb} MB)`"
                :value="model.name"
              />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="applyModel" :loading="modelLoading">应用</el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <!-- 视频配置 -->
      <el-tab-pane label="视频配置" name="video">
        <el-form :model="videoForm" label-width="120px">
          <el-form-item label="视频URL">
            <el-input v-model="videoForm.video_url" placeholder="rtsp://..." />
          </el-form-item>
          <el-form-item label="摄像头IP">
            <el-input 
              v-model="videoForm.camera_ip" 
              placeholder="自动从RTSP URL提取或手动输入"
              style="width: 300px"
            />
            <span style="margin-left: 10px; color: #666; font-size: 12px">
              留空则自动从RTSP URL中提取
            </span>
          </el-form-item>
          <el-form-item label="摄像头状态">
            <el-tag 
              :type="getCameraStatusType(videoForm.camera_status)"
              size="large"
            >
              <el-icon style="margin-right: 5px">
                <CircleCheck v-if="videoForm.camera_status === 'online'" />
                <CircleClose v-else-if="videoForm.camera_status === 'offline'" />
                <QuestionFilled v-else />
              </el-icon>
              {{ getCameraStatusText(videoForm.camera_status) }}
            </el-tag>
            <el-button 
              size="small" 
              style="margin-left: 10px"
              @click="checkCameraStatus"
              :loading="statusChecking"
            >
              检测状态
            </el-button>
          </el-form-item>
          <el-form-item label="检测间隔（秒）">
            <el-input-number
              v-model="videoForm.camera_check_interval"
              :min="1"
              :max="300"
              :step="1"
              style="width: 150px"
            />
            <span style="margin-left: 10px; color: #666; font-size: 12px">
              摄像头状态检测的时间间隔，最小1秒
            </span>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="applyVideo" :loading="videoLoading">应用</el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <!-- 类别配置 -->
      <el-tab-pane label="检测类别" name="classes">
        <div class="classes-controls">
          <el-button size="small" @click="selectAllClasses">全选</el-button>
          <el-button size="small" @click="deselectAllClasses">全不选</el-button>
          <el-button type="primary" size="small" @click="applyClasses" :loading="classesLoading">应用</el-button>
        </div>
        <el-scrollbar height="300px" style="margin-top: 15px">
          <div class="classes-list">
            <div
              v-for="cls in classesData"
              :key="cls.id"
              class="class-item"
              :class="{ enabled: enabledClasses.includes(cls.id) }"
            >
              <el-checkbox
                v-model="enabledClasses"
                :label="cls.id"
                @change="handleClassToggle(cls.id)"
              >
                <span class="class-name-cn">{{ cls.name_cn }}</span>
                <span class="class-name-en">({{ cls.name_en }})</span>
              </el-checkbox>
              <el-input
                v-model="cls.custom_name"
                size="small"
                placeholder="自定义名称"
                style="width: 120px; margin-left: 10px"
                @blur="saveCustomName(cls.id)"
              />
              <el-input-number
                v-model="cls.confidence_threshold"
                size="small"
                :min="0"
                :max="1"
                :step="0.01"
                :precision="2"
                style="width: 100px; margin-left: 10px"
                @blur="saveConfidence(cls.id)"
              />
            </div>
          </div>
        </el-scrollbar>
      </el-tab-pane>

      <!-- 显示配置 -->
      <el-tab-pane label="显示设置" name="display">
        <el-form :model="displayForm" label-width="120px">
          <el-form-item label="字体大小">
            <el-input-number v-model="displayForm.font_size" :min="8" :max="72" />
          </el-form-item>
          <el-form-item label="边框粗细">
            <el-input-number v-model="displayForm.box_thickness" :min="1" :max="10" />
          </el-form-item>
          <el-form-item label="边框颜色">
            <el-color-picker v-model="displayForm.box_color_hex" />
            <el-input
              v-model="displayForm.box_color_rgb"
              placeholder="RGB: 0,255,0"
              style="width: 150px; margin-left: 10px"
            />
          </el-form-item>
          <el-form-item label="文字颜色">
            <el-color-picker v-model="displayForm.text_color_hex" />
            <el-input
              v-model="displayForm.text_color_rgb"
              placeholder="RGB: 0,0,0"
              style="width: 150px; margin-left: 10px"
            />
          </el-form-item>
          <el-form-item label="显示语言">
            <el-button
              :type="displayForm.use_chinese ? 'default' : 'primary'"
              @click="toggleLanguage"
            >
              {{ displayForm.use_chinese ? '切换为英文' : '切换为中文' }}
            </el-button>
            <span style="margin-left: 10px; color: #666">
              当前: {{ displayForm.use_chinese ? '中文' : '英文' }}
            </span>
          </el-form-item>
          <el-divider />
          <el-form-item label="报警区域填充颜色">
            <el-color-picker v-model="displayForm.zone_fill_color_hex" />
            <el-input
              v-model="displayForm.zone_fill_color_rgb"
              placeholder="RGB: 0,255,255"
              style="width: 150px; margin-left: 10px"
            />
          </el-form-item>
          <el-form-item label="报警区域边框颜色">
            <el-color-picker v-model="displayForm.zone_border_color_hex" />
            <el-input
              v-model="displayForm.zone_border_color_rgb"
              placeholder="RGB: 0,255,255"
              style="width: 150px; margin-left: 10px"
            />
          </el-form-item>
          <el-form-item label="填充透明度">
            <el-slider
              v-model="displayForm.zone_fill_alpha"
              :min="0"
              :max="1"
              :step="0.1"
              :show-input="true"
              :format-tooltip="(val) => `${(val * 100).toFixed(0)}%`"
              style="width: 300px"
            />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="applyDisplay" :loading="displayLoading">应用显示设置</el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <!-- 遮挡检测配置 -->
      <el-tab-pane label="遮挡检测" name="occlusion">
        <el-form :model="occlusionForm" label-width="150px">
          <el-form-item label="启用遮挡检测">
            <el-switch v-model="occlusionForm.enabled" />
            <span style="margin-left: 10px; color: #666; font-size: 12px">
              启用后，系统会自动检测视频画面是否被遮挡
            </span>
          </el-form-item>
          <el-form-item label="检测间隔（秒）">
            <el-input-number
              v-model="occlusionForm.check_interval"
              :min="0.5"
              :max="300"
              :step="0.5"
              :precision="1"
            />
            <span style="margin-left: 10px; color: #666; font-size: 12px">
              两次检测之间的时间间隔
            </span>
          </el-form-item>
          <el-form-item label="遮挡率阈值">
            <el-input-number
              v-model="occlusionForm.occlusion_threshold"
              :min="0"
              :max="1"
              :step="0.01"
              :precision="2"
            />
            <span style="margin-left: 10px; color: #666; font-size: 12px">
              遮挡率超过该值将触发报警（0-1之间，例如0.3表示30%）
            </span>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="applyOcclusion" :loading="occlusionLoading">应用遮挡检测设置</el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <!-- 报警配置 -->
      <el-tab-pane label="报警设置" name="alarm">
        <el-form :model="alarmForm" label-width="150px">
          <el-form-item label="防抖时间（秒）">
            <el-input-number
              v-model="alarmForm.debounce_time"
              :min="0"
              :max="300"
              :step="0.1"
              :precision="1"
            />
            <span style="margin-left: 10px; color: #666; font-size: 12px">
              同一目标在此时间内只报警一次
            </span>
          </el-form-item>
          <el-form-item label="检测模式">
            <el-select v-model="alarmForm.detection_mode" style="width: 100%">
              <el-option
                label="中心点模式（检测框中心点进入区域）"
                value="center"
              />
              <el-option
                label="边框模式（检测框任意点进入区域）"
                value="edge"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="相同ID只报警一次">
            <el-switch v-model="alarmForm.once_per_id" />
            <span style="margin-left: 10px; color: #666; font-size: 12px">
              启用后，同一ID在整个生命周期内只报警一次
            </span>
          </el-form-item>
          
          <el-divider>事件保存设置</el-divider>
          
          <el-form-item label="保存事件视频">
            <el-switch v-model="alarmForm.save_event_video" />
            <span style="margin-left: 10px; color: #666; font-size: 12px">
              触发报警时自动保存视频片段
            </span>
          </el-form-item>
          <el-form-item label="保存事件图片">
            <el-switch v-model="alarmForm.save_event_image" />
            <span style="margin-left: 10px; color: #666; font-size: 12px">
              触发报警时自动保存当前画面
            </span>
          </el-form-item>
          <el-form-item label="事件视频时长（秒）" v-if="alarmForm.save_event_video">
            <el-input-number
              v-model="alarmForm.event_video_duration"
              :min="5"
              :max="60"
              :step="1"
            />
            <span style="margin-left: 10px; color: #666; font-size: 12px">
              报警时录制的视频时长
            </span>
          </el-form-item>
          <el-form-item label="事件保存路径">
            <el-input
              v-model="alarmForm.event_save_path"
              placeholder="请输入保存路径"
            >
              <template #append>
                <el-button @click="selectEventSavePath">选择</el-button>
              </template>
            </el-input>
            <div style="margin-top: 5px; color: #666; font-size: 12px">
              视频保存在 videos/ 目录，图片保存在 images/ 目录
            </div>
          </el-form-item>
          
          <el-form-item>
            <el-button type="primary" @click="applyAlarm" :loading="alarmLoading">应用报警设置</el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CircleCheck, CircleClose, QuestionFilled } from '@element-plus/icons-vue'
import axios from 'axios'

const emit = defineEmits(['model-changed', 'video-changed', 'classes-changed', 'display-changed', 'alarm-changed'])

const activeTab = ref('model')
const models = ref([])
const classesData = ref([])
const enabledClasses = ref([])

const modelForm = ref({ model: '' })
const videoForm = ref({ 
  video_url: '',
  camera_ip: '',
  camera_status: 'unknown',
  camera_check_interval: 5
})
const statusChecking = ref(false)
let statusCheckInterval = null
const displayForm = ref({
  font_size: 16,
  box_thickness: 2,
  box_color_hex: '#00ff00',
  box_color_rgb: '0,255,0',
  text_color_hex: '#000000',
  text_color_rgb: '0,0,0',
  use_chinese: true,
  zone_fill_color_hex: '#00ffff',
  zone_fill_color_rgb: '0,255,255',
  zone_border_color_hex: '#00ffff',
  zone_border_color_rgb: '0,255,255',
  zone_fill_alpha: 0.3
})
const alarmForm = ref({
  debounce_time: 5.0,
  detection_mode: 'center',
  once_per_id: false,
  save_event_video: true,
  save_event_image: true,
  event_video_duration: 10,
  event_save_path: ''
})
const occlusionForm = ref({
  enabled: false,
  check_interval: 5.0,
  occlusion_threshold: 0.3
})

const modelLoading = ref(false)
const videoLoading = ref(false)
const classesLoading = ref(false)
const displayLoading = ref(false)
const alarmLoading = ref(false)
const occlusionLoading = ref(false)

// RGB 和 Hex 转换
const rgbToHex = (r, g, b) => {
  return '#' + [r, g, b].map(x => {
    const hex = x.toString(16)
    return hex.length === 1 ? '0' + hex : hex
  }).join('')
}

const hexToRgb = (hex) => {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex)
  return result ? [
    parseInt(result[1], 16),
    parseInt(result[2], 16),
    parseInt(result[3], 16)
  ] : null
}

// 颜色选择器和RGB输入框的双向同步
watch(() => displayForm.value.box_color_hex, (newHex) => {
  if (newHex) {
    const rgb = hexToRgb(newHex)
    if (rgb) {
      displayForm.value.box_color_rgb = `${rgb[0]},${rgb[1]},${rgb[2]}`
    }
  }
})

watch(() => displayForm.value.text_color_hex, (newHex) => {
  if (newHex) {
    const rgb = hexToRgb(newHex)
    if (rgb) {
      displayForm.value.text_color_rgb = `${rgb[0]},${rgb[1]},${rgb[2]}`
    }
  }
})

watch(() => displayForm.value.box_color_rgb, (newRgb) => {
  if (newRgb) {
    const rgbArray = newRgb.split(',').map(x => parseInt(x.trim()))
    if (rgbArray.length === 3 && rgbArray.every(x => !isNaN(x) && x >= 0 && x <= 255)) {
      const hex = rgbToHex(rgbArray[0], rgbArray[1], rgbArray[2])
      if (displayForm.value.box_color_hex !== hex) {
        displayForm.value.box_color_hex = hex
      }
    }
  }
})

watch(() => displayForm.value.text_color_rgb, (newRgb) => {
  if (newRgb) {
    const rgbArray = newRgb.split(',').map(x => parseInt(x.trim()))
    if (rgbArray.length === 3 && rgbArray.every(x => !isNaN(x) && x >= 0 && x <= 255)) {
      const hex = rgbToHex(rgbArray[0], rgbArray[1], rgbArray[2])
      if (displayForm.value.text_color_hex !== hex) {
        displayForm.value.text_color_hex = hex
      }
    }
  }
})

watch(() => displayForm.value.zone_fill_color_hex, (newHex) => {
  if (newHex) {
    const rgb = hexToRgb(newHex)
    if (rgb) {
      displayForm.value.zone_fill_color_rgb = `${rgb[0]},${rgb[1]},${rgb[2]}`
    }
  }
})

watch(() => displayForm.value.zone_border_color_hex, (newHex) => {
  if (newHex) {
    const rgb = hexToRgb(newHex)
    if (rgb) {
      displayForm.value.zone_border_color_rgb = `${rgb[0]},${rgb[1]},${rgb[2]}`
    }
  }
})

watch(() => displayForm.value.zone_fill_color_rgb, (newRgb) => {
  if (newRgb) {
    const rgbArray = newRgb.split(',').map(x => parseInt(x.trim()))
    if (rgbArray.length === 3 && rgbArray.every(x => !isNaN(x) && x >= 0 && x <= 255)) {
      const hex = rgbToHex(rgbArray[0], rgbArray[1], rgbArray[2])
      if (displayForm.value.zone_fill_color_hex !== hex) {
        displayForm.value.zone_fill_color_hex = hex
      }
    }
  }
})

watch(() => displayForm.value.zone_border_color_rgb, (newRgb) => {
  if (newRgb) {
    const rgbArray = newRgb.split(',').map(x => parseInt(x.trim()))
    if (rgbArray.length === 3 && rgbArray.every(x => !isNaN(x) && x >= 0 && x <= 255)) {
      const hex = rgbToHex(rgbArray[0], rgbArray[1], rgbArray[2])
      if (displayForm.value.zone_border_color_hex !== hex) {
        displayForm.value.zone_border_color_hex = hex
      }
    }
  }
})

// 加载数据
onMounted(() => {
  loadModels()
  loadVideoUrl()
  loadClasses()
  loadDisplayConfig()
  loadAlarmConfig()
  loadOcclusionConfig()
  
  // 每5秒自动更新摄像头状态
  statusCheckInterval = setInterval(() => {
    checkCameraStatus()
  }, 5000)
})

onUnmounted(() => {
  if (statusCheckInterval) {
    clearInterval(statusCheckInterval)
  }
})

const loadModels = async () => {
  try {
    const res = await axios.get('/api/models')
    models.value = res.data.models || []
    const current = models.value.find(m => m.current)
    if (current) {
      modelForm.value.model = current.name
    }
  } catch (error) {
    console.error('加载模型列表失败:', error)
    ElMessage.error('加载模型列表失败')
  }
}

const loadVideoUrl = async () => {
  try {
    const res = await axios.get('/api/video')
    if (res.data.video_url) {
      videoForm.value.video_url = res.data.video_url
    }
    if (res.data.camera_ip) {
      videoForm.value.camera_ip = res.data.camera_ip
    }
    if (res.data.camera_status) {
      videoForm.value.camera_status = res.data.camera_status
    }
    if (res.data.camera_check_interval) {
      videoForm.value.camera_check_interval = res.data.camera_check_interval
    }
  } catch (error) {
    console.error('加载视频配置失败:', error)
  }
}

// 获取摄像头状态类型
const getCameraStatusType = (status) => {
  switch (status) {
    case 'online':
      return 'success'
    case 'offline':
      return 'danger'
    default:
      return 'info'
  }
}

// 获取摄像头状态文本
const getCameraStatusText = (status) => {
  switch (status) {
    case 'online':
      return '在线'
    case 'offline':
      return '离线'
    default:
      return '未知'
  }
}

// 检测摄像头状态
const checkCameraStatus = async () => {
  statusChecking.value = true
  try {
    const res = await axios.get('/api/video')
    if (res.data.camera_status) {
      videoForm.value.camera_status = res.data.camera_status
      if (res.data.camera_ip) {
        videoForm.value.camera_ip = res.data.camera_ip
      }
      if (res.data.camera_check_interval) {
        videoForm.value.camera_check_interval = res.data.camera_check_interval
      }
    }
  } catch (error) {
    console.error('检测摄像头状态失败:', error)
    ElMessage.error('检测摄像头状态失败')
  } finally {
    statusChecking.value = false
  }
}

const loadClasses = async () => {
  try {
    const res = await axios.get('/api/classes')
    classesData.value = res.data.classes || []
    enabledClasses.value = res.data.enabled_classes || []
  } catch (error) {
    console.error('加载类别列表失败:', error)
    ElMessage.error('加载类别列表失败')
  }
}

const loadDisplayConfig = async () => {
  try {
    const res = await axios.get('/api/display')
    if (res.data.font_size) {
      displayForm.value.font_size = res.data.font_size
    }
    if (res.data.box_thickness) {
      displayForm.value.box_thickness = res.data.box_thickness
    }
    if (res.data.box_color) {
      // 后端已经返回 RGB 格式，直接使用
      const rgb = res.data.box_color
      displayForm.value.box_color_hex = rgbToHex(rgb[0], rgb[1], rgb[2])
      displayForm.value.box_color_rgb = rgb.join(',')
    }
    if (res.data.text_color) {
      displayForm.value.text_color_hex = rgbToHex(
        res.data.text_color[0],
        res.data.text_color[1],
        res.data.text_color[2]
      )
      displayForm.value.text_color_rgb = res.data.text_color.join(',')
    }
    if (res.data.use_chinese !== undefined) {
      displayForm.value.use_chinese = res.data.use_chinese
    }
    if (res.data.zone_fill_color) {
      const rgb = res.data.zone_fill_color
      displayForm.value.zone_fill_color_hex = rgbToHex(rgb[0], rgb[1], rgb[2])
      displayForm.value.zone_fill_color_rgb = rgb.join(',')
    }
    if (res.data.zone_border_color) {
      const rgb = res.data.zone_border_color
      displayForm.value.zone_border_color_hex = rgbToHex(rgb[0], rgb[1], rgb[2])
      displayForm.value.zone_border_color_rgb = rgb.join(',')
    }
    if (res.data.zone_fill_alpha !== undefined) {
      displayForm.value.zone_fill_alpha = res.data.zone_fill_alpha
    }
  } catch (error) {
    console.error('加载显示配置失败:', error)
  }
}

const loadAlarmConfig = async () => {
  try {
    const res = await axios.get('/api/alarm')
    if (res.data.debounce_time !== undefined) {
      alarmForm.value.debounce_time = res.data.debounce_time
    }
    if (res.data.detection_mode !== undefined) {
      alarmForm.value.detection_mode = res.data.detection_mode
    }
    if (res.data.once_per_id !== undefined) {
      alarmForm.value.once_per_id = res.data.once_per_id
    }
    if (res.data.save_event_video !== undefined) {
      alarmForm.value.save_event_video = res.data.save_event_video
    }
    if (res.data.save_event_image !== undefined) {
      alarmForm.value.save_event_image = res.data.save_event_image
    }
    if (res.data.event_video_duration !== undefined) {
      alarmForm.value.event_video_duration = res.data.event_video_duration
    }
    if (res.data.event_save_path !== undefined) {
      alarmForm.value.event_save_path = res.data.event_save_path
    }
  } catch (error) {
    console.error('加载报警配置失败:', error)
  }
}

const loadOcclusionConfig = async () => {
  try {
    const res = await axios.get('/api/occlusion')
    if (res.data.enabled !== undefined) {
      occlusionForm.value.enabled = res.data.enabled
    }
    if (res.data.check_interval !== undefined) {
      occlusionForm.value.check_interval = res.data.check_interval
    }
    if (res.data.occlusion_threshold !== undefined) {
      occlusionForm.value.occlusion_threshold = res.data.occlusion_threshold
    }
  } catch (error) {
    console.error('加载遮挡检测配置失败:', error)
  }
}

// 应用配置
const applyModel = async () => {
  if (!modelForm.value.model) {
    ElMessage.warning('请选择一个模型')
    return
  }
  
  try {
    await ElMessageBox.confirm(
      `确定要切换到模型 "${modelForm.value.model}" 吗？切换后检测将使用新模型。`,
      '确认切换',
      { type: 'warning' }
    )
    
    modelLoading.value = true
    const res = await axios.post('/api/model', { model: modelForm.value.model })
    if (res.data.success) {
      ElMessage.success(res.data.message)
      emit('model-changed')
      loadModels()
    } else {
      ElMessage.error('切换失败: ' + res.data.message)
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('切换模型失败:', error)
      ElMessage.error('切换模型失败')
    }
  } finally {
    modelLoading.value = false
  }
}

const applyVideo = async () => {
  if (!videoForm.value.video_url.trim()) {
    ElMessage.warning('请输入视频URL')
    return
  }
  
  try {
    await ElMessageBox.confirm(
      `确定要更改视频源为 "${videoForm.value.video_url}" 吗？更改后视频流将重新连接。`,
      '确认更改',
      { type: 'warning' }
    )
    
    videoLoading.value = true
    const res = await axios.post('/api/video', { 
      video_url: videoForm.value.video_url,
      camera_ip: videoForm.value.camera_ip || '',
      camera_check_interval: videoForm.value.camera_check_interval
    })
    if (res.data.success) {
      ElMessage.success(res.data.message)
      // 更新状态（包括空字符串）
      if (res.data.camera_ip !== undefined) {
        videoForm.value.camera_ip = res.data.camera_ip
      }
      if (res.data.camera_status) {
        videoForm.value.camera_status = res.data.camera_status
      }
      if (res.data.camera_check_interval) {
        videoForm.value.camera_check_interval = res.data.camera_check_interval
      }
      emit('video-changed')
    } else {
      ElMessage.error('设置失败: ' + res.data.message)
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('设置视频配置失败:', error)
      ElMessage.error('设置视频配置失败')
    }
  } finally {
    videoLoading.value = false
  }
}

const selectAllClasses = () => {
  enabledClasses.value = classesData.value.map(cls => cls.id)
}

const deselectAllClasses = () => {
  enabledClasses.value = []
}

const handleClassToggle = (classId) => {
  // 已由 checkbox 的 v-model 处理
}

const applyClasses = async () => {
  if (enabledClasses.value.length === 0) {
    ElMessage.warning('请至少选择一个类别')
    return
  }
  
  try {
    await ElMessageBox.confirm(
      `确定要启用 ${enabledClasses.value.length} 个类别吗？`,
      '确认应用',
      { type: 'warning' }
    )
    
    classesLoading.value = true
    const res = await axios.post('/api/classes/enabled', {
      enabled_classes: enabledClasses.value
    })
    if (res.data.success) {
      ElMessage.success(res.data.message)
      emit('classes-changed')
      loadClasses()
    } else {
      ElMessage.error('设置失败: ' + res.data.message)
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('设置类别失败:', error)
      ElMessage.error('设置类别失败')
    }
  } finally {
    classesLoading.value = false
  }
}

const saveCustomName = async (classId) => {
  const cls = classesData.value.find(c => c.id === classId)
  if (!cls) return
  
  try {
    await axios.post('/api/classes/custom-name', {
      class_id: classId,
      custom_name: cls.custom_name || null
    })
    loadClasses()
  } catch (error) {
    console.error('保存自定义名称失败:', error)
  }
}

const saveConfidence = async (classId) => {
  const cls = classesData.value.find(c => c.id === classId)
  if (!cls) return
  
  try {
    await axios.post('/api/classes/confidence', {
      class_id: classId,
      confidence_threshold: cls.confidence_threshold
    })
    ElMessage.success('保存成功')
    loadClasses()
  } catch (error) {
    console.error('保存置信度阈值失败:', error)
    ElMessage.error('保存失败')
  }
}

const toggleLanguage = async () => {
  displayForm.value.use_chinese = !displayForm.value.use_chinese
  await applyDisplay()
}

const applyDisplay = async () => {
  const boxColorRgbArray = displayForm.value.box_color_rgb.split(',').map(x => parseInt(x.trim()))
  if (boxColorRgbArray.length !== 3 || !boxColorRgbArray.every(x => !isNaN(x) && x >= 0 && x <= 255)) {
    ElMessage.error('边框颜色格式错误，请输入RGB格式，如: 0,255,0')
    return
  }
  // 前端发送 RGB 格式，后端会转换为 BGR
  const boxColor = boxColorRgbArray // RGB 格式
  
  const textColorArray = displayForm.value.text_color_rgb.split(',').map(x => parseInt(x.trim()))
  if (textColorArray.length !== 3 || !textColorArray.every(x => !isNaN(x) && x >= 0 && x <= 255)) {
    ElMessage.error('文字颜色格式错误，请输入RGB格式，如: 0,0,0')
    return
  }
  
  const zoneFillColorArray = displayForm.value.zone_fill_color_rgb.split(',').map(x => parseInt(x.trim()))
  if (zoneFillColorArray.length !== 3 || !zoneFillColorArray.every(x => !isNaN(x) && x >= 0 && x <= 255)) {
    ElMessage.error('报警区域填充颜色格式错误，请输入RGB格式，如: 0,255,255')
    return
  }
  
  const zoneBorderColorArray = displayForm.value.zone_border_color_rgb.split(',').map(x => parseInt(x.trim()))
  if (zoneBorderColorArray.length !== 3 || !zoneBorderColorArray.every(x => !isNaN(x) && x >= 0 && x <= 255)) {
    ElMessage.error('报警区域边框颜色格式错误，请输入RGB格式，如: 0,255,255')
    return
  }
  
  displayLoading.value = true
  try {
    const res = await axios.post('/api/display', {
      font_size: displayForm.value.font_size,
      box_thickness: displayForm.value.box_thickness,
      box_color: boxColor, // 发送 RGB 格式
      text_color: textColorArray, // 发送 RGB 格式
      use_chinese: displayForm.value.use_chinese,
      zone_fill_color: zoneFillColorArray, // 发送 RGB 格式
      zone_border_color: zoneBorderColorArray, // 发送 RGB 格式
      zone_fill_alpha: displayForm.value.zone_fill_alpha
    })
    if (res.data.success) {
      ElMessage.success(res.data.message)
      emit('display-changed')
    } else {
      ElMessage.error('设置失败: ' + res.data.message)
    }
  } catch (error) {
    console.error('设置显示配置失败:', error)
    ElMessage.error('设置失败')
  } finally {
    displayLoading.value = false
  }
}

const selectEventSavePath = async () => {
  try {
    const { value: path } = await ElMessageBox.prompt(
      '请输入事件保存路径（绝对路径）',
      '选择保存路径',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        inputValue: alarmForm.value.event_save_path,
        inputValidator: (value) => {
          if (!value || !value.trim()) {
            return '路径不能为空'
          }
          return true
        }
      }
    )
    
    if (path) {
      alarmForm.value.event_save_path = path.trim()
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('选择路径失败:', error)
    }
  }
}

const applyAlarm = async () => {
  alarmLoading.value = true
  try {
    const res = await axios.post('/api/alarm', {
      debounce_time: alarmForm.value.debounce_time,
      detection_mode: alarmForm.value.detection_mode,
      once_per_id: alarmForm.value.once_per_id,
      save_event_video: alarmForm.value.save_event_video,
      save_event_image: alarmForm.value.save_event_image,
      event_video_duration: alarmForm.value.event_video_duration,
      event_save_path: alarmForm.value.event_save_path
    })
    if (res.data.success) {
      ElMessage.success(res.data.message)
      emit('alarm-changed')
    } else {
      ElMessage.error('设置失败: ' + res.data.message)
    }
  } catch (error) {
    console.error('设置报警配置失败:', error)
    ElMessage.error('设置失败')
  } finally {
    alarmLoading.value = false
  }
}

const applyOcclusion = async () => {
  occlusionLoading.value = true
  try {
    const res = await axios.post('/api/occlusion', {
      enabled: occlusionForm.value.enabled,
      check_interval: occlusionForm.value.check_interval,
      occlusion_threshold: occlusionForm.value.occlusion_threshold
    })
    if (res.data.success) {
      ElMessage.success(res.data.message)
    } else {
      ElMessage.error('设置失败: ' + res.data.message)
    }
  } catch (error) {
    console.error('设置遮挡检测配置失败:', error)
    ElMessage.error('设置失败')
  } finally {
    occlusionLoading.value = false
  }
}
</script>

<style scoped>
.config-panel {
  padding: 20px;
}

.classes-controls {
  display: flex;
  gap: 10px;
  margin-bottom: 15px;
}

.classes-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 10px;
}

.class-item {
  padding: 10px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.class-item.enabled {
  background: #f0f9ff;
  border-color: #409eff;
}

.class-name-cn {
  font-weight: 600;
  color: #333;
}

.class-name-en {
  font-size: 12px;
  color: #666;
  margin-left: 5px;
}
</style>

