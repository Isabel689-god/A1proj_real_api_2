<template>
  <div class="sop-flow">
    <div class="sop-header">
      <h4>📋 标准检修作业指引 (<span class="text-accent">SOP</span>)</h4>
      <p class="sub-title">{{ sopMeta }}</p>
    </div>
    <div class="steps-wrapper" v-if="dynamicSteps.length > 0">
      <el-steps direction="vertical" :active="currentStepIndex" finish-status="success">
        <el-step
          v-for="(step, index) in dynamicSteps"
          :key="index"
          :title="step.title"
          :status="step.statusClass"
        >
          <template #description>
            <div class="step-desc-content">
              <div class="ai-instruction">{{ step.desc }}</div>
              <el-button size="small" type="primary" link @click="showDemo(step)" style="margin-top:4px;">🎬 演示动画</el-button>
              <div class="step-status-line">
                <el-tag v-if="step._status === 'done'" type="success" size="small" effect="dark">✅ 已完成</el-tag>
                <el-tag v-else-if="step._status === 'in_progress'" type="warning" size="small" effect="dark">🔄 Agent判定:进行中</el-tag>
                <el-tag v-else type="info" size="small" effect="plain">⬜ 待执行</el-tag>
                <span v-if="step._note" class="step-note">— {{ step._note }}</span>
              </div>
            </div>
          </template>
        </el-step>
        <el-step title="检修完成" v-if="allDone" status="success">
          <template #description><p class="text-green">Agent 判定：全部步骤已完成。</p></template>
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
      <p>等待 Agent 生成标准化排障步骤...</p>
    </div>
    <!-- 动画演示弹窗 -->
    <el-dialog v-model="demoVisible" :title="demoTitle" width="95%" top="2vh" destroy-on-close>
      <div v-if="demoLoading" style="text-align:center;padding:60px;color:var(--text-muted);">🎬 正在生成动画...</div>
      <iframe v-else :srcdoc="demoHtml" style="width:100%;height:70vh;border:none;border-radius:8px;" />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useChatStore } from '../stores/chat'

const store = useChatStore()
const emit = defineEmits<{ (e: 'all-done', v: boolean): void }>()

const lastAssistantMsg = computed(() => {
  // 触发 sopTick 强制重新计算
  void store.sopTick
  const msgs = store.messages
  return [...msgs].reverse().find((m: any) => m.role === 'assistant')
})

const currentSop = computed(() => lastAssistantMsg.value?.current_sop)

const dynamicSteps = computed(() => {
  const sop = currentSop.value
  const steps = sop?.steps?.length ? sop.steps : lastAssistantMsg.value?.sop_steps
  console.log('SopFlow computed:', steps?.length, steps?.map((s:any) => s.step_status || s.status || '?'))
  if (!steps?.length) return []
  return steps.map((s: any) => {
    const status = s.step_status || s.status || 'pending'
    return {
      title: s.step_title || s.title || '',
      desc: s.desc || s.description || '',
      _status: status,
      _note: s.step_note || s.note || '',
      statusClass: status === 'done' ? 'success' : status === 'in_progress' ? 'process' : 'wait',
    }
  })
})

const sopNotes = computed(() => {
  return (currentSop.value?.notes || []).map((n: any) => ({
    title: n.title || '注意事项',
    content: n.content || ''
  })).filter((n: any) => n.content)
})

const sopMeta = computed(() => {
  const sop = currentSop.value
  if (!sop) return 'Agent 实时生成 · 状态由 Agent 自动同步'
  const classification = sop.classification
  const isMerge = classification?.decision === 'same'
  const decisionLabel = isMerge ? '🔄 追问补充' : '✨ 新故障诊断'
  const sopId = sop.sop_id ? ` · ${sop.sop_id.slice(0, 8)}` : ''
  const t = sop.updated_at || sop.created_at
  const timeStr = t ? new Date(t).toLocaleString('zh-CN') : '刚刚更新'
  return `${decisionLabel} · v${sop.version}${sopId} · ${timeStr}`
})

const allDone = computed(() => currentSop.value?.all_done || false)
const currentStepIndex = computed(() => (currentSop.value?.current_step || 1) - 1)

// 监听 allDone 变化，emit 给父组件
import { watch } from 'vue'
watch(allDone, (v) => emit('all-done', v))

const formatTime = (value?: string) => {
  if (!value) return '刚刚更新'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleString('zh-CN')
}

const API_BASE = import.meta.env.VITE_API_BASE ?? ''
const demoVisible = ref(false)
const demoLoading = ref(false)
const demoHtml = ref('')
const demoTitle = ref('')

const showDemo = async (step: any) => {
  demoTitle.value = `🎬 ${step.title || step.step_title}`
  demoVisible.value = true
  if (step._animHtml) { demoHtml.value = step._animHtml; return }
  demoLoading.value = true
  try {
    const res = await fetch(`${API_BASE}/animation/generate`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ step_desc: step.desc, step_title: step.title })
    })
    const data = await res.json()
    step._animHtml = data.html
    demoHtml.value = data.html
  } catch { demoVisible.value = false } finally { demoLoading.value = false }
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
.step-status-line{margin-top:8px;display:flex;align-items:center;gap:6px;font-size:12px}
.step-note{color:var(--text-muted);font-size:12px}
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
