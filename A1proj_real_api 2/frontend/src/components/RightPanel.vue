<template>
  <div class="right-panel">
    <SopFlow v-model:activeStep="activeStep" @all-completed="handleAllStepsCompleted" />

    <RepairReport
      v-if="store.hasPermission('submit_report')"
      :isEnabled="isAllStepsCompleted"
      :orderId="currentOrderId"
      :dispatchTime="dispatchTime"
      @report-submitted="handleReportSubmit"
    />
    <div v-else class="intern-notice glass-card">
       <p>⚠️ 实习账号</p>
       <p style="font-size: 12px; margin-top: 5px;">暂不具备实操提报权限，请仅作为学习指导参考。</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
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

const activeStep = ref(0);
const isAllStepsCompleted = ref(false);

const currentOrderId = computed(() => props.sessionId);
const dispatchTime = computed(() => {
  const timestamp = props.sessionId.replace('session_', '');
  const date = new Date(parseInt(timestamp));
  return date.toLocaleString('zh-CN');
});

watch(() => props.sessionId, () => {
  activeStep.value = 0;
  isAllStepsCompleted.value = false;
});

const handleAllStepsCompleted = () => {
  isAllStepsCompleted.value = true;
};

const handleReportSubmit = () => {
  const report = {
    orderId: currentOrderId.value,
    dispatchTime: dispatchTime.value,
    submitTime: new Date().toLocaleString('zh-CN'),
    deviceModel: props.deviceModel || '未指定',
    messages: [...props.messages],
    stepCount: activeStep.value
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
  background-color: #0f172a;
  overflow-y: auto;
  gap: 16px;
}
.intern-notice {
   background: rgba(239, 68, 68, 0.1);
   border: 1px solid rgba(239, 68, 68, 0.3);
   color: #fca5a5;
   padding: 15px;
   text-align: center;
   border-radius: 8px;
   font-weight: bold;
   flex-shrink: 0;
}
</style>