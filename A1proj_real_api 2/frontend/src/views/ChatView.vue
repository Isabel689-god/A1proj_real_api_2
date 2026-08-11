<template>
  <div class="chat-view-container">
    <div class="system-header">
      <div class="header-title">
        <el-button v-if="viewingHistory" @click="exitHistoryView" size="small" text style="margin-right:10px;">← 返回</el-button>
        智能设备多模态检修控制台
      </div>
      <div class="header-right-actions" style="display: flex; align-items: center; gap: 16px;">
        <el-button type="primary" link class="user-center-btn" @click="showUserCenter = true">
          👤 个人空间 ({{ store.group }})
        </el-button>
      </div>
    </div>

    <div class="chat-body-layout">
      <ChatSidebar />
      <div class="chat-main-area">
        <ChatMessageList @suggestion-click="handleSuggestionClick" />
        <ChatComposer v-if="!viewingHistory && !reportLocked" />
      </div>

      <div class="chat-right-panel" :class="{ collapsed: rightCollapsed }">
        <button class="right-collapse-toggle" @click="rightCollapsed = !rightCollapsed" :title="rightCollapsed ? '展开右侧面板' : '收起右侧面板'">
          {{ rightCollapsed ? '◀' : '▶' }}
        </button>
        <RightPanel
          v-if="!rightCollapsed"
          :sessionId="store.activeSessionId"
          :messages="store.messages"
          :deviceModel="store.selectedDeviceModel"
          @report-submitted="handleReportSubmitted"
        />
      </div>
    </div>

    <el-drawer
      v-model="showUserCenter"
      direction="rtl"
      size="520px"
      class="dark-drawer"
      :with-header="false"
      append-to-body
    >
      <div class="drawer-inner">
        <div class="profile-card glass-card">
          <div class="profile-left">
            <el-avatar :size="56" class="profile-avatar">
              {{ store.username.substring(0, 2).toUpperCase() }}
            </el-avatar>
            <div class="profile-meta">
              <h3 class="username">{{ store.username }}</h3>
              <el-tag size="small" type="success" effect="dark" class="role-tag">
                {{ store.group }}
              </el-tag>
            </div>
          </div>
          <el-button type="danger" plain size="small" class="logout-btn" @click="handleLogout">
            退出登录
          </el-button>
        </div>

        <div v-if="store.hasPermission('audit_uploads') || store.hasPermission('view_intern_logs')" class="section-block">
          <div class="section-title">
            <span class="title-icon">🛡️</span>
            <span>高级职工专属管理</span>
          </div>
          <div class="action-grid">
            <el-button v-if="store.hasPermission('audit_uploads')" type="warning" plain class="action-btn">
              待审普通员工手册
              <span class="badge">0</span>
            </el-button>
            <el-button v-if="store.hasPermission('direct_upload')" type="success" plain class="action-btn">
              直传设备手册
            </el-button>
          </div>
        </div>

        <div v-if="store.hasPermission('request_upload') && !store.hasPermission('direct_upload')" class="section-block">
          <div class="section-title">
            <span class="title-icon">📝</span>
            <span>手册更新业务</span>
          </div>
          <el-button type="primary" plain class="full-width-btn">
            发起新手册录入申请 (待高级职工审核)
          </el-button>
        </div>

        <div v-if="store.hasPermission('submit_report')" class="section-block history-section">
          <div class="section-title">
            <span class="title-icon">📋</span>
            <span>我的维修记录</span>
            <el-button size="small" type="success" plain style="margin-left:8px;" @click="syncAllToCloud">☁️ 同步到云端</el-button>
            <el-button size="small" type="primary" link style="margin-left:auto;" @click="showMaintenanceDrawer = true">🔧 维修总结</el-button>
          </div>
          <el-empty v-if="historyReports.length === 0" description="暂无提报数据" :image-size="80" class="dark-empty" />
          <el-table v-else :data="historyReports" size="small" class="three-line-table" style="width:100%">
            <el-table-column prop="orderId" label="编号" width="160" show-overflow-tooltip />
            <el-table-column prop="dispatchTime" label="开始时间" width="140" />
            <el-table-column prop="submitTime" label="结束时间" width="140" />
            <el-table-column label="轮数" width="60" align="center">
              <template #default="{ row }">
                {{ row.messages?.length || 0 }}
              </template>
            </el-table-column>
            <el-table-column label="状态" width="80" align="center">
              <template #default="{ row }">
                <el-tag size="small" :type="row.maintenanceAdded ? 'success' : 'info'">{{ row.maintenanceAdded ? '已加入' : '未加入' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="280" align="right">
              <template #default="{ row }">
                <el-button size="small" type="primary" link @click="viewHistoryChat(row)">查看</el-button>
                <el-button size="small" type="warning" plain @click="saveToMaintenance(row)">📝 加入维修总结</el-button>
                <el-popconfirm title="确定删除该记录吗？" @confirm="deleteReport(row)">
                  <template #reference>
                    <el-button size="small" type="danger" link>删除</el-button>
                  </template>
                </el-popconfirm>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <template v-else>
          <el-empty description="实习账号不开放工单提报与审查权限" :image-size="100" class="dark-empty" />
        </template>
      </div>
    </el-drawer>

    <MaintenanceRecordDrawer v-model="showMaintenanceDrawer" />

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { useChatStore } from '../stores/chat';
import { renderMarkdown } from '../utils/chatMarkdown';
import ChatSidebar from '../components/ChatSidebar.vue';
import ChatMessageList from '../components/ChatMessageList.vue';
import ChatComposer from '../components/ChatComposer.vue';
import RightPanel from '../components/RightPanel.vue';
import MaintenanceRecordDrawer from '../components/MaintenanceRecordDrawer.vue';

const router = useRouter();
const store = useChatStore();

const handleSuggestionClick = (text: string) => {
  store.sendMessage(text);
};
const showUserCenter = ref(false);
watch(showUserCenter, (v) => { if (v) loadMaintenanceStatus(); });
// 切换会话时根据是否已提交维修记录决定锁定状态
watch(() => store.activeSessionId, (newId) => {
  const hasReport = store.globalReports.some((r: any) => r.orderId === newId);
  reportLocked.value = hasReport;
});
const rightCollapsed = ref(false);
const historyReports = computed(() => store.globalReports);
const viewingHistory = ref(false);
const showMaintenanceDrawer = ref(false);
const reportLocked = ref(false);
const _prevSessionId = ref('');
const _prevMessages = ref<any[]>([]);
const _prevRightCollapsed = ref(false);
const _prevLockedSOP = ref<any>(null);
const _prevReportLocked = ref(false);
const apiBase3 = import.meta.env.VITE_API_BASE || '';

// 从数据库加载哪些工单已加入维修记录 + 已提交
const syncAllToCloud = async () => {
  if (!store.globalReports.length) { ElMessage.info('没有可同步的记录'); return; }
  let count = 0;
  for (const rep of store.globalReports) {
    try {
      await fetch(`${apiBase3}/maintenance/reports/sync?user_id=${encodeURIComponent(store.username)}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(rep),
      });
      count++;
    } catch {}
  }
  ElMessage.success(`已同步 ${count} 条记录到云端`);
};

const loadMaintenanceStatus = async () => {
  // 从 MySQL 加载缺失的报告
  try {
    const repRes = await fetch(`${apiBase3}/maintenance/reports/sync?user_id=${encodeURIComponent(store.username)}`);
    if (repRes.ok) {
      const repData = await repRes.json();
      const existingIds = new Set(store.globalReports.map((r: any) => r.orderId));
      for (const rep of (repData.reports || [])) {
        if (rep.orderId && !existingIds.has(rep.orderId)) {
          store.globalReports.push(rep);
        }
      }
      localStorage.setItem('INDUSTRIAL_GLOBAL_REPORTS', JSON.stringify(store.globalReports));
    }
  } catch {}

  // 自动同步：把 MySQL 中没有的报告上传
  try {
    const repRes = await fetch(`${apiBase3}/maintenance/reports/sync?user_id=${encodeURIComponent(store.username)}`);
    if (repRes.ok) {
      const remoteIds = new Set(((await repRes.json()).reports || []).map((r: any) => r.orderId));
      for (const rep of store.globalReports) {
        if (rep.orderId && !remoteIds.has(rep.orderId)) {
          await fetch(`${apiBase3}/maintenance/reports/sync?user_id=${encodeURIComponent(store.username)}`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(rep),
          });
        }
      }
    }
  } catch {}

  // 检查 maintenanceAdded 标记
  try {
    const res = await fetch(`${apiBase3}/maintenance/records?user_id=${encodeURIComponent(store.username)}&page_size=500`);
    if (res.ok) {
      const data = await res.json();
      const addedIds = new Set((data.records || [])
        .filter((r: any) => r.report_order_id && (r.description || r.fault_type))
        .map((r: any) => r.report_order_id));
      for (const item of store.globalReports) {
        if (!item.maintenanceAdded && addedIds.has(item.orderId)) item.maintenanceAdded = true;
      }
      localStorage.setItem('INDUSTRIAL_GLOBAL_REPORTS', JSON.stringify(store.globalReports));
    }
  } catch { /* */ }
};

const deleteReport = (item: any) => {
  const idx = store.globalReports.findIndex((r: any) => r.orderId === item.orderId);
  if (idx >= 0) {
    store.globalReports.splice(idx, 1);
    localStorage.setItem('INDUSTRIAL_GLOBAL_REPORTS', JSON.stringify(store.globalReports));
  }
  ElMessage.success('已删除');
};

const saveToMaintenance = async (item: any) => {
  const msgs = item.messages || [];
  // 合并所有 assistant 消息，查找完整诊断格式
  const fullText = msgs.filter((m: any) => m.role === 'assistant').map((m: any) => m.content || '').join('\n');
  const firstMsg = msgs[0]?.content || '';

  // 按 SOP 章节分割（兼容 ## 前缀）
  const sec1 = fullText.match(/#*\s*一、故障诊断[\s\S]*?(?=#*\s*二、原因分析|$)/)?.[0] || '';
  const sec2 = fullText.match(/#*\s*二、原因分析[\s\S]*?(?=#*\s*三、解决方案|$)/)?.[0] || '';
  const sec3 = fullText.match(/#*\s*三、解决方案[\s\S]*?(?=##\s|【标准作业指引】|#*\s*四、|$)/)?.[0] || '';

  // 设备型号：匹配各种格式（设备型号 / **设备型号** 等）
  const dm = sec1.match(/\*{0,2}设备型号\*{0,2}[：:]\s*(.+)/) || fullText.match(/\*{0,2}设备型号\*{0,2}[：:]\s*(.+)/);
  const device = dm ? dm[1].trim().replace(/[#*]/g, '').slice(0, 50) : (firstMsg.slice(0, 30) || '未指定');

  // 故障类型：匹配 报警/故障码/报警名称 等
  const alarm = sec1.match(/\*{0,2}(?:报警|报警名称|报警码|故障码)\*{0,2}[：:]\s*(.+)/);
  const fault = alarm ? alarm[1].trim().replace(/[#*]/g, '').slice(0, 50) : (firstMsg.slice(0, 30) || '未知故障');

  // 故障描述：匹配 现象/故障现象
  const phen = sec1.match(/\*{0,2}(?:现象|故障现象)\*{0,2}[：:]\s*([\s\S]+?)(?=\n\*{0,2}(?:报警|设备|原因|方案|步骤|判断|\n)|\n\n|\n##|$)/);
  const desc = phen ? phen[1].trim().replace(/[#*]/g, '').slice(0, 500) : firstMsg.slice(0, 200);

  // 故障原因：二、原因分析 的正文
  const cause = sec2.replace(/##?\s*二、原因分析\s*/g, '').trim().replace(/[#*]/g, '').slice(0, 500);

  // 维修方案：三、解决方案 的正文
  const solution = sec3.replace(/##?\s*三、解决方案\s*/g, '').trim().replace(/[#*]/g, '').slice(0, 500);

  // 时间计算 — 将派单/提报时间转为 ISO 格式
  const toISO = (t: string) => {
    if (!t) return '';
    try {
      const d = new Date(t);
      if (isNaN(d.getTime())) return '';
      // 格式化为 YYYY-MM-DDTHH:mm:ss
      const pad = (n: number) => String(n).padStart(2, '0');
      return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
    } catch { return ''; }
  };
  const startTime = toISO(item.dispatchTime);
  const endTime = toISO(item.submitTime);
  let duration = '';
  if (startTime && endTime) {
    const start = new Date(startTime);
    const end = new Date(endTime);
    const diffMs = end.getTime() - start.getTime();
    if (diffMs > 0) {
      const mins = Math.round(diffMs / 60000);
      const hours = mins / 60;
      if (hours >= 24) {
        duration = `${(hours / 24).toFixed(1)}天`;
      } else if (hours >= 1) {
        duration = `${hours.toFixed(1)}小时`;
      } else if (mins >= 1) {
        duration = `${mins}分钟`;
      } else {
        duration = '不足1分钟';
      }
    }
  }

  try {
    const res = await fetch(`${apiBase3}/maintenance/records?user_id=${encodeURIComponent(store.username)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        device_model: device || '未指定',
        fault_type: fault,
        repair_date: '',
        technician: store.username || '',
        description: desc || '',
        solution: solution || '',
        parts_replaced: '',
        status: '已完成',
        repair_start_time: startTime,
        repair_end_time: endTime,
        repair_duration: duration,
        fault_cause: cause || '',
        fault_resolved: '是',
        report_order_id: item.orderId || '',
      }),
    });
    if (res.ok) {
      item.maintenanceAdded = true;
      localStorage.setItem('INDUSTRIAL_GLOBAL_REPORTS', JSON.stringify(store.globalReports));
      ElMessage.success('已加入维修记录总结');
    }
    else { const d = await res.json(); ElMessage.error(d.detail || '保存失败'); }
  } catch (e: any) { ElMessage.error('保存失败: ' + (e?.message || '')); }
};

const roleNameMap: Record<string, string> = {
  admin: '管理中枢',
  senior: '高级职工',
  employee: '普通员工',
  intern: '访客'
};

const handleReportSubmitted = (report: any) => {
  store.submitReport(report);
  reportLocked.value = true;
  ElMessage.success('报告已提交归档');
};

const viewHistoryChat = (item: any) => {
  const msgs = item.messages || [];
  if (!msgs.length) {
    ElMessage.info('该记录无对话内容');
    return;
  }
  // 保存当前会话状态
  _prevSessionId.value = store.activeSessionId || '';
  _prevRightCollapsed.value = rightCollapsed.value;
  _prevLockedSOP.value = store.lockedSOP ? JSON.parse(JSON.stringify(store.lockedSOP)) : null;
  _prevReportLocked.value = reportLocked.value;
  reportLocked.value = false;
  if (store.activeSession) {
    _prevMessages.value = [...(store.activeSession.messages || [])];
  }
  // 创建临时历史会话
  const historyId = '__history_view__';
  // 从历史消息中提取 SOP（后端 _attach_latest_sop 挂在最后一条 assistant 消息上）
  let historySOP: any = null;
  const historyMessages = msgs.map((m: any, i: number) => {
    const msg: any = {
      id: `hist_${i}`,
      role: m.role || 'user',
      content: m.content || '',
      timestamp: Date.now(),
    };
    if (m.current_sop) {
      historySOP = m.current_sop;
      msg.current_sop = m.current_sop;
      msg.sop_steps = m.sop_steps || m.current_sop.steps;
    }
    return msg;
  });
  const historySession = {
    id: historyId,
    title: item.orderId || '历史对话',
    messages: historyMessages,
    updatedAt: Date.now(),
  };
  store.sessions = [historySession, ...store.sessions];
  store.activeSessionId = historyId;
  store.lockedSOP = historySOP ? JSON.parse(JSON.stringify(historySOP)) : null;
  store.sopTick++;
  viewingHistory.value = true;
  rightCollapsed.value = true;
};

const exitHistoryView = () => {
  viewingHistory.value = false;
  rightCollapsed.value = _prevRightCollapsed.value;
  store.lockedSOP = _prevLockedSOP.value ? JSON.parse(JSON.stringify(_prevLockedSOP.value)) : null;
  store.sopTick++;
  reportLocked.value = _prevReportLocked.value;
  // 删除临时会话
  store.sessions = store.sessions.filter((s: any) => s.id !== '__history_view__');
  // 恢复原会话
  if (_prevSessionId.value) {
    store.activeSessionId = _prevSessionId.value;
    const prev = store.sessions.find((s: any) => s.id === _prevSessionId.value);
    if (prev) prev.messages = _prevMessages.value;
  }
};

const loadInternLogs = () => {
   ElMessage.info('正在拉取实习组最近7天问答数据...');
};

const handleLogout = () => {
  store.logout();
  showUserCenter.value = false;
  ElMessage.success('已安全退出当前操作终端');
  router.push('/login');
};

onMounted(() => {
  store.init();
  loadMaintenanceStatus();
});
</script>

<style scoped>
.chat-view-container {
  display: flex;
  flex-direction: column;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  font-family: 'PingFang SC', 'Microsoft YaHei', 'Noto Sans SC', system-ui, sans-serif;
  background: var(--bg-darker, #020617);
}

.system-header {
  height: 52px;
  background: linear-gradient(90deg, var(--bg-dark), var(--bg-darker), var(--bg-dark));
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 24px;
  border-bottom: 1px solid var(--border-glass);
  flex-shrink: 0;
}

.header-title {
  color: var(--text-primary);
  font-weight: 600;
  font-size: 15px;
  letter-spacing: 1px;
  display: flex;
  align-items: center;
  gap: 10px;
}
.header-title::before {
  content: '';
  width: 8px; height: 8px;
  border-radius: 50%;
  background: var(--primary-color);
}

/* 顶栏按钮 */
.graph-btn, .neo4j-btn {
  font-size: 14px;
}

.user-center-btn {
  font-size: 14px;
}

.chat-body-layout {
  flex: 1;
  display: flex;
  overflow: hidden;
  min-height: 0;
}

.chat-main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: var(--bg-darker, #020617);
  border-right: 1px solid var(--border-glass);
  min-width: 0;
}

.chat-right-panel {
  width: 360px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: width 0.3s ease;
  position: relative;
}
.chat-right-panel.collapsed {
  width: 40px;
}

.right-collapse-toggle {
  position: absolute;
  top: 10px;
  left: 8px;
  z-index: 10;
  width: 24px;
  height: 24px;
  border: 1px solid var(--border-glass);
  border-radius: 4px;
  background: var(--bg-glass);
  color: var(--text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  transition: all 0.2s;
}
.right-collapse-toggle:hover {
  border-color: var(--primary-color);
  color: var(--primary-color);
}

/* ========== 抽屉深色背景 + 彻底清除白边 ========== */
:deep(.dark-drawer.el-drawer) {
  background: var(--bg-dark) !important;
  border: none !important;
  box-shadow: none !important;
  outline: none !important;
  border-left: 1px solid var(--border-glass) !important;
}

:deep(.dark-drawer .el-drawer__body) {
  background: var(--bg-dark) !important;
  padding: 0 !important;
  margin: 0 !important;
  border: none !important;
}

:deep(.dark-drawer .el-drawer__header) {
  background: var(--bg-dark) !important;
  color: var(--text-primary) !important;
  border-bottom: 1px solid var(--border-glass) !important;
  margin-bottom: 0 !important;
  border: none !important;
}

:deep(.dark-drawer .el-drawer__container) {
  background: var(--bg-dark) !important;
  box-shadow: none !important;
}

.drawer-inner {
  padding: 24px 20px;
  display: flex;
  flex-direction: column;
  gap: 24px;
  height: 100%;
  box-sizing: border-box;
  overflow-y: auto;
  background: var(--bg-dark);
}

.glass-card {
  background: var(--bg-glass);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid var(--border-glass);
  box-shadow: var(--shadow-glass);
}

/* ========== 用户信息卡片 ========== */
.profile-card {
  padding: 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border-radius: 12px;
}

.profile-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.profile-avatar {
  background: var(--primary-color);
  color: var(--text-inverse);
  font-weight: 600;
}

.profile-meta {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.username {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.role-tag {
  width: fit-content;
}

.logout-btn {
  flex-shrink: 0;
}

/* ========== 通用区块 ========== */
.section-block {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-glass);
}

.title-icon {
  font-size: 16px;
}

.action-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.action-btn {
  height: auto;
  padding: 12px 10px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
  font-size: 13px;
  position: relative;
  white-space: normal;
  text-align: left;
}

/* ✅ 新增：使抽屉内部知识图谱按钮左对齐且有呼吸灯质感 */
.text-left-btn {
  text-align: left;
  justify-content: flex-start;
  padding-left: 16px;
  border-color: var(--border-light) !important;
  color: var(--success) !important;
}
.text-left-btn:hover {
  background: var(--bg-hover) !important;
}

.badge {
  position: absolute;
  top: 6px;
  right: 8px;
  background: var(--danger);
  color: var(--text-inverse);
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 10px;
  line-height: 1.4;
}

.full-width-btn {
  width: 100%;
  height: 44px;
}

/* ========== 维修记录 - 与管理端对齐 ========== */
.history-section {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.card-list-container {
  flex: 1;
  overflow-y: auto;
  padding-right: 4px;
  display: flex;
  flex-direction: column;
}

.data-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  margin-bottom: 12px;
  border-radius: 12px;
  transition: all 0.2s ease;
}

.data-card:hover {
  border-color: var(--border-light);
  transform: translateY(-1px);
}

.card-info-group {
  display: flex;
  align-items: center;
  flex: 1;
  gap: 0;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  text-align: left;
  flex-shrink: 0;
}

.info-label {
  font-size: 12px;
  color: var(--text-secondary);
  text-align: left;
  line-height: 1;
}

.info-value {
  font-size: 13px;
  font-weight: 500;
  text-align: left;
  line-height: 1.2;
  color: var(--text-primary);
}

.mono-text {
  font-family: 'Cascadia Code', 'Fira Code', 'JetBrains Mono', ui-monospace, Consolas, monospace;
  color: var(--accent-blue);
}

.col-order-id {
  flex: 0 0 140px;
  padding-right: 16px;
}

.col-time {
  flex: 0 0 130px;
  padding-right: 16px;
}

.col-round {
  flex: 0 0 90px;
}

.card-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
  margin-left: 16px;
}

/* 深色空状态 */
.dark-empty :deep(.el-empty__description) {
  color: var(--text-muted);
}

/* ========== 历史对话查看（内嵌模式） ========== */
.history-view-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 16px;
  background: var(--bg-glass);
  border-bottom: 1px solid var(--border-glass);
}

.history-view-banner .banner-title {
  font-size: 13px;
  color: var(--text-muted);
}

/* ✅ 新增：深度穿透强行适配 Element Plus Dialog 暗色炫酷质感 */
:deep(.el-dialog) {
  background: var(--bg-dark) !important;
  border: 1px solid var(--border-glass) !important;
  border-radius: 12px;
}
:deep(.el-dialog__title) {
  color: var(--text-primary) !important;
  font-weight: 600;
  font-size: 16px;
}
:deep(.el-dialog__body) {
  background: var(--bg-dark) !important;
  padding: 12px !important;
}
:deep(.el-dialog__headerbtn .el-dialog__close) {
  color: var(--text-secondary) !important;
}
:deep(.el-dialog__headerbtn:hover .el-dialog__close) {
  color: var(--accent-blue) !important;
}

/* 滚动条美化 */
.drawer-inner::-webkit-scrollbar {
  width: 6px;
}
.drawer-inner::-webkit-scrollbar-track {
  background: var(--bg-dark);
}
.drawer-inner::-webkit-scrollbar-thumb {
  background: var(--border-light);
  border-radius: 3px;
}
</style>

<style>
/* 添加了 :focus 和 :focus-visible 以拦截浏览器默认焦点框 */
.dark-drawer.el-drawer,
.dark-drawer.el-drawer:focus,
.dark-drawer.el-drawer:focus-visible,
.dark-drawer .el-drawer__body,
.dark-drawer .el-drawer__container {
  background-color: var(--bg-dark) !important;
  border: none !important;
  box-shadow: none !important;
  outline: none !important;
}
.dark-drawer .el-drawer__body {
  padding: 0 !important;
}
/* 左侧分隔线兜底 */
.dark-drawer.el-drawer {
  border-left: 1px solid var(--border-glass) !important;
}
</style>
