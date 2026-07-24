<template>
  <div class="chat-view-container">
    <div class="system-header">
      <div class="header-title">智能设备多模态检修控制台</div>
      <div class="header-right-actions" style="display: flex; align-items: center; gap: 16px;">
        <el-button type="primary" link class="graph-btn" @click="$router.push('/dashboard')">
          📊 故障大屏
        </el-button>
        <el-button type="primary" link class="graph-btn" @click="$router.push('/automotive')">
          🚗 设备大屏
        </el-button>
        <el-button v-if="store.hasPermission('view_graph')" type="primary" link class="graph-btn" @click="showGraphDialog = true">
          🌐 查看知识图谱
        </el-button>
        <el-button type="primary" link class="user-center-btn" @click="showUserCenter = true">
          👤 个人空间 ({{ roleNameMap[store.role] || store.role }})
        </el-button>
      </div>
    </div>

    <div class="chat-body-layout">
      <ChatSidebar />
      <div class="chat-main-area">
        <ChatMessageList />
        <ChatComposer />
      </div>

      <div class="chat-right-panel">
        <RightPanel
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
                {{ roleNameMap[store.role] || store.role }}
              </el-tag>
            </div>
          </div>
          <el-button type="danger" plain size="small" class="logout-btn" @click="handleLogout">
            退出登录
          </el-button>
        </div>

        <div v-if="store.hasPermission('view_graph')" class="section-block">
          <div class="section-title">
            <span class="title-icon">🕸️</span>
            <span>设备学识中心</span>
          </div>
          <el-button type="success" plain class="full-width-btn text-left-btn" @click="showGraphDialog = true; showUserCenter = false;">
            📊 探索数字化设备知识图谱
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
            <span>我的归档结单数据</span>
          </div>
          <div class="card-list-container">
            <el-empty v-if="historyReports.length === 0" description="暂无提报数据" :image-size="80" class="dark-empty" />
            <div v-for="item in historyReports" :key="item.orderId" class="glass-card data-card">
              <div class="card-info-group">
                <div class="info-item col-order-id">
                  <span class="info-label">工单编号</span>
                  <span class="info-value mono-text">{{ item.orderId }}</span>
                </div>
                <div class="info-item col-time">
                  <span class="info-label">派单时间</span>
                  <span class="info-value">{{ item.dispatchTime }}</span>
                </div>
                <div class="info-item col-time">
                  <span class="info-label">结单提报时间</span>
                  <span class="info-value">{{ item.submitTime }}</span>
                </div>
                <div class="info-item col-round">
                  <span class="info-label">交互轮数</span>
                  <el-tag size="small" effect="dark">{{ item.messages?.length || 0 }} 轮</el-tag>
                </div>
              </div>
              <div class="card-actions">
                <el-button size="small" type="primary" link @click="viewHistoryChat(item)">
                  查看完整对话流
                </el-button>
              </div>
            </div>
          </div>
        </div>

        <template v-else>
          <el-empty description="实习账号不开放工单提报与审查权限" :image-size="100" class="dark-empty" />
        </template>
      </div>
    </el-drawer>

    <el-dialog v-model="showHistoryDialog" :title="`对话回溯 [单号: ${selectedHistoryOrder}]`" width="650px" destroy-on-close>
      <div class="history-chat-viewer">
        <div v-for="msg in selectedChatHistory" :key="msg.id" :class="['history-msg-item', msg.role]">
          <div class="msg-sender">{{ msg.role === 'user' ? '操作员:' : 'AI助手:' }}</div>
          <div class="msg-text">{{ msg.content }}</div>
        </div>
      </div>
    </el-dialog>

    <el-dialog v-model="showGraphDialog" title="数字化智能设备知识图谱网络" width="85%" top="5vh" destroy-on-close append-to-body>
      <div class="graph-dialog-body">
        <KnowledgeGraph />
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import ChatSidebar from '../components/ChatSidebar.vue';
import ChatMessageList from '../components/ChatMessageList.vue';
import ChatComposer from '../components/ChatComposer.vue';
import RightPanel from '../components/RightPanel.vue';
import KnowledgeGraph from '../components/KnowledgeGraph.vue'; // ✅ 新增：导入图谱可视化组件
import { useChatStore } from '../stores/chat';

const router = useRouter();
const store = useChatStore();
const showUserCenter = ref(false);
const showHistoryDialog = ref(false);
const showGraphDialog = ref(false); // ✅ 新增：控制知识图谱弹窗开启闭合
const selectedChatHistory = ref<Array<any>>([]);
const selectedHistoryOrder = ref('');
const historyReports = computed(() => store.globalReports);

const roleNameMap: Record<string, string> = {
  admin: '管理中枢',
  senior: '高级职工',
  employee: '普通员工',
  intern: '实习生'
};

const handleReportSubmitted = (report: any) => {
  store.submitReport(report);
  const newId = 'session_' + Date.now();
  store.sessions.unshift({
    id: newId,
    title: '新检修任务',
    messages: [],
    updatedAt: Date.now()
  });
  store.activateSession(newId);
  ElMessage.success('报告已提交归档');
};

const viewHistoryChat = (item: any) => {
  selectedHistoryOrder.value = item.orderId;
  selectedChatHistory.value = item.messages || [];
  showHistoryDialog.value = true;
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
  height: 50px;
  background: #0f172a;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  flex-shrink: 0;
}

.header-title {
  color: #f1f5f9;
  font-weight: 600;
  font-size: 16px;
  letter-spacing: 1px;
}

/* ✅ 新增：顶栏知识图谱高亮按钮样式 */
.graph-btn {
  color: #10b981 !important;
  font-size: 14px;
  font-weight: 500;
}
.graph-btn:hover {
  color: #34d399 !important;
  text-shadow: 0 0 8px rgba(16, 185, 129, 0.5);
}

.user-center-btn {
  color: #38bdf8 !important;
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
  border-right: 1px solid rgba(255, 255, 255, 0.08);
  min-width: 0;
}

.chat-right-panel {
  width: 360px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* ========== 抽屉深色背景 + 彻底清除白边 ========== */
:deep(.dark-drawer.el-drawer) {
  background: #020617 !important;
  border: none !important;
  box-shadow: none !important;
  outline: none !important;
  border-left: 1px solid rgba(255, 255, 255, 0.08) !important;
}

:deep(.dark-drawer .el-drawer__body) {
  background: #020617 !important;
  padding: 0 !important;
  margin: 0 !important;
  border: none !important;
}

:deep(.dark-drawer .el-drawer__header) {
  background: #020617 !important;
  color: #f1f5f9 !important;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08) !important;
  margin-bottom: 0 !important;
  border: none !important;
}

:deep(.dark-drawer .el-drawer__container) {
  background: #020617 !important;
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
  background: #020617;
}

.glass-card {
  background: rgba(15, 23, 42, 0.75);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(131, 165, 221, 0.12);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
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
  background: linear-gradient(135deg, #0ea5e9, #3b82f6);
  color: white;
  font-weight: 600;
  box-shadow: 0 0 20px rgba(14, 165, 233, 0.4);
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
  color: #f8fafc;
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
  color: #e2e8f0;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
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
  border-color: rgba(16, 185, 129, 0.3) !important;
  color: #10b981 !important;
}
.text-left-btn:hover {
  background: rgba(16, 185, 129, 0.1) !important;
}

.badge {
  position: absolute;
  top: 6px;
  right: 8px;
  background: #ef4444;
  color: white;
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 10px;
  line-height: 1.4;
}

.full-width-btn {
  width: 100%;
  height: 44px;
}

/* ========== 归档结单数据 - 与管理端对齐 ========== */
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
  border-color: rgba(131, 165, 221, 0.25);
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
  color: #94a3b8;
  text-align: left;
  line-height: 1;
}

.info-value {
  font-size: 13px;
  font-weight: 500;
  text-align: left;
  line-height: 1.2;
  color: #f1f5f9;
}

.mono-text {
  font-family: 'Cascadia Code', 'Fira Code', 'JetBrains Mono', ui-monospace, Consolas, monospace;
  color: #38bdf8;
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
  color: #64748b;
}

/* ========== 历史对话弹窗 ========== */
.history-chat-viewer {
  max-height: 400px;
  overflow-y: auto;
  padding: 10px;
  background: #f8f9fa;
  border-radius: 6px;
}

.history-msg-item {
  margin-bottom: 12px;
  padding: 8px 12px;
  border-radius: 6px;
}

.history-msg-item.user {
  background: #eef2fe;
}

.history-msg-item.assistant {
  background: #fff;
  border: 1px solid #e5e8ef;
}

.msg-sender {
  font-size: 12px;
  font-weight: bold;
  margin-bottom: 4px;
}

.msg-text {
  font-size: 13px;
  color: #1d2129;
  line-height: 1.5;
}

/* ✅ 新增：图谱网络弹窗内部承载容器样式 */
.graph-dialog-body {
  height: 72vh;
  width: 100%;
  background: #020617;
  border-radius: 8px;
  overflow: hidden;
}

/* ✅ 新增：深度穿透强行适配 Element Plus Dialog 暗色炫酷质感 */
:deep(.el-dialog) {
  background: #0f172a !important;
  border: 1px solid rgba(255, 255, 255, 0.08) !important;
  border-radius: 12px;
}
:deep(.el-dialog__title) {
  color: #f1f5f9 !important;
  font-weight: 600;
  font-size: 16px;
}
:deep(.el-dialog__body) {
  background: #020617 !important;
  padding: 12px !important;
}
:deep(.el-dialog__headerbtn .el-dialog__close) {
  color: #94a3b8 !important;
}
:deep(.el-dialog__headerbtn:hover .el-dialog__close) {
  color: #38bdf8 !important;
}

/* 滚动条美化 */
.drawer-inner::-webkit-scrollbar {
  width: 6px;
}
.drawer-inner::-webkit-scrollbar-track {
  background: #020617;
}
.drawer-inner::-webkit-scrollbar-thumb {
  background: rgba(56, 189, 248, 0.5);
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
  background-color: #020617 !important;
  border: none !important;
  box-shadow: none !important;
  outline: none !important;
}
.dark-drawer .el-drawer__body {
  padding: 0 !important;
}
/* 左侧分隔线兜底 */
.dark-drawer.el-drawer {
  border-left: 1px solid rgba(255, 255, 255, 0.08) !important;
}
</style>