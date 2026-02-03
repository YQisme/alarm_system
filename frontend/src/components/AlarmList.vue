<template>
  <div class="alarm-list">
    <el-empty v-if="alarms.length === 0" description="暂无报警记录" />
    <el-scrollbar height="400px">
      <div v-for="(alarm, index) in alarms" :key="index" class="alarm-item">
        <div class="alarm-time">{{ alarm.time }}</div>
        <div class="alarm-info">
          <span class="object-name">{{ alarm.object_name || alarm.class_name_cn || '对象' }}</span>
          <span class="person-id"> ID: {{ alarm.track_id !== undefined ? alarm.track_id : alarm.person_id }}</span>
          <span> 进入监控区域</span>
          <br>
          <span class="alarm-position">位置: ({{ alarm.position.x.toFixed(0) }}, {{ alarm.position.y.toFixed(0) }})</span>
        </div>
      </div>
    </el-scrollbar>
  </div>
</template>

<script setup>
defineProps({
  alarms: {
    type: Array,
    default: () => []
  }
})
</script>

<style scoped>
.alarm-list {
  min-height: 200px;
}

.alarm-item {
  background: white;
  padding: 12px;
  margin-bottom: 10px;
  border-radius: 6px;
  border-left: 4px solid #f56c6c;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(-20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.alarm-time {
  font-size: 12px;
  color: #909399;
  margin-bottom: 5px;
}

.alarm-info {
  font-size: 14px;
  color: #303133;
}

.person-id {
  font-weight: 600;
  color: #f56c6c;
}

.object-name {
  font-weight: 600;
  color: #409eff;
}

.alarm-position {
  font-size: 12px;
  color: #909399;
}
</style>

