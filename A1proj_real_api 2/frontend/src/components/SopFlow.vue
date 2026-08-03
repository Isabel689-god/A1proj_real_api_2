<template>
  <div class="sop-flow">
    <div class="sop-header">
      <h4>📋 动态检修作业指引 (<span class="text-accent">SOP</span>)</h4>
      <p class="sub-title">{{ sopMeta }}</p>
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
                <el-button type="primary" size="small" class="next-action-btn"
                  :disabled="!step.selectedOption" @click="nextStep">
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
          <template #description><p class="text-green">所有检修步骤均已确认完毕。</p></template>
        </el-step>
      </el-steps>
      <div v-if="sopNotes.length" class="sop-notes">
        <div class="notes-title">操作规范与安全要求</div>
        <div v-for="(note, index) in sopNotes" :key="index" class="note-item">
          <span class="note-label">{{ note.title }}</span>
          <span class="note-content">{{ note.content }}</span>
        </div>
      </div>
    </div>
    <div v-else class="empty-state">
      <div class="radar-scan"></div>
      <p>等待 AI 生成标准化排障步骤...</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useChatStore } from '../stores/chat'
import { Check } from '@element-plus/icons-vue'

const store = useChatStore()
const props = defineProps<{ activeStep: number }>()
const emit = defineEmits<{ (e: 'update:activeStep', v: number): void; (e: 'all-completed'): void }>()
const dynamicSteps = ref<any[]>([]);
const sopNotes = ref<any[]>([]);
const sopMeta = ref('根据 AI 分析结果实时生成');

watch(() => store.messages, (msgs) => {
  const last = [...msgs].reverse().find(m => m.role === 'assistant' && m.status === 'done')
  const currentSop = last?.current_sop;
  const steps = currentSop?.steps?.length ? currentSop.steps : last?.sop_steps;
  if (steps?.length) {
    dynamicSteps.value = steps.map((s: any, index: number) => ({
      ...s,
      title: s.step_title || s.title || `检修步骤 ${index + 1}`,
      desc: s.desc || s.description || '',
      options: ['✅ 正常', '⚠️ 已修复', '🔧 已更换'],
      selectedOption: s.selectedOption || ''
    }))
    sopNotes.value = (currentSop?.notes || []).map((n: any) => ({
      title: n.title || '注意事项',
      content: n.content || ''
    })).filter((n: any) => n.content)
    // 显示分类状态：追问补充 vs 新故障
    const classification = currentSop?.classification
    const isMerge = classification?.decision === 'same'
    const decisionLabel = isMerge ? '🔄 追问补充' : '✨ 新故障诊断'
    const sopId = currentSop?.sop_id ? ` · ${currentSop.sop_id.slice(0, 8)}` : ''
    sopMeta.value = `${decisionLabel} · v${currentSop.version}${sopId} · ${formatTime(currentSop.updated_at || currentSop.created_at)}`
    emit('update:activeStep', 0)
  } else if (!last) {
    dynamicSteps.value = []
    sopNotes.value = []
    sopMeta.value = '根据 AI 分析结果实时生成'
  }
}, { deep: true, immediate: true })

const formatTime = (value?: string) => {
  if (!value) return '刚刚更新'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleString('zh-CN')
}

const nextStep = () => {
  const n = props.activeStep + 1
  emit('update:activeStep', n)
  if (n >= dynamicSteps.value.length) emit('all-completed')
}
</script>

<style scoped>
.sop-flow{flex:1;display:flex;flex-direction:column;overflow:hidden;min-height:0}
.sop-header{margin-bottom:24px;border-bottom:1px solid var(--border-glass);padding-bottom:12px;flex-shrink:0}
.sop-header h4{margin:0;color:var(--text-primary);font-weight:600}
.sub-title{font-size:12px;color:var(--text-muted);margin-top:6px}
.text-accent{color:var(--primary-light)}
.text-green{color:var(--success);font-weight:bold}
.steps-wrapper{flex:1;overflow-y:auto;padding-right:8px;min-height:0}
:deep(.el-step__title){font-size:14px!important;font-weight:600}
:deep(.el-step__title.is-process){color:var(--accent-blue)!important}
:deep(.el-step__title.is-wait){color:var(--text-muted)!important}
:deep(.el-step__title.is-success){color:var(--success)!important}
.step-desc-content{margin-top:8px;margin-bottom:16px}
.ai-instruction{font-size:13px;line-height:1.6;color:var(--text-primary);background:var(--bg-soft);padding:10px 12px;border-radius:6px;border-left:2px solid var(--primary-color)}
.step-action-zone{margin-top:12px;background:var(--bg-soft);padding:12px;border-radius:8px;border:1px dashed var(--border-light)}
.cyber-radio-group{display:flex;flex-direction:column;gap:8px;margin-bottom:12px}
:deep(.el-radio){color:var(--text-secondary);margin-right:0;display:flex;align-items:center}
:deep(.el-radio .el-radio__label){padding-left:6px;font-size:13px}
.next-action-btn{width:100%;border-radius:6px;background:var(--theme-gradient);border:none}
.completed-badge{display:flex;align-items:center;gap:6px;margin-top:10px;font-size:12px;color:var(--success);background:color-mix(in srgb, var(--success) 12%, transparent);padding:6px 10px;border-radius:4px}
.sop-notes{margin-top:14px;padding:12px;border:1px solid var(--border-glass);border-radius:8px;background:var(--bg-soft)}
.notes-title{font-size:13px;font-weight:700;color:var(--text-primary);margin-bottom:8px}
.note-item{display:flex;flex-direction:column;gap:4px;font-size:12px;color:var(--text-secondary);padding:8px 0;border-top:1px solid var(--border-glass)}
.note-item:first-of-type{border-top:none}
.note-label{color:var(--warning);font-weight:600}
.note-content{line-height:1.6;color:var(--text-secondary)}
.empty-state{display:flex;flex-direction:column;align-items:center;justify-content:center;height:60%;color:var(--text-muted);text-align:center;font-size:13px}
.radar-scan{width:60px;height:60px;border-radius:50%;border:1px solid var(--border-light);position:relative;margin-bottom:20px;overflow:hidden}
.radar-scan::before{content:'';position:absolute;top:50%;left:50%;width:50%;height:50%;background:conic-gradient(from 0deg,transparent 70%,var(--primary-color) 100%);transform-origin:0 0;animation:scan 2s linear infinite}
@keyframes scan{0%{transform:rotate(0deg)}100%{transform:rotate(360deg)}}
</style>
