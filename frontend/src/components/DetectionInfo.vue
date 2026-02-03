<template>
  <div class="detection-info">
    <el-empty v-if="detections.length === 0" description="等待检测数据..." />
    <el-scrollbar height="400px">
      <div
        v-for="(det, index) in detections"
        :key="index"
        class="detection-item"
        :class="{ 'in-zone': det.in_zone }"
      >
        <div>
          <span class="class-name">{{ det.class_name_cn || det.class_name || '对象' }}</span>
          <span class="id"> ID: {{ det.id }}</span>
          <el-tag v-if="det.in_zone" type="danger" size="small" style="margin-left: 10px">
            在区域内
          </el-tag>
        </div>
        <div class="details">
          置信度: {{ (det.confidence * 100).toFixed(1) }}% |
          位置: ({{ det.center.x.toFixed(0) }}, {{ det.center.y.toFixed(0) }})
        </div>
      </div>
    </el-scrollbar>
  </div>
</template>

<script setup>
defineProps({
  detections: {
    type: Array,
    default: () => []
  }
})
</script>

<style scoped>
.detection-info {
  min-height: 200px;
}

.detection-item {
  background: white;
  padding: 10px;
  margin-bottom: 8px;
  border-radius: 6px;
  border-left: 4px solid #409eff;
}

.detection-item.in-zone {
  border-left-color: #f56c6c;
  background: #fef0f0;
}

.id {
  font-weight: 600;
  color: #409eff;
}

.detection-item.in-zone .id {
  color: #f56c6c;
}

.class-name {
  font-weight: 600;
  color: #409eff;
}

.detection-item.in-zone .class-name {
  color: #f56c6c;
}

.details {
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
}
</style>

