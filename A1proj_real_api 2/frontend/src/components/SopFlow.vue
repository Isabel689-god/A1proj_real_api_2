<template>
  <div class="sop-flow">
    <div class="sop-header">
      <h4>📋 动态检修作业指引 (<span class="text-accent">SOP</span>)</h4>
      <p class="sub-title">根据 AI 分析结果实时生成</p>
    </div>
    <div class="steps-wrapper" v-if="dynamicSteps.length > 0">
      <el-steps direction="vertical" :active="activeStep" finish-status="success">
        <el-step v-for="(step, index) in dynamicSteps" :key="index" :title="step.title">
          <template #description>
            <div class="step-desc-content">
              <div class="ai-instruction">{{ step.desc }}</div>
              <div v-if="activeStep === index" class="step-action-zone">
                <el-radio-group v-model="step.selectedOption" class="cyber-radio-group">
                  <el-radio v-for="opt in step.options" :key="opt" :label="opt">{{ opt }}</el-radio>
                </el-radio-group>
                <el-button
                  type="primary"
                  size="small"
                  class="next-action-btn"
                  :disabled="!step.selectedOption"
                  @click="nextStep"
                >
                  确认记录并进入下一步
                </el-button>
              </div>
              <div v-else-if="activeStep > index" class="completed-badge">
                <el-icon><Check /></el-icon>
                <span>操作结果: {{ step.selectedOption }}</span>
              </div>
            </div>
          </template>
        </el-step>
        <el-step title="归档与复位" v-if="activeStep >= dynamicSteps.length">
          <template #description>
            <div class="step-desc-content">
              <p class="text-green">所有智能生成的检修步骤均已确认完毕，设备已具备复位条件。</p>
              <p class="text-green" style="margin-top: 8px;">请在下方提交报告并归档工单。</p>
            </div>
          </template>
        </el-step>
      </el-steps>
    </div>
    <div v-else class="empty-state">
      <div class="radar-scan"></div>
      <p>正在监听多模态诊断链路<br/>等待 AI 生成标准化排障步骤...</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue';
import { useChatStore } from '../stores/chat';
import { Check } from '@element-plus/icons-vue';

const store = useChatStore();
const props = defineProps<{
  activeStep: number;
}>();
const emit = defineEmits<{
  (e: 'update:activeStep', value: number): void;
  (e: 'all-completed'): void;
}>();

const dynamicSteps = ref<any[]>([]);

// 监听对话消息，当 AI 给出新回答时动态提取 SOP 步骤
watch(
  () => store.messages,
  (newMessages) => {
    const lastAiMsg = [...newMessages].reverse().find(m => m.role === 'assistant' && m.status === 'done');
    if (lastAiMsg && lastAiMsg.content) {
      const content = lastAiMsg.content;
      const lines = content.split('\n');
      const extractedSteps = [];
      let currentStep = null;

      // 只提取「三、解决方案」板块的步骤
      let inSolution = false;
      for (const line of lines) {
        if (line.includes('三、解决方案') || line.includes('解决方案')) {
          inSolution = true;
          continue;
        }
        // 遇到下一板块就停止
        if (inSolution && (line.includes('四、经验总结') || line.includes('经验总结'))) {
          break;
        }
        if (!inSolution) continue;

        const match = line.match(/^(\d+)[\.\、]\s*(.*)/);
        if (match) {
          if (currentStep) extractedSteps.push(currentStep);
          currentStep = {
            title: `检修动作 ${match[1]}`,
            desc: match[2].replace(/\*/g, ''),
            options: ['✅ 检测正常，无异常', '⚠️ 发现故障，已原位修复', '🔧 部件损坏，已更换新件'],
            selectedOption: ''
          };
        } else if (currentStep && line.trim() && !line.startsWith('![')) {
          currentStep.desc += '\n' + line.trim().replace(/\*/g, '');
        }
      }
      if (currentStep) extractedSteps.push(currentStep);

      if (extractedSteps.length > 0) {
        dynamicSteps.value = extractedSteps;
        emit('update:activeStep', 0);
      } else {
        dynamicSteps.value = [];
      }
    } else {
      // 无有效 AI 回答时清空步骤，切换会话自动重置
      dynamicSteps.value = [];
    }
  },
  { deep: true, immediate: true }
);

const nextStep = () => {
  const nextVal = props.activeStep + 1;
  emit('update:activeStep', nextVal);
  // 全部步骤完成，触发事件
  if (nextVal >= dynamicSteps.value.length) {
    emit('all-completed');
  }
};
</script>

<style scoped>
.sop-flow {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 0;
}
.sop-header {
  margin-bottom: 24px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  padding-bottom: 12px;
  flex-shrink: 0;
}
.sop-header h4 {
  margin: 0;
  color: #f8fafc;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 1px;
}
.sub-title {
  font-size: 12px;
  color: #64748b;
  margin-top: 6px;
}
.text-accent { color: var(--primary-light); }
.text-green { color: var(--success); font-weight: bold; }

.steps-wrapper {
  flex: 1;
  overflow-y: auto;
  padding-right: 8px;
  min-height: 0;
}
:deep(.el-step__title) {
  font-size: 14px !important;
  font-weight: 600;
}
:deep(.el-step__title.is-process) { color: #38bdf8 !important; }
:deep(.el-step__title.is-wait) { color: #64748b !important; }
:deep(.el-step__title.is-success) { color: #10b981 !important; }

.step-desc-content {
  margin-top: 8px;
  margin-bottom: 16px;
}
.ai-instruction {
  font-size: 13px; line-height: 1.6; color: var(--text-primary);
  background: rgba(0, 0, 0, 0.2);
  padding: 10px 12px; border-radius: 6px;
  border-left: 2px solid var(--primary-color);
}

.step-action-zone {
  margin-top: 12px; background: rgba(0, 0, 0, 0.15);
  padding: 12px; border-radius: 8px;
  border: 1px dashed var(--border-light);
}
.cyber-radio-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}
:deep(.el-radio) {
  color: #94a3b8;
  margin-right: 0;
  height: auto;
}
:deep(.el-radio__input.is-checked + .el-radio__label) {
  color: #38bdf8;
}
.next-action-btn {
  width: 100%; border-radius: 6px;
  background: linear-gradient(90deg, #3a5078, #4a6596);
  border: none;
}
.next-action-btn:disabled {
  background: #334155;
  color: #64748b;
}
.completed-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 10px;
  font-size: 12px;
  color: #10b981;
  background: rgba(16, 185, 129, 0.1);
  padding: 6px 10px;
  border-radius: 4px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 60%;
  color: #64748b;
  text-align: center;
  font-size: 13px;
  line-height: 1.6;
}
.radar-scan {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  border: 1px solid rgba(56, 189, 248, 0.2);
  position: relative;
  margin-bottom: 20px;
  overflow: hidden;
}
.radar-scan::before {
  content: ''; position: absolute;
  top: 50%; left: 50%; width: 50%; height: 50%;
  background: conic-gradient(from 0deg, transparent 70%, rgba(107, 137, 196, 0.5) 100%);
  transform-origin: 0 0; animation: scan 2s linear infinite;
}
@keyframes scan {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
.steps-wrapper::-webkit-scrollbar { width: 4px; }
.steps-wrapper::-webkit-scrollbar-thumb { background: #334155; border-radius: 4px; }
</style>
