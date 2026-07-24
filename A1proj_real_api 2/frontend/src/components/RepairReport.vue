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
        <div class="status-badge">
          <span class="pulse-dot"></span>
          {{ isEnabled ? '符合提交流程' : '待完成全部步骤' }}
        </div>
      </div>
    </div>
    <div class="card-footer">
      <el-button
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
import { ref } from 'vue';
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
    submitting.value = true;
    setTimeout(() => {
      submitting.value = false;
      ElMessage({
        type: 'success',
        message: '工单已成功提报！故障经验已同步至系统知识库。',
        duration: 3000
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
  /* 深蓝渐变基底 */
  background: linear-gradient(145deg, rgba(12, 19, 38, 0.8) 0%, rgba(8, 12, 24, 0.6) 100%);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(131, 165, 221, 0.15); /* 低透明度淡蓝细描边 */
  border-radius: 14px;
  padding: 24px;
  margin-bottom: 16px;
  overflow: hidden;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.5);
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}
.cyber-card-3d:hover {
  transform: translateY(-2px);
  box-shadow:
    0 16px 45px rgba(0, 0, 0, 0.6),
    0 0 30px rgba(92, 85, 140, 0.25); /* 柔和蓝紫环境光 */
  border-color: rgba(131, 165, 221, 0.3);
}
.cyber-card-3d::after {
  content: '';
  position: absolute;
  top: 0; left: 0; width: 100%; height: 100%;
  /* 从左上角到右下角的微弱柔光慢流动感 */
  background: linear-gradient(135deg, rgba(107, 137, 196, 0.05) 0%, rgba(92, 85, 140, 0.08) 50%, transparent 100%);
  animation: smoothShimmer 6s ease-in-out infinite alternate;
  pointer-events: none;
}
.card-header {
  display: flex; align-items: center; gap: 10px;
  border-bottom: 1px solid var(--border-glass); /* 细描边 */
  padding-bottom: 12px; margin-bottom: 16px;
}
.card-header .header-icon {
  background: var(--primary-light);
  box-shadow: 0 0 10px rgba(107, 137, 196, 0.4); /* 剔除刺眼青光 */
}
.header-icon {
  width: 10px; height: 10px; background: var(--primary-light);
  box-shadow: 0 0 8px var(--primary-light); transform: rotate(45deg);
}
.card-header h4 {
  margin: 0; color: #f8fafc; font-size: 15px; font-weight: 600; letter-spacing: 1px;
}
.card-body {
  display: flex; flex-direction: column; gap: 12px; margin-bottom: 20px;
}
.info-row {
  display: flex; justify-content: space-between; align-items: center;
  background: rgba(15, 23, 42, 0.5);
  padding: 10px 12px; border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.05);
}
.label { color: #94a3b8; font-size: 13px; }
.value { color: #f1f5f9; font-size: 13px; font-weight: bold; font-family: 'Cascadia Code', 'Fira Code', 'JetBrains Mono', ui-monospace, Consolas, monospace; }
.text-cyan { color: #22d3ee; text-shadow: 0 0 8px rgba(34, 211, 238, 0.5); }

.status-badge {
  display: flex; align-items: center; gap: 6px;
  background: rgba(16, 185, 129, 0.15);
  border: 1px solid #10b981; color: #34d399;
  padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: bold;
}
.pulse-dot {
  width: 8px; height: 8px; background: #10b981; border-radius: 50%;
  box-shadow: 0 0 8px #10b981; animation: pulse 1.5s infinite;
}
.card-footer { text-align: right; }
.cyber-submit-btn { width: 100%; border-radius: 8px; font-weight: bold; letter-spacing: 1px; }
.neon-glow {
  background: linear-gradient(90deg, #3a5078, #5b7bb2) !important;
  border: 1px solid rgba(131, 165, 221, 0.3) !important;
  color: #fff !important;
  box-shadow: 0 0 15px rgba(92, 85, 140, 0.3); /* 蓝紫光晕 */
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