<template>
  <div class="alarm-list">
    <el-empty v-if="alarms.length === 0" description="暂无报警记录" />
    <el-scrollbar height="400px">
      <div 
        v-for="(alarm, index) in alarms" 
        :key="index" 
        class="alarm-item"
        :class="getAlarmTypeClass(alarm.alarm_type)"
      >
        <div class="alarm-time">{{ alarm.time }}</div>
        <div class="alarm-info">
          <!-- 区域报警格式 -->
          <template v-if="alarm.alarm_type === 'zone' || !alarm.alarm_type">
            <span class="object-name">{{ alarm.object_name || alarm.class_name_cn || '对象' }}</span>
            <span class="person-id"> ID: {{ alarm.track_id !== undefined ? alarm.track_id : alarm.person_id }}</span>
            <span> 进入</span>
            <span class="zone-name" v-if="alarm.zone_name">【{{ alarm.zone_name }}】</span>
            <span v-else>监控区域</span>
            <br>
            <span class="alarm-position">位置: ({{ alarm.position.x.toFixed(0) }}, {{ alarm.position.y.toFixed(0) }})</span>
          </template>
          
          <!-- 摄像头离线报警格式 -->
          <template v-else-if="alarm.alarm_type === 'camera_offline'">
            <span class="alarm-icon">📹</span>
            <span class="alarm-title">摄像头离线</span>
            <span class="alarm-detail" v-if="alarm.camera_ip"> - IP: {{ alarm.camera_ip }}</span>
            <br>
            <span class="alarm-desc">摄像头连接已断开，请检查网络连接</span>
          </template>
          
          <!-- 画面遮挡报警格式 -->
          <template v-else-if="alarm.alarm_type === 'occlusion'">
            <span class="alarm-icon">🚫</span>
            <span class="alarm-title">画面遮挡</span>
            <span class="alarm-detail" v-if="alarm.occlusion_ratio !== undefined"> - 遮挡率: {{ alarm.occlusion_ratio }}%</span>
            <br>
            <span class="alarm-desc">检测到画面被遮挡，请检查摄像头</span>
          </template>
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

// 根据报警类型返回对应的CSS类名
const getAlarmTypeClass = (alarmType) => {
  switch (alarmType) {
    case 'camera_offline':
      return 'alarm-camera-offline'
    case 'occlusion':
      return 'alarm-occlusion'
    case 'zone':
    default:
      return 'alarm-zone'
  }
}
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
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  animation: slideIn 0.3s ease-out;
}

/* 区域报警 - 红色 */
.alarm-zone {
  border-left: 4px solid #f56c6c;
}

/* 摄像头离线报警 - 橙色 */
.alarm-camera-offline {
  border-left: 4px solid #e6a23c;
  background: #fdf6ec;
}

/* 画面遮挡报警 - 黄色 */
.alarm-occlusion {
  border-left: 4px solid #f0a020;
  background: #fef9e7;
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

.zone-name {
  font-weight: 600;
  color: #67c23a;
}

/* 系统报警样式 */
.alarm-icon {
  font-size: 16px;
  margin-right: 6px;
}

.alarm-title {
  font-weight: 600;
  font-size: 15px;
}

.alarm-camera-offline .alarm-title {
  color: #e6a23c;
}

.alarm-occlusion .alarm-title {
  color: #f0a020;
}

.alarm-detail {
  color: #606266;
  font-weight: 500;
}

.alarm-desc {
  font-size: 12px;
  color: #909399;
  font-style: italic;
}
</style>

