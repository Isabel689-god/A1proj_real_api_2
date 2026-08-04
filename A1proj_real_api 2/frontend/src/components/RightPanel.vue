<template>
  <div class="right-panel">
    <div class="panel-section">
      <div class="panel-header" @click="sopExpanded = !sopExpanded">
        <span>📋 检修作业指引</span>
        <span class="collapse-icon">{{ sopExpanded ? '▼' : '▶' }}</span>
      </div>
      <div v-show="sopExpanded">
        <SopFlow @all-done="isAllDone = $event" />
      </div>
    </div>

    <div class="panel-section">
      <div class="panel-header" @click="reportExpanded = !reportExpanded">
        <span>📝 闭环报告</span>
        <span class="collapse-icon">{{ reportExpanded ? '▼' : '▶' }}</span>
      </div>
      <div v-show="reportExpanded">
        <RepairReport
          v-if="store.hasPermission('submit_report')"
          :isEnabled="isAllDone"
          :orderId="currentOrderId"
          :dispatchTime="dispatchTime"
          @report-submitted="handleReportSubmit"
        />
        <div v-else class="intern-notice glass-card">
           <p>⚠️ 访客账号</p>
           <p style="font-size: 12px; margin-top: 5px;">暂不具备实操提报权限，请仅作为学习指导参考。</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import SopFlow from './SopFlow.vue';
import RepairReport from './RepairReport.vue';
import { useChatStore } from '../stores/chat';

const store = useChatStore();

const props = defineProps<{
  sessionId: string;
  messages: any[];
  deviceModel?: string;
}>();
const emit = defineEmits<{
  (e: 'report-submitted', report: any): void;
}>();

const sopExpanded = ref(true);
const reportExpanded = ref(true);
const isAllDone = ref(false);

const currentOrderId = computed(() => props.sessionId);
const dispatchTime = computed(() => {
  const timestamp = props.sessionId.replace('session_', '');
  const date = new Date(parseInt(timestamp));
  return date.toLocaleString('zh-CN');
});

const handleReportSubmit = () => {
  const report = {
    orderId: currentOrderId.value,
    dispatchTime: dispatchTime.value,
    submitTime: new Date().toLocaleString('zh-CN'),
    deviceModel: props.deviceModel || '未指定',
    messages: [...props.messages]
  };
  emit('report-submitted', report);
};
</script>

<style scoped>
.right-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 16px;
  background-color: var(--bg-dark);
  overflow-y: auto;
  gap: 16px;
}
.intern-notice {
   background: color-mix(in srgb, var(--danger) 12%, transparent);
   border: 1px solid color-mix(in srgb, var(--danger) 32%, transparent);
   color: var(--danger);
   padding: 15px;
   text-align: center;
   border-radius: 8px;
   font-weight: bold;
   flex-shrink: 0;
}

.panel-section {
  display: flex;
  flex-direction: column;
}
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  background: var(--bg-glass);
  border: 1px solid var(--border-glass);
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
  transition: all 0.2s;
  user-select: none;
}
.panel-header:hover {
  border-color: var(--primary-color);
  background: var(--bg-hover);
}
.collapse-icon {
  font-size: 10px;
  color: var(--text-muted);
}
</style>
