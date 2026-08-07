<template>
  <div class="repair-report cyber-card-3d">
    <div class="card-header">
      <div class="header-icon"></div>
      <h4>检修业务标准化闭环报告</h4>
    </div>
    <div class="card-body">
      <div class="info-row">
        <span class="label">作业单号:</span>
        <span class="value text-cyan">{{ orderId }}</span>
      </div>
      <div class="info-row">
        <span class="label">派单时间:</span>
        <span class="value">{{ dispatchTime }}</span>
      </div>
      <div class="info-row">
        <span class="label">标准合规校验:</span>
        <div class="status-badge" :class="{ 'is-done': submitted || isEnabled }">
          <span class="pulse-dot"></span>
          {{ submitted || isEnabled ? '符合提交流程' : '待完成全部步骤' }}
        </div>
      </div>
    </div>
    <div class="card-footer">
      <el-button
        v-if="submitted"
        type="success"
        size="default"
        class="cyber-submit-btn"
        disabled
      >
        已提交
      </el-button>
      <el-button
        v-else
        :type="isEnabled ? 'primary' : 'info'"
        size="default"
        class="cyber-submit-btn"
        :class="{ 'neon-glow': isEnabled }"
        :loading="submitting"
        :disabled="!isEnabled"
        @click="handleArchiveOrder"
      >
        {{ isEnabled ? '提报经验并归档结单' : '需先完成SOP全流程' }}
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';

const props = defineProps<{
  isEnabled: boolean;
  orderId: string;
  dispatchTime: string;
}>();

const emit = defineEmits<{
  (e: 'report-submitted'): void;
}>();

const submitting = ref(false);
const submitted = ref(false);

const API_BASE = import.meta.env.VITE_API_BASE || '';

// 从后端加载提交状态
watch(() => props.orderId, async (id) => {
  if (!id) { submitted.value = false; return; }
  // 从 MySQL 加载提交状态
  try {
    const res = await fetch(`${API_BASE}/maintenance/records?page_size=1&user_id=&check_order=${encodeURIComponent(id)}`);
    const checkId = async (oid: string) => {
      // 查询该 orderId 是否有已提交的记录
      const r = await fetch(`${API_BASE}/maintenance/records/check-submitted/${encodeURIComponent(oid)}`);
      if (r.ok) { const d = await r.json(); submitted.value = d.submitted; }
    };
    await checkId(id);
  } catch { /* */ }
}, { immediate: true });

const handleArchiveOrder = () => {
  ElMessageBox.confirm(
    '确定完成本次设备检修，并将故障分析经验提报至知识库归档吗？',
    '归档结单确认',
    {
      confirmButtonText: '确定归档',
      cancelButtonText: '取消',
      type: 'warning',
    }
  ).then(() => {
    submitted.value = true;
    // 保存到 MySQL：创建/更新一条维修记录，标记已提交
    fetch(`${API_BASE}/maintenance/records/submit-report`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        report_order_id: props.orderId || '',
        report_submitted: true,
      }),
    }).catch(() => {});
    submitting.value = true;
    setTimeout(() => {
      submitting.value = false;
      ElMessage({
        type: 'success',
        message: '已提报',
        duration: 1500
      });
      emit('report-submitted');
    }, 1200);
  }).catch(() => {
    ElMessage({ type: 'info', message: '已取消归档操作' });
  });
};
</script>

<style scoped>
.cyber-card-3d {
  position: relative;
  background: var(--bg-card);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid var(--border-glass);
  border-radius: 14px;
  padding: 24px;
  margin-bottom: 16px;
  overflow: hidden;
  box-shadow: var(--shadow-glass);
  transition: transform 0.3s ease, box-shadow 0.3s ease, background 0.35s ease, border-color 0.35s ease;
}
.cyber-card-3d:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-neon);
  border-color: var(--border-light);
}
.cyber-card-3d::after {
  content: '';
  position: absolute;
  top: 0; left: 0; width: 100%; height: 100%;
  background: linear-gradient(135deg, var(--border-glass), transparent);
  animation: smoothShimmer 6s ease-in-out infinite alternate;
  pointer-events: none;
}
.card-header {
  display: flex; align-items: center; gap: 10px;
  border-bottom: 1px solid var(--border-glass);
  padding-bottom: 12px; margin-bottom: 16px;
}
.card-header .header-icon {
  background: var(--primary-light);
  box-shadow: 0 0 10px var(--primary-color);
}
.header-icon {
  width: 10px; height: 10px; background: var(--primary-light);
  box-shadow: 0 0 8px var(--primary-light); transform: rotate(45deg);
}
.card-header h4 {
  margin: 0; color: var(--text-primary); font-size: 15px; font-weight: 600; letter-spacing: 1px;
}
.card-body {
  display: flex; flex-direction: column; gap: 12px; margin-bottom: 20px;
}
.info-row {
  display: flex; justify-content: space-between; align-items: center;
  background: var(--bg-glass);
  padding: 10px 12px; border-radius: 6px;
  border: 1px solid var(--border-glass);
}
.label { color: var(--text-secondary); font-size: 13px; }
.value { color: var(--text-primary); font-size: 13px; font-weight: bold; font-family: 'Cascadia Code', 'Fira Code', 'JetBrains Mono', ui-monospace, Consolas, monospace; }
.text-cyan { color: var(--accent-blue); text-shadow: 0 0 8px var(--accent-blue); }

.status-badge {
  display: flex; align-items: center; gap: 6px;
  background: var(--success);
  border: 1px solid var(--success); color: var(--text-inverse);
  padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: bold;
  opacity: 0.85;
}
.pulse-dot {
  width: 8px; height: 8px; background: var(--text-inverse); border-radius: 50%;
  animation: pulse 1.5s infinite;
}
.card-footer { text-align: right; }
.neon-glow {
  background: var(--primary-color) !important;
  border: 1px solid var(--primary-color) !important;
  color: var(--text-inverse) !important;
  box-shadow: 0 0 15px var(--primary-color);
}

@keyframes pulse {
  0% { transform: scale(0.9); opacity: 0.8; }
  50% { transform: scale(1.2); opacity: 1; }
  100% { transform: scale(0.9); opacity: 0.8; }
}
@keyframes smoothShimmer {
  0% { opacity: 0.5; transform: scale(0.98); }
  100% { opacity: 1; transform: scale(1.02); }
}
</style>
