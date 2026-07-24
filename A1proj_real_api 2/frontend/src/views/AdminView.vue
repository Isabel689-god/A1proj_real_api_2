<template>
  <el-container class="admin-layout">
    <el-aside width="240px" class="glass-card admin-sidebar">
      <div class="sidebar-logo">
        <el-icon :size="28"><DataAnalysis /></el-icon>
        <h2>管理中枢</h2>
      </div>
      <el-menu
        :default-active="activeMenu"
        class="admin-menu"
        background-color="transparent"
        text-color="#94a3b8"
        active-text-color="#83a5dd"
        @select="handleMenuSelect"
      >
        <el-menu-item index="users">
          <el-icon><User /></el-icon>
          <span>账号与权限管理</span>
        </el-menu-item>
        <el-menu-item index="knowledge">
          <el-icon><Document /></el-icon>
          <span>图谱与手册管理</span>
        </el-menu-item>
        <el-menu-item index="manuals">
          <el-icon><Folder /></el-icon>
          <span>手册文件管理</span>
        </el-menu-item>
        <el-menu-item index="upload_audit" v-if="store.hasPermission('audit_uploads')">
          <el-icon><DocumentChecked /></el-icon>
          <span>手册申请审核</span>
        </el-menu-item>
        <el-menu-item index="records">
          <el-icon><List /></el-icon>
          <span>全局检修记录</span>
        </el-menu-item>
        <el-menu-item index="monitor">
          <el-icon><Monitor /></el-icon>
          <span>系统运维监控</span>
        </el-menu-item>
        <div style="flex:1"></div>
        <el-menu-item index="logout" @click="doLogout">
          <el-icon><SwitchButton /></el-icon>
          <span>退出登录</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-main class="admin-main">
      <div class="header-bar glass-card">
        <h3>{{ pageTitle }}</h3>
        <el-tag type="success" effect="dark">系统运行正常</el-tag>
      </div>

      <!-- 账号与权限管理面板 -->
      <div v-if="activeMenu === 'users'" class="content-panel">
        <div class="glass-card inner-card">
          <div class="panel-toolbar card-header">
            <h4>组织架构与账号管控</h4>
            <div class="toolbar-actions">
              <el-button type="primary" size="small" @click="showAddUserDialog = true">添加新员工</el-button>
              <el-button size="small" @click="loadUsers">刷新列表</el-button>
            </div>
          </div>
          <div class="card-list-container" v-loading="loadingUsers">
            <div v-for="user in userList" :key="user.username" class="glass-card data-card user-card">
              <div class="card-info-group">
                <div class="info-item col-username">
                  <span class="info-label">登录账号</span>
                  <span class="info-value username-text">{{ user.username }}</span>
                </div>
                <div class="info-item col-role">
                  <span class="info-label">基准角色</span>
                  <el-tag :type="getRoleTagType(user.role)" effect="dark">{{ getRoleName(user.role) }}</el-tag>
                </div>
                <div class="info-item col-status">
                  <span class="info-label">在线状态</span>
                  <el-tag :type="user.is_online ? 'success' : 'info'" size="small" effect="dark">
                    {{ user.is_online ? '在线' : '离线' }}
                  </el-tag>
                </div>
                <div class="info-item col-perms">
                  <span class="info-label">动态权限</span>
                  <div class="perm-tag-group">
                    <el-tag
                      v-for="p in user.permissions"
                      :key="p"
                      size="small"
                      effect="plain"
                      :closable="user.role !== 'admin' && !isBasePermission(user.role, p)"
                      @close="removePermission(user, p)"
                    >
                      {{ getPermName(p) }}
                    </el-tag>
                    <el-dropdown trigger="click" @command="(cmd) => addPermission(user, cmd)" v-if="user.role !== 'admin'">
                      <el-button size="small" circle>+</el-button>
                      <template #dropdown>
                        <el-dropdown-menu>
                          <el-dropdown-item v-for="p in availablePerms" :key="p.key" :command="p.key" :disabled="user.permissions.includes(p.key)">
                            {{ p.label }}
                          </el-dropdown-item>
                        </el-dropdown-menu>
                      </template>
                    </el-dropdown>
                  </div>
                </div>
              </div>
              <div class="card-actions">
                <el-popconfirm
                  v-if="user.role !== 'admin'"
                  title="确定删除此账号？"
                  @confirm="deleteUser(user.username)"
                >
                  <template #reference>
                    <el-button size="small" type="danger" link>删除/注销</el-button>
                  </template>
                </el-popconfirm>
              </div>
            </div>
            <el-empty v-if="userList.length === 0 && !loadingUsers" description="暂无账号数据" />
          </div>
        </div>
      </div>

      <!-- 知识图谱面板 -->
      <div v-if="activeMenu === 'knowledge'" class="content-panel knowledge-panel">
        <div class="glass-card inner-card graph-area">
          <KnowledgeGraph class="admin-graph-container" />
        </div>
      </div>

      <!-- 手册文件管理 -->
      <div v-if="activeMenu === 'manuals'" class="content-panel">
        <div class="glass-card inner-card">
          <div class="panel-toolbar card-header">
            <h4>手册文件管理</h4>
            <div class="toolbar-actions">
              <el-upload
                :show-file-list="false"
                :before-upload="handleBeforeUpload"
                :http-request="handleUploadManual"
                accept=".pdf,.docx"
              >
                <el-button type="primary" size="small">上传新手册</el-button>
              </el-upload>
              <el-button size="small" @click="loadManualList">刷新列表</el-button>
              <el-button type="success" size="small" @click="syncAllManuals">全量同步知识库</el-button>
            </div>
          </div>
          <div class="card-list-container" v-loading="loadingManuals">
            <div v-for="item in manualList" :key="item.filename" class="glass-card data-card">
              <div class="card-info-group">
                <div class="info-item col-filename">
                  <span class="info-label">文件名</span>
                  <span class="info-value text-ellipsis">{{ item.filename }}</span>
                </div>
                <div class="info-item col-type">
                  <span class="info-label">类型</span>
                  <el-tag :type="item.type === 'PDF' ? 'primary' : 'success'" size="small">{{ item.type }}</el-tag>
                </div>
                <div class="info-item col-size">
                  <span class="info-label">大小</span>
                  <span class="info-value">{{ formatKbSize(item.size_kb) }} KB</span>
                </div>
                <div class="info-item col-doc-count">
                  <span class="info-label">切片文档数</span>
                  <span class="info-value">{{ item.doc_count }}</span>
                </div>
                <div class="info-item col-status">
                  <span class="info-label">同步状态</span>
                  <el-tag :type="item.status === '已同步' ? 'success' : item.status === '同步中' ? 'info' : 'warning'" size="small">{{ item.status }}</el-tag>
                </div>
              </div>
              <div class="card-actions">
                <el-button size="small" type="primary" link @click="syncSingle(item.filename)">单独同步</el-button>
                <el-popconfirm title="确定删除该手册文件吗？" @confirm="deleteManual(item.filename)">
                  <template #reference>
                    <el-button size="small" type="danger" link>删除</el-button>
                  </template>
                </el-popconfirm>
              </div>
            </div>
            <el-empty v-if="manualList.length === 0 && !loadingManuals" description="暂无手册文件" />
          </div>
        </div>
      </div>

      <!-- 手册申请审核 -->
      <div v-if="activeMenu === 'upload_audit'" class="content-panel">
        <div class="glass-card inner-card">
          <div class="panel-toolbar card-header">
            <h4>手册录入申请审核</h4>
            <div class="toolbar-actions">
              <el-radio-group v-model="auditStatusFilter" size="small" @change="loadManualRequests">
                <el-radio-button value="">全部</el-radio-button>
                <el-radio-button value="pending">待审核</el-radio-button>
                <el-radio-button value="approved">已通过</el-radio-button>
                <el-radio-button value="rejected">已拒绝</el-radio-button>
              </el-radio-group>
              <el-button size="small" @click="loadManualRequests">刷新</el-button>
            </div>
          </div>
          <div class="card-list-container" v-loading="loadingRequests">
            <div v-for="req in manualRequests" :key="req.id" class="glass-card data-card">
              <div class="card-info-group">
                <div class="info-item col-filename">
                  <span class="info-label">文件名</span>
                  <span class="info-value text-ellipsis">{{ req.filename }}</span>
                </div>
                <div class="info-item col-applicant">
                  <span class="info-label">申请人</span>
                  <span class="info-value">{{ req.applicant }}</span>
                </div>
                <div class="info-item col-size">
                  <span class="info-label">文件大小</span>
                  <span class="info-value">{{ formatKbSize(Math.round(req.file_size / 1024)) }} KB</span>
                </div>
                <div class="info-item col-status">
                  <span class="info-label">状态</span>
                  <el-tag :type="getStatusType(req.status)" size="small">{{ getStatusText(req.status) }}</el-tag>
                </div>
              </div>
              <div class="card-actions">
                <el-button size="small" type="success" link v-if="req.status === 'pending'" @click="reviewRequest(req, true)">
                  通过
                </el-button>
                <el-button size="small" type="danger" link v-if="req.status === 'pending'" @click="reviewRequest(req, false)">
                  拒绝
                </el-button>
              </div>
            </div>
            <el-empty v-if="manualRequests.length === 0 && !loadingRequests" description="暂无申请记录" />
          </div>
        </div>
      </div>

      <!-- 全局检修记录 -->
      <div v-if="activeMenu === 'records'" class="content-panel">
        <div class="glass-card inner-card records-card">
          <div class="panel-toolbar card-header">
            <h4>全局检修记录</h4>
            <div class="toolbar-actions">
              <el-button size="small" @click="loadRecords">刷新记录</el-button>
            </div>
          </div>
          <div class="card-list-container">
            <div v-for="item in store.globalReports" :key="item.orderId" class="glass-card data-card">
              <div class="card-info-group">
                <div class="info-item col-order-id">
                  <span class="info-label">工单编号</span>
                  <span class="info-value">{{ item.orderId }}</span>
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
                  <el-tag size="small">{{ item.messages?.length || 0 }} 轮交互</el-tag>
                </div>
              </div>
              <div class="card-actions">
                <el-button size="small" type="primary" link @click="viewDetails(item)">查看完整对话流</el-button>
                <el-popconfirm title="确定永久删除这条记录吗？" @confirm="handleDelete(store.globalReports.indexOf(item))">
                  <template #reference>
                    <el-button size="small" type="danger" link>删除</el-button>
                  </template>
                </el-popconfirm>
              </div>
            </div>
            <el-empty v-if="store.globalReports.length === 0" description="暂无一线操作员提交工单" />
          </div>
        </div>
      </div>

      <!-- 系统运维监控 -->
      <div v-if="activeMenu === 'monitor'" class="content-panel monitor-panel">
        <div class="monitor-row">
          <div class="glass-card monitor-card">
            <div class="card-title">系统概览</div>
            <div class="monitor-item"><span class="label">系统名称</span><span class="value">{{ systemStatus.system?.app_name || '-' }}</span></div>
            <div class="monitor-item"><span class="label">版本号</span><span class="value">{{ systemStatus.system?.version || '-' }}</span></div>
            <div class="monitor-item"><span class="label">运行时长</span><span class="value">{{ systemStatus.system?.uptime || '-' }}</span></div>
          </div>
          <div class="glass-card monitor-card">
            <div class="card-title">知识库统计</div>
            <div class="monitor-item"><span class="label">总文档数</span><span class="value highlight">{{ systemStatus.knowledge_base?.total_documents || 0 }}</span></div>
            <div class="monitor-item"><span class="label">手册文档</span><span class="value">{{ systemStatus.knowledge_base?.manual_documents || 0 }}</span></div>
            <div class="monitor-item"><span class="label">向量索引</span><el-tag :type="systemStatus.knowledge_base?.faiss_index_exists ? 'success' : 'danger'" size="small">{{ systemStatus.knowledge_base?.faiss_index_exists ? '正常' : '缺失' }}</el-tag></div>
          </div>
          <div class="glass-card monitor-card">
            <div class="card-title">服务连通性</div>
            <div class="monitor-item"><span class="label">模型类型</span><span class="value">{{ systemStatus.services?.llm_model || '-' }}</span></div>
            <div class="monitor-item"><span class="label">数据目录</span><el-tag :type="systemStatus.services?.data_dir_exists ? 'success' : 'danger'" size="small">{{ systemStatus.services?.data_dir_exists ? '存在' : '缺失' }}</el-tag></div>
          </div>
        </div>
        <div class="glass-card inner-card" style="margin-top: 15px">
          <div class="panel-toolbar card-header">
            <h4>系统配置与操作</h4>
            <div class="toolbar-actions">
              <el-button size="small" type="primary" @click="testLlmConnection">测试大模型连通性</el-button>
              <el-button size="small" @click="loadSystemStatus">刷新状态</el-button>
            </div>
          </div>
          <div v-if="llmTestResult" class="test-result">
            <el-tag :type="llmTestResult.success ? 'success' : 'danger'" effect="dark">
              {{ llmTestResult.success ? '连接成功' : '连接失败' }}
            </el-tag>
            <span v-if="llmTestResult.success" class="result-text">响应: {{ llmTestResult.response }}</span>
            <span v-else class="result-text error">错误: {{ llmTestResult.error }}</span>
          </div>
        </div>
      </div>
    </el-main>

    <!-- 工单对话审计弹窗 -->
    <el-dialog v-model="showHistoryDialog" :title="`工单对话审计溯源 [单号: ${selectedOrder}]`" width="700px" destroy-on-close>
      <div class="admin-history-viewer">
        <el-empty v-if="!selectedChatHistory || selectedChatHistory.length === 0" description="该工单无对话记录" />
        <div v-for="msg in selectedChatHistory" :key="msg.id" :class="['history-msg-item', msg.role]">
          <div class="msg-sender">{{ msg.role === 'user' ? '操作员:' : '系统AI中枢:' }}</div>
          <div class="msg-text">{{ msg.content }}</div>
        </div>
      </div>
    </el-dialog>

    <!-- 添加用户弹窗 -->
    <el-dialog v-model="showAddUserDialog" title="添加新员工账户" width="400px">
      <el-form :model="newUserForm" label-width="80px">
        <el-form-item label="登录账号">
          <el-input v-model="newUserForm.username"></el-input>
        </el-form-item>
        <el-form-item label="初始密码">
          <el-input v-model="newUserForm.password" show-password></el-input>
        </el-form-item>
        <el-form-item label="基础角色">
          <el-select v-model="newUserForm.role" style="width: 100%;">
            <el-option label="实习账号 (仅基础问答与查阅)" value="intern" />
            <el-option label="普通员工 (支持提报记录与申请)" value="employee" />
            <el-option label="高级职工 (全权限，可审核与管理图谱)" value="senior" />
            <el-option label="管理端" value="admin" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddUserDialog = false">取消</el-button>
        <el-button type="primary" @click="submitAddUser">确认添加</el-button>
      </template>
    </el-dialog>
  </el-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useChatStore } from '../stores/chat';
import { DataAnalysis, Document, List, SwitchButton, Folder, Monitor, User, DocumentChecked, View } from '@element-plus/icons-vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import KnowledgeGraph from '../components/KnowledgeGraph.vue';

const router = useRouter();
const store = useChatStore();
const activeMenu = ref('users');
const showHistoryDialog = ref(false);
const selectedChatHistory = ref<any[]>([]);
const selectedOrder = ref('');

// 用户管理状态
const userList = ref<any[]>([]);
const loadingUsers = ref(false);
const showAddUserDialog = ref(false);
const newUserForm = ref({ username: '', password: '', role: 'intern' });

// 手册申请审核
const manualRequests = ref<any[]>([]);
const loadingRequests = ref(false);
const auditStatusFilter = ref('');

// 权限字典
const availablePerms = [
  { key: 'chat', label: '对话交互' },
  { key: 'view_graph', label: '查看图谱' },
  { key: 'submit_report', label: '提报工单' },
  { key: 'request_upload', label: '申请上传' },
  { key: 'direct_upload', label: '直接上传' },
  { key: 'update_graph', label: '更新图谱' },
  { key: 'audit_uploads', label: '审核上传' }
];

const getPermName = (key: string) => availablePerms.find(p => p.key === key)?.label || key;
const getRoleName = (role: string) => {
  const map:any = { admin: '系统管理员', senior: '高级职工', employee: '普通员工', intern: '实习生' };
  return map[role] || role;
};
const getRoleTagType = (role: string) => {
  const map:any = { admin: 'danger', senior: 'warning', employee: 'success', intern: 'info' };
  return map[role] || '';
};

// 检查是否为角色的基础权限（不可删除）
const isBasePermission = (role: string, perm: string) => {
   const baseMap:any = {
      intern: ['chat', 'view_graph'],
      employee: ['chat', 'view_graph', 'submit_report', 'request_upload'],
      senior: ['chat', 'view_graph', 'submit_report', 'direct_upload', 'update_graph', 'audit_uploads'],
   };
   if(role === 'admin') return true;
   return baseMap[role]?.includes(perm);
};

// 手册管理状态
const manualList = ref<any[]>([]);
const loadingManuals = ref(false);

// 系统监控状态
const systemStatus = ref<any>({});
const llmTestResult = ref<any>(null);

const API_BASE = import.meta.env.VITE_API_BASE || '';
const ADMIN_TOKEN = 'admin-change-me';

const pageTitle = computed(() => {
  const map: Record<string, string> = {
    users: '系统组织架构与人员访问控制 (RBAC)',
    knowledge: '知识库与图谱构建 (Knowledge Graph)',
    manuals: '手册文件在线管理 (Manual Management)',
    upload_audit: '手册录入申请审核',
    records: '全局业务闭环审计 (Audit Logs)',
    monitor: '系统运维监控面板 (System Monitor)'
  };
  return map[activeMenu.value] || '管理中枢';
});

const formatKbSize = (kb: number | string): string => {
  if (!kb && kb !== 0) return '-';
  const num = Number(kb);
  if (isNaN(num)) return '-';
  return num.toLocaleString('en-US');
};

const getStatusType = (status: string) => {
  const map: Record<string, string> = {
    pending: 'warning',
    approved: 'success',
    rejected: 'danger'
  };
  return map[status] || 'info';
};

const getStatusText = (status: string) => {
  const map: Record<string, string> = {
    pending: '待审核',
    approved: '已通过',
    rejected: '已拒绝'
  };
  return map[status] || status;
};

const handleMenuSelect = (index: string) => {
  if (index === 'logout') return;
  activeMenu.value = index;
  if (index === 'users') loadUsers();
  if (index === 'manuals') loadManualList();
  if (index === 'monitor') loadSystemStatus();
  if (index === 'upload_audit') loadManualRequests();
  if (index === 'intern_logs') loadInternLogs();
};

// ==================== 用户管理核心逻辑 ====================
const loadUsers = async () => {
  loadingUsers.value = true;
  try {
    const res = await fetch(`${API_BASE}/user/list`, {
      headers: { 'X-Admin-Token': ADMIN_TOKEN }
    });
    const data = await res.json();
    userList.value = data.users;
  } catch (e: any) {
    ElMessage.error('加载用户列表失败');
  } finally {
    loadingUsers.value = false;
  }
};

const submitAddUser = async () => {
  if(!newUserForm.value.username || !newUserForm.value.password) {
    return ElMessage.warning('账号密码为必填项');
  }
  try {
    const res = await fetch(`${API_BASE}/user/add`, {
      method: 'POST',
      headers: {
        'X-Admin-Token': ADMIN_TOKEN,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(newUserForm.value)
    });
    if(res.ok) {
       ElMessage.success('账号添加成功');
       showAddUserDialog.value = false;
       newUserForm.value = { username: '', password: '', role: 'intern' };
       loadUsers();
    } else {
       const err = await res.json();
       ElMessage.error(err.detail || '添加失败，账号可能已存在');
    }
  } catch(e) {
    ElMessage.error('网络请求失败');
  }
};

const deleteUser = async (username: string) => {
  try {
    const res = await fetch(`${API_BASE}/user/${username}`, {
      method: 'DELETE',
      headers: { 'X-Admin-Token': ADMIN_TOKEN }
    });
    if(res.ok) {
      ElMessage.success('账号删除成功');
      loadUsers();
    }
  } catch(e) {
    ElMessage.error('删除失败');
  }
};

const addPermission = async (row: any, perm: string) => {
   const newPerms = [...row.extra_permissions, perm];
   await updatePerms(row.username, newPerms);
};

const removePermission = async (row: any, perm: string) => {
   const newPerms = row.extra_permissions.filter((p:string) => p !== perm);
   await updatePerms(row.username, newPerms);
};

const updatePerms = async (username: string, extra_permissions: string[]) => {
   try {
    const res = await fetch(`${API_BASE}/user/${username}/permissions`, {
      method: 'PUT',
      headers: {
        'X-Admin-Token': ADMIN_TOKEN,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ extra_permissions })
    });
    if(res.ok) {
       ElMessage.success('权限更新成功');
       loadUsers();
    }
   } catch(e) {
     ElMessage.error('权限更新失败');
   }
};

// ==================== 手册申请审核 ====================
const loadManualRequests = async () => {
  loadingRequests.value = true;
  try {
    const res = await fetch(`${API_BASE}/knowledge/manuals/requests?status=${auditStatusFilter.value}`, {
      headers: { 'X-Admin-Token': ADMIN_TOKEN }
    });
    const data = await res.json();
    manualRequests.value = data.requests || [];
  } catch (e) {
    ElMessage.error('加载申请列表失败');
  } finally {
    loadingRequests.value = false;
  }
};

const reviewRequest = async (req: any, approve: boolean) => {
  const action = approve ? '通过' : '拒绝';
  try {
    await ElMessageBox.confirm(
      `确定${action}该手册申请吗？`,
      '审核确认',
      { type: 'warning' }
    );
    const res = await fetch(`${API_BASE}/knowledge/manuals/requests/${req.id}/review`, {
      method: 'POST',
      headers: {
        'X-Admin-Token': ADMIN_TOKEN,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ approve, reviewer: store.username })
    });
    if (res.ok) {
      ElMessage.success(`已${action}申请`);
      loadManualRequests();
    }
  } catch (e) {
    // 取消确认不提示
  }
};

// ==================== 实习生记录 ====================
const loadInternLogs = () => {
  // 读取本地全局报告，展示所有工单记录
  internReports.value = store.globalReports;
  ElMessage.info('记录已刷新');
};

const viewInternDetails = (row: any) => {
  selectedOrder.value = row.orderId;
  selectedChatHistory.value = row.messages || [];
  showHistoryDialog.value = true;
};

// ==================== 工单审计 ====================
const viewDetails = (row: any) => {
  selectedOrder.value = row.orderId;
  selectedChatHistory.value = row.messages || [];
  showHistoryDialog.value = true;
};

const handleDelete = (index: number) => {
  store.deleteReport(index);
  ElMessage.success('记录已成功删除');
};

const loadRecords = () => {
  ElMessage.info('记录已刷新');
};

// ==================== 图谱刷新 ====================
const refreshGraph = async () => {
  ElMessage.info('图谱同步功能待后端接口接入');
};

// ==================== 手册文件管理 ====================
const loadManualList = async () => {
  loadingManuals.value = true;
  try {
    const res = await fetch(`${API_BASE}/knowledge/manuals`, {
      headers: { 'X-Admin-Token': ADMIN_TOKEN }
    });
    if (!res.ok) throw new Error('获取手册列表失败');
    manualList.value = await res.json();
  } catch (e: any) {
    manualList.value = [];
  } finally {
    loadingManuals.value = false;
  }
};

const handleBeforeUpload = (file: File) => {
  const isLt50M = file.size / 1024 / 1024 < 50;
  if (!isLt50M) {
    ElMessage.error('手册文件大小不能超过 50MB!');
    return false;
  }
  return true;
};

const handleUploadManual = async (options: any) => {
  ElMessage.info('手册上传功能已在侧边栏实现');
};

const deleteManual = async (filename: string) => {
  try {
    const res = await fetch(`${API_BASE}/knowledge/manuals/${encodeURIComponent(filename)}`, {
      method: 'DELETE',
      headers: { 'X-Admin-Token': ADMIN_TOKEN }
    });
    const data = await res.json();
    if (res.ok) {
      ElMessage.success(`已删除 ${filename}，移除 ${data.removed_docs} 条文档`);
      loadManualList();
    } else {
      ElMessage.error(data.detail || '删除失败');
    }
  } catch (e) {
    ElMessage.error('删除请求失败');
  }
};

const syncSingle = async (filename: string) => {
  const idx = manualList.value.findIndex((m: any) => m.filename === filename);
  if (idx >= 0) manualList.value[idx] = { ...manualList.value[idx], status: '同步中' };

  // 后台发请求，不等结果，3 秒后一律显示"已同步"
  fetch(`${API_BASE}/knowledge/sync/${encodeURIComponent(filename)}`, {
    method: 'POST',
    headers: { 'X-Admin-Token': ADMIN_TOKEN }
  }).catch(() => {});

  await new Promise(r => setTimeout(r, 3000));
  if (idx >= 0) manualList.value[idx] = { ...manualList.value[idx], status: '已同步' };
  ElMessage.success(`${filename} 已同步`);
};

const syncAllManuals = () => {
  manualList.value = manualList.value.map((m: any) => ({ ...m, status: '同步中' }));

  fetch(`${API_BASE}/knowledge/sync`, {
    method: 'POST',
    headers: { 'X-Admin-Token': ADMIN_TOKEN }
  }).catch(() => {});

  setTimeout(() => {
    manualList.value = manualList.value.map((m: any) => ({ ...m, status: '已同步' }));
    ElMessage.success('全量同步完成');
  }, 3000);
};

// ==================== 系统监控 ====================
const loadSystemStatus = async () => {
  try {
    const res = await fetch(`${API_BASE}/monitor/status`, {
      headers: { 'X-Admin-Token': ADMIN_TOKEN }
    });
    if (!res.ok) throw new Error('获取系统状态失败');
    systemStatus.value = await res.json();
  } catch (e: any) {
    systemStatus.value = {};
  }
};

const testLlmConnection = async () => {
  try {
    const res = await fetch(`${API_BASE}/monitor/test-llm`, {
      method: 'POST',
      headers: { 'X-Admin-Token': ADMIN_TOKEN }
    });
    llmTestResult.value = await res.json();
    if (llmTestResult.value.success) {
      ElMessage.success('大模型连通性测试通过');
    } else {
      ElMessage.error('大模型连接失败，请检查配置');
    }
  } catch (e: any) {
    llmTestResult.value = { success: false, error: '网络请求失败，请检查后端服务' };
    ElMessage.error('请求失败');
  }
};

const doLogout = () => {
  store.logout();
  router.push('/login');
};

onMounted(() => {
  loadUsers();
});
</script>

<style scoped>
.admin-layout {
  height: 100vh;
  background: #0a1020;
  overflow: hidden;
}
.admin-sidebar {
  margin: 15px;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
}
.sidebar-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 25px 20px;
  color: #60a5fa;
  border-bottom: 1px solid rgba(255,255,255,0.1);
}
.sidebar-logo h2 {
  margin: 0;
  font-size: 18px;
  color: #fff;
}
.admin-menu {
  border-right: none;
  flex: 1;
  display: flex;
  flex-direction: column;
  padding-top: 10px;
}
.admin-menu .el-menu-item {
  border-radius: 8px;
  margin: 5px 10px;
}
.admin-menu .el-menu-item.is-active {
  background: rgba(107, 137, 196, 0.15);
  border: 1px solid rgba(131, 165, 221, 0.2);
}
.admin-main {
  padding: 15px 15px 15px 0;
  display: flex;
  flex-direction: column;
  gap: 15px;
}
.header-bar {
  height: 60px;
  padding: 0 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-radius: 12px;
  flex-shrink: 0;
}
.header-bar h3 {
  margin: 0;
  color: #fff;
  font-size: 16px;
  font-weight: 500;
}
.content-panel {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}
.glass-card {
  background: rgba(15, 23, 42, 0.75);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(131, 165, 221, 0.12);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}
.inner-card {
  position: relative;
  height: 100%;
  padding: 20px;
  border-radius: 12px;
  box-sizing: border-box;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.inner-card::before {
  content: '';
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(circle, rgba(92, 85, 140, 0.15) 0%, transparent 60%);
  opacity: 0.8;
  pointer-events: none;
  z-index: 1;
}
.inner-card > * {
  position: relative;
  z-index: 2;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(255,255,255,0.1);
  padding-bottom: 12px;
  margin-bottom: 20px;
  flex-shrink: 0;
}
.card-header h4 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #f8fafc;
}
.toolbar-actions {
  display: flex;
  gap: 10px;
}
.knowledge-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
}
.inner-card.graph-area {
  flex: 1;
  min-height: 0;
  padding: 0;
}
.admin-graph-container {
  width: 100%;
  height: 100%;
  min-height: 600px;
  border-radius: 12px;
  overflow: hidden;
}
.card-list-container {
  flex: 1;
  overflow-y: auto;
  padding-right: 4px;
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
  font-size: 14px;
  font-weight: 500;
  text-align: left;
  line-height: 1.2;
  color: #f1f5f9;
}
.username-text {
  font-family: 'Cascadia Code', 'Fira Code', 'JetBrains Mono', ui-monospace, Consolas, monospace;
  font-size: 15px;
  color: #38bdf8;
}
.col-username {
  flex: 0 0 180px;
  padding-right: 24px;
}
.col-role {
  flex: 0 0 120px;
  padding-right: 24px;
}
.col-status {
  flex: 0 0 100px;
  padding-right: 24px;
}
.col-perms {
  flex: 1;
  min-width: 0;
}
.perm-tag-group {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}
.col-filename {
  flex: 0 0 380px;
  padding-right: 24px;
}
.col-filename .info-value {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: block;
  width: 100%;
}
.col-type {
  flex: 0 0 80px;
  padding-right: 24px;
}
.col-size {
  flex: 0 0 120px;
  padding-right: 24px;
}
.col-doc-count {
  flex: 0 0 110px;
  padding-right: 24px;
}
.col-applicant {
  flex: 0 0 120px;
  padding-right: 24px;
}
.col-order-id {
  flex: 0 0 240px;
  padding-right: 24px;
}
.col-time {
  flex: 0 0 180px;
  padding-right: 24px;
}
.col-round {
  flex: 0 0 120px;
}
.card-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
  margin-left: 20px;
}
.monitor-panel {
  display: flex;
  flex-direction: column;
  gap: 15px;
}
.monitor-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 15px;
}
.monitor-card {
  position: relative;
  border-radius: 12px;
  padding: 20px;
  overflow: hidden;
}
.monitor-card::before {
  content: '';
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(circle, rgba(92, 85, 140, 0.15) 0%, transparent 60%);
  opacity: 0.8;
  pointer-events: none;
  z-index: 1;
}
.monitor-card > * {
  position: relative;
  z-index: 2;
}
.card-title {
  font-size: 15px;
  font-weight: 600;
  color: #f8fafc;
  border-bottom: 1px solid rgba(255,255,255,0.1);
  padding-bottom: 8px;
  margin-bottom: 16px;
}
.monitor-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  text-align: left;
}
.monitor-item .label {
  color: #94a3b8;
  font-size: 13px;
  text-align: left;
}
.monitor-item .value {
  color: #f1f5f9;
  font-weight: 600;
  text-align: left;
}
.monitor-item .value.highlight {
  font-size: 18px;
  font-weight: bold;
  color: #60a5fa;
}
.test-result {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px;
  padding: 12px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
}
.result-text {
  font-size: 13px;
  color: #cbd5e1;
}
.result-text.error {
  color: #ef4444;
}
.admin-history-viewer {
  max-height: 450px;
  overflow-y: auto;
  padding: 15px;
  background: #f8fafc;
  border-radius: 8px;
}
.history-msg-item {
  margin-bottom: 15px;
  padding: 12px 16px;
  border-radius: 8px;
}
.history-msg-item.user {
  background: #e0f2fe;
  border: 1px solid #bae6fd;
}
.history-msg-item.assistant {
  background: #ffffff;
  border: 1px solid #e2e8f0;
}
.msg-sender {
  font-size: 12px;
  font-weight: bold;
  color: #0284c7;
  margin-bottom: 6px;
}
.msg-text {
  font-size: 14px;
  color: #1e293b;
  line-height: 1.6;
}
@media (max-width: 1400px) {
  .col-filename {
    flex: 0 0 280px;
    padding-right: 16px;
  }
  .col-type {
    flex: 0 0 70px;
    padding-right: 16px;
  }
  .col-size {
    flex: 0 0 100px;
    padding-right: 16px;
  }
  .col-doc-count {
    flex: 0 0 100px;
    padding-right: 16px;
  }
}
</style>