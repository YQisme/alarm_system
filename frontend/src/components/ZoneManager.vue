<template>
  <el-card shadow="hover">
    <template #header>
      <div class="card-header">
        <span>区域管理</span>
        <el-button type="primary" size="small" @click="startDrawing">新建区域</el-button>
      </div>
    </template>
    
    <div class="zone-list">
      <el-empty v-if="zones.length === 0" description="暂无区域" :image-size="80" />
      <div v-else>
        <div
          v-for="zone in zones"
          :key="zone.id"
          class="zone-item"
          :class="{ active: selectedZoneId === zone.id, disabled: !zone.enabled }"
        >
          <div class="zone-info" @click="selectZone(zone.id)">
            <div class="zone-name">
              <el-icon v-if="zone.enabled"><Check /></el-icon>
              <el-icon v-else><Close /></el-icon>
              <span>{{ zone.name }}</span>
            </div>
            <div class="zone-meta">
              <span>{{ zone.points?.length || 0 }} 个顶点</span>
            </div>
          </div>
          <div class="zone-actions">
            <el-switch
              v-model="zone.enabled"
              size="small"
              @change="updateZoneEnabled(zone)"
            />
            <el-button
              type="primary"
              size="small"
              link
              @click="editZone(zone)"
            >
              编辑
            </el-button>
            <el-button
              type="primary"
              size="small"
              link
              @click="renameZone(zone)"
            >
              重命名
            </el-button>
            <el-button
              type="danger"
              size="small"
              link
              @click="deleteZone(zone)"
            >
              删除
            </el-button>
          </div>
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { ref, defineProps, defineEmits } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Check, Close } from '@element-plus/icons-vue'
import axios from 'axios'

const props = defineProps({
  zones: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['zone-selected', 'start-drawing', 'zone-updated'])

const selectedZoneId = ref(null)

const selectZone = (zoneId) => {
  selectedZoneId.value = zoneId
  emit('zone-selected', zoneId)
}

const startDrawing = () => {
  emit('start-drawing')
}

const editZone = (zone) => {
  emit('zone-selected', zone.id)
  emit('start-drawing', zone)
}

const updateZoneEnabled = async (zone) => {
  try {
    const res = await axios.put(`/api/zones/${zone.id}`, {
      enabled: zone.enabled
    })
    if (res.data.success) {
      ElMessage.success(zone.enabled ? '区域已启用' : '区域已禁用')
      emit('zone-updated')
    }
  } catch (error) {
    console.error('更新区域状态失败:', error)
    ElMessage.error('更新失败')
    zone.enabled = !zone.enabled  // 回滚
  }
}

const renameZone = async (zone) => {
  try {
    const { value: newName } = await ElMessageBox.prompt(
      '请输入新的区域名称',
      '重命名区域',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        inputValue: zone.name,
        inputValidator: (value) => {
          if (!value || !value.trim()) {
            return '区域名称不能为空'
          }
          return true
        }
      }
    )
    
    const res = await axios.post(`/api/zones/${zone.id}/rename`, {
      name: newName.trim()
    })
    
    if (res.data.success) {
      ElMessage.success('区域已重命名')
      emit('zone-updated')
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('重命名失败:', error)
      ElMessage.error('重命名失败')
    }
  }
}

const deleteZone = async (zone) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除区域"${zone.name}"吗？`,
      '确认删除',
      {
        type: 'warning',
        confirmButtonText: '删除',
        cancelButtonText: '取消'
      }
    )
    
    const res = await axios.delete(`/api/zones/${zone.id}`)
    
    if (res.data.success) {
      ElMessage.success('区域已删除')
      if (selectedZoneId.value === zone.id) {
        selectedZoneId.value = null
      }
      emit('zone-updated')
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
      ElMessage.error('删除失败')
    }
  }
}
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.zone-list {
  max-height: 400px;
  overflow-y: auto;
}

.zone-item {
  padding: 12px;
  margin-bottom: 8px;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  background: #fafafa;
  transition: all 0.3s;
}

.zone-item:hover {
  background: #f0f2f5;
  border-color: #c0c4cc;
}

.zone-item.active {
  border-color: #409eff;
  background: #ecf5ff;
}

.zone-item.disabled {
  opacity: 0.6;
}

.zone-info {
  cursor: pointer;
  margin-bottom: 8px;
}

.zone-name {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
  margin-bottom: 4px;
}

.zone-meta {
  font-size: 12px;
  color: #909399;
  margin-left: 24px;
}

.zone-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: flex-end;
}
</style>

