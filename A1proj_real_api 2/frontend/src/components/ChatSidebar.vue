<template>
  <div class="chat-sidebar" :class="{ 'is-collapsed': isCollapsed }">
    <div class="sidebar-header-wrapper">
      <button class="icon-btn toggle-menu-btn" @click="toggleSidebar" title="扩展/收起侧边栏">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="3" y1="12" x2="21" y2="12"></line>
          <line x1="3" y1="6" x2="21" y2="6"></line>
          <line x1="3" y1="18" x2="21" y2="18"></line>
        </svg>
      </button>
      <h3 v-if="!isCollapsed" class="system-title">智能检修中枢</h3>
    </div>

    <div v-if="!isCollapsed" class="equipment-selector">
      <div class="selector-label">选择维修设备</div>
      <el-cascader
        v-model="selectedEquipment"
        :options="equipmentOptions"
        :props="{ expandTrigger: 'hover', checkStrictly: true }"
        placeholder="请选择设备类型及设备型号"
        size="small"
        class="equipment-cascader"
        clearable
      />
    </div>

    <div class="action-zone">
      <button
        @click="createNewSession"
        :class="isCollapsed ? 'new-session-circle-btn' : 'new-session-pill-btn'"
        title="新建检修工单"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width: 16px; height: 16px;">
          <line x1="12" y1="5" x2="12" y2="19"></line>
          <line x1="5" y1="12" x2="19" y2="12"></line>
        </svg>
        <span v-if="!isCollapsed">新建检修工单</span>
      </button>

      <button
        v-if="store.hasPermission('view_graph')"
        @click="showGraphDialog = true"
        :class="isCollapsed ? 'new-session-circle-btn mt-8' : 'new-session-pill-btn mt-8'"
        title="探索知识图谱"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width: 16px; height: 16px;">
          <circle cx="18" cy="5" r="3"></circle>
          <circle cx="6" cy="12" r="3"></circle>
          <circle cx="18" cy="19" r="3"></circle>
          <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line>
          <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line>
        </svg>
        <span v-if="!isCollapsed">探索知识图谱</span>
      </button>

      <button
        v-if="store.hasPermission('request_upload')"
        @click="showRequestDialog = true"
        :class="isCollapsed ? 'new-session-circle-btn mt-8' : 'new-session-pill-btn mt-8'"
        title="申请录入新手册"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width: 16px; height: 16px;">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
          <polyline points="17 8 12 3 7 8"></polyline>
          <line x1="12" y1="3" x2="12" y2="15"></line>
        </svg>
        <span v-if="!isCollapsed">申请录入手册</span>
      </button>

      <button
        v-if="store.hasPermission('direct_upload')"
        @click="showDirectUploadDialog = true"
        :class="isCollapsed ? 'new-session-circle-btn mt-8' : 'new-session-pill-btn mt-8'"
        title="直接上传设备手册"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width: 16px; height: 16px;">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
          <polyline points="14 2 14 8 20 8"></polyline>
          <line x1="12" y1="18" x2="12" y2="12"></line>
          <line x1="9" y1="15" x2="15" y2="15"></line>
        </svg>
        <span v-if="!isCollapsed">直接上传手册</span>
      </button>
    </div>

    <div class="session-list">
      <div v-if="!isCollapsed" class="list-section-title">最近记录</div>
      <div
        v-for="session in store.sessions"
        :key="session.id"
        :class="['session-item', { active: session.id === store.activeSessionId }]"
        @click="store.activateSession(session.id)"
        :title="session.title"
      >
        <div class="session-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
          </svg>
        </div>
        <div v-if="!isCollapsed" class="session-info">
          <span class="session-title-text">{{ session.title }}</span>
        </div>
        <button
          v-if="!isCollapsed && store.sessions.length > 1"
          class="session-delete-btn"
          @click.stop="store.deleteSession(session.id)"
          title="删除此对话"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px;">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
    </div>

    <div class="sidebar-footer" v-if="!isCollapsed">
      <button class="theme-toggle" @click="toggleTheme" :title="theme === 'dark' ? '切换浅色模式' : '切换深色模式'">
        <svg v-if="theme === 'dark'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="5"></circle>
          <line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line>
          <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
          <line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line>
          <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
        </svg>
        <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
        </svg>
        <span>{{ theme === 'dark' ? '浅色模式' : '深色模式' }}</span>
      </button>
      <button class="new-session-pill-btn logout-btn" @click="doLogout" title="退出系统">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width: 16px; height: 16px;">
          <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
          <polyline points="16 17 21 12 16 7"></polyline>
          <line x1="21" y1="12" x2="9" y2="12"></line>
        </svg>
        <span>退出登录</span>
      </button>
    </div>

    <el-dialog v-model="showGraphDialog" title="设备检修知识图谱网络" width="95%" top="2vh" destroy-on-close>
      <div class="graph-dialog-body">
        <KnowledgeGraph />
      </div>
    </el-dialog>

    <el-dialog v-model="showRequestDialog" title="申请录入新手册" width="480px" destroy-on-close>
      <el-form :model="requestForm" label-width="100px">
        <el-form-item label="手册文件">
          <el-upload :auto-upload="false" :show-file-list="true" :on-change="handleRequestFileChange" :limit="1" accept=".pdf,.docx">
            <el-button size="small" type="primary">选择文件</el-button>
            <template #tip><div class="el-upload__tip">最大 50MB</div></template>
          </el-upload>
        </el-form-item>
        <el-form-item label="设备型号">
          <el-input v-model="requestForm.deviceModel" placeholder="如：SINUMERIK 808D" />
        </el-form-item>
        <el-form-item label="申请说明">
          <el-input v-model="requestForm.description" type="textarea" :rows="3" placeholder="简述手册来源与用途" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showRequestDialog = false">取消</el-button>
        <el-button type="primary" :loading="submittingRequest" @click="submitRequest">提交申请</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showDirectUploadDialog" title="直接上传设备手册" width="680px" destroy-on-close>
      <el-form :model="uploadForm" label-width="100px">
        <el-form-item label="手册文件">
          <el-upload :auto-upload="false" :show-file-list="true" :on-change="handleUploadFileChange" :limit="1" accept=".pdf,.docx">
            <el-button size="small" type="primary">选择文件</el-button>
            <template #tip><div class="el-upload__tip">上传后自动同步知识库</div></template>
          </el-upload>
        </el-form-item>
        <el-form-item label="同步知识库">
          <el-switch v-model="uploadForm.autoSync" active-text="上传后自动同步" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDirectUploadDialog = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="submitDirectUpload">确认上传</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, inject } from 'vue';
import { useRouter } from 'vue-router';
import { useChatStore } from '../stores/chat';
import { ElMessage } from 'element-plus';
import KnowledgeGraph from './KnowledgeGraph.vue';

const theme = inject<any>('theme', ref('dark'))
const toggleTheme = inject<() => void>('toggleTheme', () => {})

const router = useRouter();
const store = useChatStore();
const isCollapsed = ref(false);
const selectedEquipment = ref<string[]>([]);

const equipmentOptions = [
  {
    value: 'cnc',
    label: '数控机床',
    children: [
      {
        value: 'machining_center',
        label: '加工中心类',
        children: [
          { value: 'vmc', label: '立式加工中心' },
          { value: 'hmc', label: '卧式加工中心' },
          { value: 'gantry', label: '龙门加工中心' },
        ],
      },
      {
        value: 'cnc_lathe',
        label: '数控车削类',
        children: [
          { value: 'cnc_lathe_normal', label: '普通数控车床' },
          { value: 'cnc_lathe_dual', label: '双主轴数控车' },
          { value: 'cnc_lathe_5axis', label: '五轴车铣复合中心' },
        ],
      },
      {
        value: 'gear_cnc',
        label: '齿轮专用数控设备',
        children: [
          { value: 'gear_hobbing', label: '数控滚齿机' },
          { value: 'gear_shaping', label: '数控插齿机' },
          { value: 'gear_grinding', label: '数控磨齿机' },
          { value: 'gear_honing', label: '数控珩齿机' },
        ],
      },
      {
        value: 'cnc_grinder',
        label: '数控磨床类',
        children: [
          { value: 'grinder_outer', label: '数控外圆磨床' },
          { value: 'grinder_inner', label: '数控内圆磨床' },
          { value: 'grinder_surface', label: '数控平面磨床' },
          { value: 'grinder_coordinate', label: '数控坐标磨床' },
        ],
      },
      {
        value: 'new_energy',
        label: '新能源配套专用数控设备',
        children: [
          { value: 'ne_5axis', label: '高速五轴加工中心' },
          { value: 'ne_deep_hole', label: '数控深孔钻床' },
          { value: 'ne_profile_mill', label: '数控型材铣削机' },
        ],
      },
      {
        value: 'sheet_metal',
        label: '钣金、模具特种数控设备',
        children: [
          { value: 'laser_cutting', label: '数控激光切割机' },
          { value: 'press_brake', label: '数控折弯机' },
          { value: 'edm', label: '数控电火花机床' },
          { value: 'wire_cut', label: '数控线切割机床' },
        ],
      },
    ],
  },
  {
    value: 'conveyor',
    label: '输送线',
    children: [
      { value: 'conveyor_hoisting', label: '吊装线' },
      { value: 'conveyor_door', label: '门线' },
      { value: 'conveyor_interior', label: '内饰线' },
      { value: 'conveyor_instrument', label: '仪表线' },
    ],
  },
];

const showGraphDialog = ref(false);
const showRequestDialog = ref(false);
const showDirectUploadDialog = ref(false);
const submittingRequest = ref(false);
const uploading = ref(false);

const requestForm = reactive({ file: null as File | null, deviceModel: '', description: '' });
const uploadForm = reactive({ file: null as File | null, autoSync: false });

const API_BASE = import.meta.env.VITE_API_BASE || '';
const ADMIN_TOKEN = 'admin-change-me';

const toggleSidebar = () => isCollapsed.value = !isCollapsed.value;

const createNewSession = () => {
  store.createNewSession();
};

const doLogout = async () => {
  await store.logout();
  router.push('/login');
};

const handleRequestFileChange = (file: any) => requestForm.file = file.raw;
const handleUploadFileChange = (file: any) => uploadForm.file = file.raw;

const submitRequest = async () => {
  if (!requestForm.file) return ElMessage.warning('请先选择手册文件');
  submittingRequest.value = true;
  try {
    const formData = new FormData();
    formData.append('file', requestForm.file);
    formData.append('username', store.username);
    formData.append('description', requestForm.description);
    if (requestForm.deviceModel) formData.append('device_model', requestForm.deviceModel);

    const res = await fetch(`${API_BASE}/knowledge/manuals/request`, { method: 'POST', body: formData });
    const data = await res.json();
    if (res.ok) {
      ElMessage.success('申请已提交，等待审核');
      showRequestDialog.value = false;
      requestForm.file = null;
      requestForm.deviceModel = '';
      requestForm.description = '';
    } else {
      ElMessage.error(data.detail || '提交失败');
    }
  } catch (e) {
    ElMessage.error('网络请求失败');
  } finally {
    submittingRequest.value = false;
  }
};

const submitDirectUpload = async () => {
  if (!uploadForm.file) return ElMessage.warning('请先选择手册文件');
  uploading.value = true;
  try {
    const formData = new FormData();
    formData.append('file', uploadForm.file);
    const res = await fetch(`${API_BASE}/knowledge/manuals/upload`, {
      method: 'POST',
      headers: { 'X-Admin-Token': ADMIN_TOKEN },
      body: formData
    });
    const data = await res.json();
    if (res.ok) {
      ElMessage.success('手册上传成功！请在管理中枢手动同步知识库');
      showDirectUploadDialog.value = false;
      uploadForm.file = null;
    } else {
      ElMessage.error(data.detail || '上传失败');
    }
  } catch (e) {
    ElMessage.error('网络请求失败');
  } finally {
    uploading.value = false;
  }
};
</script>

<style scoped>
.chat-sidebar {
  width: 260px;
  height: 100vh;
  background: linear-gradient(180deg, var(--bg-darker) 0%, var(--bg-dark) 100%);
  border-right: 1px solid var(--border-glass);
  display: flex;
  flex-direction: column;
  transition: width 0.25s cubic-bezier(0.4, 0, 0.2, 1), background 0.35s ease;
  overflow: hidden;
  flex-shrink: 0;
  z-index: 100;
}
.chat-sidebar.is-collapsed { width: 68px; }

.sidebar-header-wrapper {
  display: flex;
  align-items: center;
  padding: 16px;
  gap: 12px;
  height: 60px;
  border-bottom: 1px solid var(--border-glass);
}
.icon-btn {
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  transition: all 0.2s;
}
.icon-btn:hover { background: var(--bg-hover); color: var(--primary-color); }
.toggle-menu-btn svg { width: 20px; height: 20px; }
.system-title {
  font-size: 14px; font-weight: 600;
  background: linear-gradient(90deg, #00c8b4, #38bdf8);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text;
  white-space: nowrap;
}

.equipment-selector {
  padding: 12px 14px;
  border-bottom: 1px solid var(--border-glass);
}
.selector-label {
  font-size: 11px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 8px;
}
:deep(.equipment-cascader .el-input__wrapper) {
  background: var(--bg-soft);
  border: 1px solid var(--border-glass);
  box-shadow: none;
  border-radius: 8px;
}
:deep(.equipment-cascader .el-input__wrapper:hover) {
  border-color: rgba(0, 200, 180, 0.3);
}
:deep(.equipment-cascader .el-input__inner) {
  color: var(--text-primary);
  font-size: 13px;
}

.action-zone {
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  border-bottom: 1px solid var(--border-glass);
}
.is-collapsed .action-zone { align-items: center; padding: 12px 0; }

.new-session-pill-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  height: 40px;
  border-radius: 10px;
  border: 1px solid var(--border-glass);
  background: var(--bg-soft);
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  padding: 0 16px;
  transition: all 0.25s;
}
.new-session-pill-btn:hover {
  background: var(--bg-hover);
  border-color: var(--primary-color);
  color: var(--primary-color);
}
.new-session-circle-btn {
  width: 40px; height: 40px;
  border-radius: 50%;
  border: 1px solid var(--border-glass);
  background: var(--bg-soft);
  color: var(--text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.25s;
}
.new-session-circle-btn:hover {
  background: var(--bg-hover);
  border-color: var(--primary-color);
  color: var(--primary-color);
}

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}
.list-section-title {
  font-size: 11px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 1px;
  padding: 8px 8px 4px;
}
.session-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  color: var(--text-secondary);
}
.session-item:hover { background: var(--bg-hover); color: var(--text-primary); }
.session-item.active {
  background: var(--bg-hover);
  border: 1px solid var(--border-light);
  color: var(--primary-color);
}
.session-delete-btn {
  display: none;
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 2px;
  border-radius: 4px;
  flex-shrink: 0;
}
.session-item:hover .session-delete-btn {
  display: flex;
  align-items: center;
}
.session-delete-btn:hover {
  color: var(--danger);
  background: color-mix(in srgb, var(--danger) 12%, transparent);
}
.session-icon svg { width: 18px; height: 18px; }
.session-info { overflow: hidden; }
.session-title-text { font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: block; }

.sidebar-footer {
  padding: 12px 14px;
  border-top: 1px solid var(--border-glass);
}
.logout-btn {
  color: var(--text-secondary) !important;
}
.logout-btn:hover {
  color: var(--danger) !important;
  background: color-mix(in srgb, var(--danger) 10%, transparent) !important;
  border-color: color-mix(in srgb, var(--danger) 28%, transparent) !important;
}

.graph-dialog-body {
  height: 72vh;
  width: 100%;
  background: var(--bg-darker);
  border-radius: 8px;
  overflow: hidden;
}
</style>
