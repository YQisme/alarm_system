<template>
  <div class="log-panel">
    <el-empty v-if="logs.length === 0" description="等待日志数据..." />
    <el-scrollbar
      height="400px"
      ref="scrollbarRef"
      @scroll="handleScroll"
    >
      <div
        v-for="(log, index) in logs"
        :key="index"
        class="log-entry"
        :class="[`log-${log.logger}`, `log-${log.level}`]"
      >
        <span class="log-timestamp">{{ log.timestamp }}</span>
        <span class="log-level">[{{ log.level }}]</span>
        <span class="log-message">{{ log.message }}</span>
      </div>
    </el-scrollbar>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'

const props = defineProps({
  logs: {
    type: Array,
    default: () => []
  },
  autoScroll: {
    type: Boolean,
    default: true
  }
})

const scrollbarRef = ref(null)

watch(() => props.logs.length, () => {
  if (props.autoScroll) {
    nextTick(() => {
      if (scrollbarRef.value) {
        const scrollbar = scrollbarRef.value
        scrollbar.setScrollTop(scrollbar.wrapRef.scrollHeight)
      }
    })
  }
})

const handleScroll = () => {
  // 可以在这里处理滚动事件
}
</script>

<style scoped>
.log-panel {
  min-height: 200px;
}

.log-entry {
  margin-bottom: 4px;
  padding: 2px 0;
  word-wrap: break-word;
  font-family: 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.5;
}

.log-entry.log-backend {
  color: #4ec9b0;
}

.log-entry.log-yolo,
.log-entry.log-ultralytics {
  color: #dcdcaa;
}

.log-entry.log-INFO {
  color: #4ec9b0;
}

.log-entry.log-WARNING {
  color: #ce9178;
}

.log-entry.log-ERROR,
.log-entry.log-CRITICAL {
  color: #f48771;
}

.log-entry.log-CRITICAL {
  font-weight: bold;
}

.log-timestamp {
  color: #808080;
  margin-right: 8px;
}

.log-level {
  margin-right: 8px;
  font-weight: bold;
}

.log-message {
  color: inherit;
}
</style>

