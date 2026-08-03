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
        text-color="var(--text-secondary)"
        active-text-color="#83a5dd"
        @select="handleMenuSelect"
      >
        <el-menu-item index="users">
          <el-icon><User /></el-icon>
          <span>账号与权限管理</span>
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
        <el-menu-item index="knowledge_mysql">
          <el-icon><DataAnalysis /></el-icon>
          <span>知识图谱(MySQL)</span>
        </el-menu-item>
        <el-menu-item index="knowledge_neo4j">
          <el-icon><DataAnalysis /></el-icon>
          <span>知识图谱(Neo4j)</span>
        </el-menu-item>
        <div style="flex:1"></div>
        <div style="padding: 10px;">
          <button class="theme-toggle" @click="toggleTheme">
            <span v-if="theme === 'dark'">☀️ 浅色模式</span>
            <span v-else>🌙 深色模式</span>
          </button>
        </div>
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
            <h4>权限组配置</h4>
            <div class="toolbar-actions">
              <el-button type="primary" size="small" @click="openGroupDialog()">新建权限组</el-button>
            </div>
          </div>
          <div class="card-list-container">
            <div v-for="(group, name) in permGroups" :key="name" class="glass-card data-card" style="padding:16px;margin-bottom:12px;">
              <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                <div style="flex:1;">
                  <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
                    <strong style="font-size:15px;color:var(--text-primary);">{{ name }}</strong>
                    <el-tag size="small" type="info">{{ group.permissions?.length || 0 }} 项权限</el-tag>
                    <el-tag size="small" type="warning">{{ group.members?.length || 0 }} 名成员</el-tag>
                  </div>
                  <p style="color:var(--text-muted);font-size:13px;margin:0 0 10px 0;">{{ group.description }}</p>
                  <!-- 成员列表（每人一行） -->
                  <div style="margin-bottom:8px;">
                    <div v-for="m in (group.members || [])" :key="m" class="member-row">
                      <span class="member-name" style="min-width:120px;">{{ m }}</span>
                      <el-tag :type="userStatusMap[m] ? 'success' : 'info'" size="small" effect="dark" style="margin:0 12px;">
                        {{ userStatusMap[m] ? '在线' : '离线' }}
                      </el-tag>
                      <div class="perm-tag-group" style="flex:1;">
                        <el-tag
                          v-for="p in (userPermMap[m] || [])" :key="p" size="small" effect="plain"
                          :closable="name !== '管理人员' && userExtraPermMap[m]?.includes(p)"
                          @close="removeExtraPerm(name, m, p)"
                        >{{ getPermName(p) }}</el-tag>
                        <el-dropdown v-if="name !== '管理人员'" trigger="click" @command="(cmd: string) => addExtraPerm(name, m, cmd)">
                          <el-button size="small" circle>+</el-button>
                          <template #dropdown>
                            <el-dropdown-menu>
                              <el-dropdown-item v-for="p in availablePerms" :key="p.key" :command="p.key" :disabled="(userPermMap[m]||[]).includes(p.key)">{{ p.label }}</el-dropdown-item>
                            </el-dropdown-menu>
                          </template>
                        </el-dropdown>
                      </div>
                      <el-button size="small" type="danger" link @click="removeMember(name, m)">删除</el-button>
                    </div>
                    <!-- 添加成员 -->
                    <div v-if="addMemberGroup[name]" class="member-row" style="gap:4px;">
                      <el-input v-model="addMemberName[name]" size="small" style="width:100px;" placeholder="账号" @keyup.enter="doAddMember(name)" />
                      <el-input v-model="addMemberPwd[name]" size="small" style="width:70px;" placeholder="密码" @keyup.enter="doAddMember(name)" />
                      <el-button size="small" type="primary" @click="doAddMember(name)">确定</el-button>
                      <el-button size="small" @click="cancelAddMember(name)">取消</el-button>
                    </div>
                    <el-button v-else size="small" @click="startAddMember(name)" style="margin-top:4px;">+ 添加成员</el-button>
                  </div>
                  <div style="display:flex;flex-wrap:wrap;gap:6px;">
                    <span style="font-size:12px;color:var(--text-muted);">组权限：</span>
                    <el-tag v-for="p in group.permissions" :key="p" size="small" effect="plain">{{ getPermName(p) }}</el-tag>
                  </div>
                </div>
                <div style="display:flex;gap:8px;flex-shrink:0;">
                  <el-button size="small" @click="openGroupDialog(name)">编辑</el-button>
                  <el-popconfirm title="确定删除此权限组？" @confirm="deleteGroup(name)">
                    <template #reference>
                      <el-button size="small" type="danger" link>删除</el-button>
                    </template>
                  </el-popconfirm>
                </div>
              </div>
            </div>
            <el-empty v-if="Object.keys(permGroups).length === 0" description="暂无权限组" />
          </div>
        </div>
      </div>

      <!-- 权限组编辑对话框 -->
      <el-dialog v-model="showGroupDialog" :title="editingGroupName ? '编辑权限组' : '新建权限组'" width="560px" destroy-on-close>
        <el-form :model="groupForm" label-width="100px">
          <el-form-item label="组名称">
            <el-input v-model="groupForm.name" :disabled="!!editingGroupName" placeholder="如：高级技师组" />
          </el-form-item>
          <el-form-item label="描述">
            <el-input v-model="groupForm.description" placeholder="简述该组的职责范围" />
          </el-form-item>
          <el-form-item label="权限列表">
            <el-checkbox-group v-model="groupForm.permissions">
              <div style="display:flex;flex-wrap:wrap;gap:8px;">
                <el-checkbox v-for="p in availablePerms" :key="p.key" :label="p.key" :value="p.key">{{ p.label }}</el-checkbox>
              </div>
            </el-checkbox-group>
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="showGroupDialog = false">取消</el-button>
          <el-button type="primary" @click="saveGroup">{{ editingGroupName ? '保存修改' : '创建' }}</el-button>
        </template>
      </el-dialog>

      <!-- 手册文件管理 -->
      <div v-if="activeMenu === 'manuals'" class="content-panel">
        <div class="glass-card inner-card">
          <div class="panel-toolbar card-header">
            <h4>手册文件管理</h4>
            <div class="toolbar-actions">
              <el-input v-model="manualSearch" size="small" placeholder="🔍 搜索手册..." style="width:180px;" clearable />
              <el-select v-model="manualCategory" size="small" placeholder="分类" style="width:160px;" clearable>
                <el-option label="机床设备维修手册" value="机床设备维修手册" />
                <el-option label="总装设备检修手册" value="总装设备检修手册" />
              </el-select>
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
            <div v-for="item in filteredManualList" :key="item.filename" class="glass-card data-card">
              <div class="card-info-group">
                <div class="info-item col-filename">
                  <span class="info-label">文件名</span>
                  <span class="info-value text-ellipsis">{{ item.filename }}</span>
                </div>
                <div class="info-item col-type">
                  <span class="info-label">类型</span>
                  <el-tag :type="item.type === 'PDF' ? 'primary' : 'success'" size="small">{{ item.type }}</el-tag>
                </div>
                <div class="info-item col-category">
                  <span class="info-label">分类</span>
                  <el-tag size="small" effect="plain">{{ item.category || '未分类' }}</el-tag>
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
                <el-button size="small" type="primary" link @click="viewManual(item.filename)">查看内容</el-button>
                <el-button v-if="item.type === 'PDF'" size="small" type="success" link @click="viewManual(item.filename, true)">PDF 预览</el-button>
                <el-button size="small" type="primary" link @click="syncSingle(item.filename)">单独同步</el-button>
                <el-popconfirm title="确定删除该手册文件吗？" @confirm="deleteManual(item.filename)">
                  <template #reference>
                    <el-button size="small" type="danger" link>删除</el-button>
                  </template>
                </el-popconfirm>
              </div>
            </div>
            <el-empty v-if="filteredManualList.length === 0 && !loadingManuals" description="暂无手册文件" />
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
                <el-button size="small" type="primary" link @click="viewManual(req.filename)">查看内容</el-button>
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
                  <span class="info-label">对话记录编号</span>
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
            <div class="monitor-item"><span class="label">PDF 原文件</span><span class="value">{{ systemStatus.knowledge_base?.pdf_files || 0 }}</span></div>
            <div class="monitor-item"><span class="label">文档切片数</span><span class="value">{{ systemStatus.knowledge_base?.document_chunks || 0 }}</span></div>
            <div class="monitor-item"><span class="label">向量索引</span><el-tag :type="getVectorStatusType(systemStatus.knowledge_base?.vector_index?.status)" size="small">{{ systemStatus.knowledge_base?.vector_index?.label || '未知' }}</el-tag></div>
            <div class="monitor-item"><span class="label">索引条目</span><span class="value">{{ systemStatus.knowledge_base?.vector_entries || 0 }}</span></div>
            <div class="monitor-item"><span class="label">更新时间</span><span class="value">{{ systemStatus.updated_at || '-' }}</span></div>
          </div>
          <div class="glass-card monitor-card">
            <div class="card-title">服务连通性</div>
            <div class="monitor-item"><span class="label">模型类型</span><span class="value">{{ systemStatus.services?.llm_model || '-' }}</span></div>
            <div class="monitor-item"><span class="label">数据库</span><el-tag :type="getVectorStatusType(systemStatus.services?.database?.status)" size="small">{{ systemStatus.services?.database?.label || '未知' }}</el-tag></div>
            <div class="monitor-item"><span class="label">数据目录</span><el-tag :type="systemStatus.services?.data_dir_exists ? 'success' : 'danger'" size="small">{{ systemStatus.services?.data_dir_exists ? '存在' : '缺失' }}</el-tag></div>
            <div class="monitor-item"><span class="label">知识目录</span><el-tag :type="systemStatus.services?.knowledge_dir_exists ? 'success' : 'danger'" size="small">{{ systemStatus.services?.knowledge_dir_exists ? '存在' : '缺失' }}</el-tag></div>
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
            <span v-if="llmTestResult.success" class="result-text">模型: {{ llmTestResult.model }} · 延迟: {{ llmTestResult.latency_ms }}ms · 响应: {{ llmTestResult.response }}</span>
            <span v-else class="result-text error">状态: {{ llmTestResult.error_type || llmTestResult.status }} · {{ llmTestResult.error }}</span>
          </div>
          <div v-else-if="systemStatus.monitor_error" class="test-result error-panel">
            <el-tag type="danger" effect="dark">连接异常</el-tag>
            <span class="result-text error">{{ systemStatus.monitor_error }}</span>
          </div>
          <div class="operation-grid">
            <div v-for="item in systemOperations" :key="item.label" class="operation-item">
              <span class="operation-label">{{ item.label }}</span>
              <span class="operation-value">{{ item.value }}</span>
              <span class="operation-time">{{ item.time || '无时间戳' }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 知识图谱(MySQL) -->
      <div v-if="activeMenu === 'knowledge_mysql'" class="content-panel" style="height:calc(100vh - 120px);">
        <KnowledgeGraph />
      </div>

      <!-- 知识图谱(Neo4j) -->
      <div v-if="activeMenu === 'knowledge_neo4j'" class="content-panel" style="height:calc(100vh - 120px);">
        <KnowledgeGraphNeo4j />
      </div>
    </el-main>

    <!-- 工单对话审计弹窗 -->
    <el-dialog v-model="showHistoryDialog" :title="`工单对话审计溯源 [单号: ${selectedOrder}]`" width="700px" destroy-on-close>
      <div class="admin-history-viewer">
        <el-empty v-if="!selectedChatHistory || selectedChatHistory.length === 0" description="该工单无对话记录" />
        <div v-for="msg in selectedChatHistory" :key="msg.id" :class="['history-msg-item', msg.role]">
          <div class="msg-sender">{{ msg.role === 'user' ? '操作员:' : '系统AI中枢:' }}</div>
          <div class="msg-text" v-html="renderMarkdown(msg.content)"></div>
        </div>
      </div>
    </el-dialog>

    <!-- 手册内容查看弹窗 -->
    <el-dialog v-model="showManualDialog" :title="`手册内容: ${viewingManual}`" width="900px" destroy-on-close top="3vh" @opened="initManualSearch" @closed="cleanupManualPreview">
      <el-alert
        v-if="manualDiagnosticMessage"
        :title="manualDiagnosticMessage"
        :type="manualDiagnosticType"
        show-icon
        :closable="false"
        style="margin-bottom:10px;"
      />
      <iframe v-if="manualPdfUrl" class="pdf-preview-frame" :src="manualPdfUrl"></iframe>
      <!-- 搜索栏 -->
      <div style="display:flex;gap:8px;align-items:center;margin-bottom:10px;" v-if="manualContent.length > 0 && !manualPdfUrl">
        <el-input v-model="manualSearchQuery" size="small" placeholder="🔍 在手册中搜索..." style="width:260px;" clearable @input="doManualSearch" @keydown.enter="nextMatch">
          <template #suffix>
            <span v-if="manualSearchQuery && manualMatchCount > 0" style="font-size:11px;color:var(--text-muted);white-space:nowrap;">{{ manualMatchIndex }}/{{ manualMatchCount }}</span>
          </template>
        </el-input>
        <el-button size="small" :disabled="manualMatchCount === 0" @click="prevMatch">◀</el-button>
        <el-button size="small" :disabled="manualMatchCount === 0" @click="nextMatch">▶</el-button>
        <span v-if="manualSearchQuery" style="font-size:12px;color:var(--text-muted);">{{ manualMatchCount > 0 ? `找到 ${manualMatchCount} 处匹配` : '未找到' }}</span>
      </div>
      <!-- 内容区 -->
      <div v-if="!manualPdfUrl" ref="manualContentRef" style="max-height:60vh;overflow-y:auto;white-space:pre-wrap;font-size:13px;line-height:1.8;color:var(--text-primary);background:var(--bg-dark);padding:16px;border-radius:8px;" v-loading="loadingManualContent" v-html="manualHighlighted">
      </div>
    </el-dialog>

    <!-- 同步前选择分类弹窗 -->
    <el-dialog v-model="showSyncCategoryDialog" title="选择分类后同步" width="400px">
      <p style="margin-bottom:12px;color:var(--text-secondary);">「{{ syncTargetFile }}」尚未同步，请先选择所属分类：</p>
      <el-select v-model="syncCategory" size="small" style="width:100%;">
        <el-option label="机床设备维修手册" value="机床设备维修手册" />
        <el-option label="总装设备检修手册" value="总装设备检修手册" />
      </el-select>
      <template #footer>
        <el-button @click="showSyncCategoryDialog = false">取消</el-button>
        <el-button type="primary" @click="confirmSyncCategory">确认并同步</el-button>
      </template>
    </el-dialog>
  </el-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, inject } from 'vue';
import { useRouter } from 'vue-router';
import { useChatStore } from '../stores/chat';
import { renderMarkdown } from '../utils/chatMarkdown';
import { DataAnalysis, List, SwitchButton, Folder, Monitor, User, DocumentChecked } from '@element-plus/icons-vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import KnowledgeGraph from '../components/KnowledgeGraph.vue';
import KnowledgeGraphNeo4j from '../components/KnowledgeGraphNeo4j.vue';

const router = useRouter();
const store = useChatStore();
const theme = inject<any>('theme');
const toggleTheme = inject<() => void>('toggleTheme', () => {});
const activeMenu = ref('users');
const showHistoryDialog = ref(false);
const selectedChatHistory = ref<any[]>([]);
const selectedOrder = ref('');

// 手册申请审核
const manualRequests = ref<any[]>([]);
const loadingRequests = ref(false);
const auditStatusFilter = ref('');

// ═══════════ 权限组管理 ═══════════
const permGroups = ref<Record<string, any>>({});
const userStatusMap = ref<Record<string, boolean>>({});
const userPermMap = ref<Record<string, string[]>>({});
const userExtraPermMap = ref<Record<string, string[]>>({});
const showGroupDialog = ref(false);
const editingGroupName = ref<string | null>(null);
const groupForm = ref({ name: '', description: '', permissions: [] as string[] });

const loadGroups = async () => {
  try {
    const res = await fetch(`${API_BASE}/user/groups`, { headers: { 'X-Admin-Token': ADMIN_TOKEN } });
    const data = await res.json();
    permGroups.value = data.groups || {};
  } catch (e) { console.error('loadGroups failed', e); }
};

const loadUsers = async () => {
  try {
    const res = await fetch(`${API_BASE}/user/list`, { headers: { 'X-Admin-Token': ADMIN_TOKEN } });
    const data = await res.json();
    for (const u of (data.users || [])) {
      userStatusMap.value[u.username] = u.is_online;
      userPermMap.value[u.username] = u.permissions || [];
      userExtraPermMap.value[u.username] = u.extra_permissions || [];
    }
  } catch (e) { console.error('loadUsers failed', e); }
};

const addExtraPerm = async (group: string, username: string, perm: string) => {
  const current = userExtraPermMap.value[username] || [];
  const newPerms = [...current, perm];
  try {
    const res = await fetch(`${API_BASE}/user/${encodeURIComponent(username)}/permissions`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', 'X-Admin-Token': ADMIN_TOKEN },
      body: JSON.stringify({ extra_permissions: newPerms }),
    });
    if (!res.ok) throw new Error();
    ElMessage.success(`已为 ${username} 追加权限`);
    await loadUsers();
  } catch { ElMessage.error('操作失败'); }
};

const removeExtraPerm = async (group: string, username: string, perm: string) => {
  const current = userExtraPermMap.value[username] || [];
  const newPerms = current.filter((p: string) => p !== perm);
  try {
    const res = await fetch(`${API_BASE}/user/${encodeURIComponent(username)}/permissions`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', 'X-Admin-Token': ADMIN_TOKEN },
      body: JSON.stringify({ extra_permissions: newPerms }),
    });
    if (!res.ok) throw new Error();
    ElMessage.success(`已移除 ${username} 的权限`);
    await loadUsers();
  } catch { ElMessage.error('操作失败'); }
};

const openGroupDialog = (name?: string) => {
  editingGroupName.value = name || null;
  if (name && permGroups.value[name]) {
    const g = permGroups.value[name];
    groupForm.value = { name, description: g.description, permissions: [...g.permissions] };
  } else {
    groupForm.value = { name: '', description: '', permissions: [] };
  }
  showGroupDialog.value = true;
};

const saveGroup = async () => {
  const { name, description, permissions } = groupForm.value;
  if (!name) return ElMessage.warning('请输入权限组名称');
  try {
    const method = editingGroupName.value ? 'PUT' : 'POST';
    const url = editingGroupName.value
      ? `${API_BASE}/user/groups/${encodeURIComponent(editingGroupName.value)}`
      : `${API_BASE}/user/groups`;
    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json', 'X-Admin-Token': ADMIN_TOKEN },
      body: JSON.stringify({ name, description, permissions }),
    });
    if (!res.ok) throw new Error();
    ElMessage.success(editingGroupName.value ? '权限组已更新' : '权限组已创建');
    showGroupDialog.value = false;
    await loadGroups();
  } catch { ElMessage.error('操作失败'); }
};

const deleteGroup = async (name: string) => {
  try {
    const res = await fetch(`${API_BASE}/user/groups/${encodeURIComponent(name)}`, {
      method: 'DELETE',
      headers: { 'X-Admin-Token': ADMIN_TOKEN },
    });
    if (!res.ok) throw new Error();
    ElMessage.success('权限组已删除');
    await loadGroups();
  } catch { ElMessage.error('删除失败'); }
};

// 成员管理状态
const addMemberGroup = ref<Record<string, boolean>>({});
const addMemberName = ref<Record<string, string>>({});
const addMemberPwd = ref<Record<string, string>>({});

const startAddMember = (group: string) => {
  addMemberGroup.value[group] = true;
  addMemberName.value[group] = '';
  addMemberPwd.value[group] = '123';
};
const cancelAddMember = (group: string) => { addMemberGroup.value[group] = false; };

const doAddMember = async (group: string) => {
  const username = addMemberName.value[group]?.trim();
  const password = addMemberPwd.value[group] || '123';
  if (!username) return ElMessage.warning('请输入账号');
  try {
    // 如果用户已存在，改为切换其权限组
    let res = await fetch(`${API_BASE}/user/add`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Admin-Token': ADMIN_TOKEN },
      body: JSON.stringify({ username, password, group }),
    });
    if (!res.ok) {
      // 用户已存在，尝试切换组
      res = await fetch(`${API_BASE}/user/${encodeURIComponent(username)}/group`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'X-Admin-Token': ADMIN_TOKEN },
        body: JSON.stringify({ group }),
      });
    }
    if (!res.ok) throw new Error();
    ElMessage.success(`已将 ${username} 加入 ${group}`);
    cancelAddMember(group);
    await loadUsers();
    await loadGroups();
    // 强制刷新确保 UI 更新
    setTimeout(() => loadGroups(), 300);
  } catch { ElMessage.error('操作失败'); }
};

const removeMember = async (group: string, username: string) => {
  try {
    const res = await fetch(`${API_BASE}/user/${encodeURIComponent(username)}`, {
      method: 'DELETE',
      headers: { 'X-Admin-Token': ADMIN_TOKEN },
    });
    if (!res.ok) throw new Error();
    ElMessage.success(`已移除 ${username}`);
    await loadUsers();
    await loadGroups();
    setTimeout(() => loadGroups(), 300);
  } catch { ElMessage.error('移除失败'); }
};

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

// 手册管理状态
const manualList = ref<any[]>([]);
const manualSearch = ref('');
const manualCategory = ref('');
const filteredManualList = computed(() => {
  let list = manualList.value;
  const q = manualSearch.value.trim().toLowerCase();
  if (q) list = list.filter(m => m.filename.toLowerCase().includes(q));
  if (manualCategory.value) list = list.filter(m => m.category === manualCategory.value);
  return list;
});
const loadingManuals = ref(false);
const showManualDialog = ref(false);
const viewingManual = ref('');
const manualContent = ref('');
const manualPdfUrl = ref('');
const manualDiagnosticMessage = ref('');
const manualDiagnosticType = ref<'success' | 'warning' | 'error' | 'info'>('info');
const loadingManualContent = ref(false);
const showSyncCategoryDialog = ref(false);
const syncTargetFile = ref('');
const syncCategory = ref('机床设备维修手册');
const manualSearchQuery = ref('');
const manualMatchCount = ref(0);
const manualMatchIndex = ref(0);
const manualHighlighted = ref('');
const manualContentRef = ref<HTMLElement | null>(null);
let manualSearchPositions: number[] = [];
let manualRawText = '';

const initManualSearch = () => {
  manualSearchQuery.value = '';
  manualMatchCount.value = 0;
  manualMatchIndex.value = 0;
  manualHighlighted.value = escapeHtml(manualContent.value);
  manualRawText = manualContent.value;
  manualSearchPositions = [];
};

const escapeHtml = (s: string) => s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

const doManualSearch = () => {
  const q = manualSearchQuery.value.trim().toLowerCase();
  manualMatchIndex.value = 0;
  manualSearchPositions = [];
  if (!q) {
    manualHighlighted.value = escapeHtml(manualRawText);
    manualMatchCount.value = 0;
    return;
  }
  const lower = manualRawText.toLowerCase();
  let pos = 0;
  while ((pos = lower.indexOf(q, pos)) !== -1) {
    manualSearchPositions.push(pos);
    pos += q.length;
  }
  manualMatchCount.value = manualSearchPositions.length;
  if (manualSearchPositions.length > 0) {
    manualMatchIndex.value = 1;
    highlightCurrent();
  } else {
    manualHighlighted.value = escapeHtml(manualRawText);
  }
};

const highlightCurrent = () => {
  if (manualSearchPositions.length === 0) {
    manualHighlighted.value = escapeHtml(manualRawText);
    return;
  }
  const q = manualSearchQuery.value;
  const idx = manualMatchIndex.value - 1;
  if (idx < 0 || idx >= manualSearchPositions.length) return;
  const pos = manualSearchPositions[idx];
  const before = escapeHtml(manualRawText.slice(0, pos));
  const match = '<mark style="background:#00b4a0;color:#fff;padding:1px 3px;border-radius:3px;">' + escapeHtml(manualRawText.slice(pos, pos + q.length)) + '</mark>';
  const after = escapeHtml(manualRawText.slice(pos + q.length));
  manualHighlighted.value = before + match + after;
  // scroll to match
  setTimeout(() => {
    const el = manualContentRef.value;
    if (el) {
      const mark = el.querySelector('mark');
      if (mark) mark.scrollIntoView({ block: 'center', behavior: 'smooth' });
    }
  }, 50);
};

const prevMatch = () => {
  if (manualSearchPositions.length === 0) return;
  manualMatchIndex.value = manualMatchIndex.value <= 1 ? manualSearchPositions.length : manualMatchIndex.value - 1;
  highlightCurrent();
};

const nextMatch = () => {
  if (manualSearchPositions.length === 0) return;
  manualMatchIndex.value = manualMatchIndex.value >= manualSearchPositions.length ? 1 : manualMatchIndex.value + 1;
  highlightCurrent();
};

// 系统监控状态
const systemStatus = ref<any>({});
const llmTestResult = ref<any>(null);
const lastGoodSystemStatus = ref<any>({});

const API_BASE = import.meta.env.VITE_API_BASE || '';
const ADMIN_TOKEN = 'admin-change-me';

const pageTitle = computed(() => {
  const map: Record<string, string> = {
    users: '组织架构与权限管控 (RBAC & Permission Groups)',
    manuals: '手册文件在线管理 (Manual Management)',
    upload_audit: '手册录入申请审核',
    records: '全局业务闭环审计 (Audit Logs)',
    monitor: '系统运维监控面板 (System Monitor)',
    knowledge_mysql: '知识图谱 (MySQL)',
    knowledge_neo4j: '知识图谱 (Neo4j)',
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

const getVectorStatusType = (status: string) => {
  if (status === 'healthy' || status === 'exists') return 'success';
  if (status === 'missing' || status === 'unavailable' || status === 'connection_failed') return 'danger';
  return 'warning';
};

const systemOperations = computed(() => {
  const operations = systemStatus.value.operations || {};
  return [
    { label: '最近知识库同步', value: operations.last_sync_result || '暂无同步记录', time: operations.last_sync_at },
    { label: '最近手册变更', value: operations.last_manual_change || '暂无变更记录', time: operations.last_manual_change_at },
    { label: '知识文件状态', value: operations.knowledge_file || '未检测', time: operations.knowledge_file_updated_at },
    { label: '图谱文件状态', value: operations.graph_file || '未检测', time: operations.graph_file_updated_at },
  ];
});

const handleMenuSelect = (index: string) => {
  if (index === 'logout') return;
  activeMenu.value = index;
  if (index === 'users') { loadGroups(); loadUsers(); }
  if (index === 'manuals') loadManualList();
  if (index === 'monitor') loadSystemStatus();
  if (index === 'upload_audit') loadManualRequests();
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

const cleanupManualPreview = () => {
  if (manualPdfUrl.value) URL.revokeObjectURL(manualPdfUrl.value);
  manualPdfUrl.value = '';
  manualDiagnosticMessage.value = '';
};

const viewManual = async (filename: string, preferPdfPreview = false) => {
  cleanupManualPreview();
  viewingManual.value = filename;
  showManualDialog.value = true;
  loadingManualContent.value = true;
  manualContent.value = '';
  try {
    const isPdf = filename.toLowerCase().endsWith('.pdf');
    if (isPdf) {
      const diagRes = await fetch(`${API_BASE}/knowledge/manuals/${encodeURIComponent(filename)}/diagnostics`, {
        headers: { 'X-Admin-Token': ADMIN_TOKEN }
      });
      const diag = await diagRes.json();
      manualDiagnosticMessage.value = diag.message || '';
      manualDiagnosticType.value = diag.preview_status === 'available'
        ? (diag.parse_status === 'scanned' ? 'warning' : 'success')
        : 'error';
      if (preferPdfPreview || diag.parse_status !== 'parsed') {
        const rawRes = await fetch(`${API_BASE}/knowledge/manuals/${encodeURIComponent(filename)}/raw`, {
          headers: { 'X-Admin-Token': ADMIN_TOKEN }
        });
        if (!rawRes.ok) {
          const rawErr = await rawRes.json().catch(() => ({}));
          throw new Error(rawErr.detail || diag.message || 'PDF 下载失败');
        }
        const blob = await rawRes.blob();
        manualPdfUrl.value = URL.createObjectURL(blob);
        manualContent.value = '';
        manualHighlighted.value = '';
        manualRawText = '';
        return;
      }
    }
    const res = await fetch(`${API_BASE}/knowledge/manuals/${encodeURIComponent(filename)}/content`, {
      headers: { 'X-Admin-Token': ADMIN_TOKEN }
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || '加载失败');
    manualContent.value = data.content || '[无内容]';
    manualHighlighted.value = escapeHtml(manualContent.value);
    manualRawText = manualContent.value;
  } catch (e: any) {
    manualContent.value = `[加载失败] ${e?.message || '无法读取该手册内容'}`;
    manualHighlighted.value = escapeHtml(manualContent.value);
    manualRawText = manualContent.value;
  } finally {
    loadingManualContent.value = false;
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
  const item = manualList.value.find((m: any) => m.filename === filename);
  if (!item) return;
  // 未同步的手册需先选择分类
  if (item.status === '待同步') {
    syncTargetFile.value = filename;
    showSyncCategoryDialog.value = true;
    return;
  }
  doSyncSingle(filename);
};

const doSyncSingle = async (filename: string) => {
  const idx = manualList.value.findIndex((m: any) => m.filename === filename);
  if (idx >= 0) manualList.value[idx] = { ...manualList.value[idx], status: '同步中' };

  try {
    const res = await fetch(`${API_BASE}/knowledge/sync/${encodeURIComponent(filename)}`, {
      method: 'POST',
      headers: { 'X-Admin-Token': ADMIN_TOKEN }
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || '同步失败');
    ElMessage.success(`${filename} 已同步，新增 ${data.added_docs || 0} 条切片`);
    await loadManualList();
  } catch (e: any) {
    if (idx >= 0) manualList.value[idx] = { ...manualList.value[idx], status: '同步失败' };
    ElMessage.error(e?.message || '同步失败');
  }
};

const confirmSyncCategory = async () => {
  const filename = syncTargetFile.value;
  if (!filename) return;
  // 将分类写入后端（通过 update category 接口）
  try {
    await fetch(`${API_BASE}/knowledge/manuals/${encodeURIComponent(filename)}/category`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', 'X-Admin-Token': ADMIN_TOKEN },
      body: JSON.stringify({ category: syncCategory.value }),
    });
  } catch { /* ignore */ }
  showSyncCategoryDialog.value = false;
  doSyncSingle(filename);
};

const syncAllManuals = async () => {
  manualList.value = manualList.value.map((m: any) => ({ ...m, status: '同步中' }));
  try {
    const res = await fetch(`${API_BASE}/knowledge/sync`, {
      method: 'POST',
      headers: { 'X-Admin-Token': ADMIN_TOKEN }
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || '全量同步失败');
    ElMessage.success(`全量同步完成，共 ${data.result?.document_count || 0} 条文档`);
    await loadManualList();
  } catch (e: any) {
    ElMessage.error(e?.message || '全量同步失败');
    await loadManualList();
  }
};

// ==================== 系统监控 ====================
const loadSystemStatus = async () => {
  try {
    const res = await fetch(`${API_BASE}/monitor/status`, {
      headers: { 'X-Admin-Token': ADMIN_TOKEN }
    });
    if (!res.ok) throw new Error('获取系统状态失败');
    const data = await res.json();
    systemStatus.value = data;
    lastGoodSystemStatus.value = data;
  } catch (e: any) {
    systemStatus.value = {
      ...lastGoodSystemStatus.value,
      monitor_error: e?.message || '系统状态接口连接失败',
    };
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
  loadGroups();
  loadUsers();
});
</script>

<style scoped>
.admin-layout {
  height: 100vh;
  background: var(--bg-darker);
  overflow: hidden;
}
.admin-sidebar {
  margin: 15px;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  background: var(--bg-glass);
  border: 1px solid var(--border-glass);
}
.sidebar-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 25px 20px;
  color: #00c8b4;
  border-bottom: 1px solid var(--border-glass);
}
.sidebar-logo h2 {
  margin: 0;
  font-size: 18px;
  background: linear-gradient(135deg, #00c8b4, #38bdf8);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text;
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
  background: rgba(0, 200, 180, 0.12);
  border: 1px solid rgba(0, 200, 180, 0.2);
  color: #00c8b4 !important;
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
  color: var(--text-primary);
  font-size: 16px;
  font-weight: 500;
}
.content-panel {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}
.glass-card {
  background: var(--bg-glass);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid var(--border-glass);
  box-shadow: var(--shadow-glass);
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
  border-bottom: 1px solid var(--border-glass);
  padding-bottom: 12px;
  margin-bottom: 20px;
  flex-shrink: 0;
}
.card-header h4 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
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
.member-name {
  font-weight: 600;
  color: var(--text-primary);
  font-family: 'Cascadia Code', 'Fira Code', ui-monospace, monospace;
}
.member-row {
  display: flex;
  align-items: center;
  padding: 6px 10px;
  margin-bottom: 4px;
  background: var(--bg-glass);
  border: 1px solid var(--border-glass);
  border-radius: 8px;
  font-size: 13px;
  gap: 6px;
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
  font-size: 14px;
  font-weight: 500;
  text-align: left;
  line-height: 1.2;
  color: var(--text-primary);
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
.col-category {
  flex: 0 0 150px;
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
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-glass);
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
  color: var(--text-secondary);
  font-size: 13px;
  text-align: left;
}
.monitor-item .value {
  color: var(--text-primary);
  font-weight: 600;
  text-align: left;
}
.monitor-item .value.highlight {
  font-size: 18px;
  font-weight: bold;
  color: #60a5fa;
}
.test-result {
  background: var(--bg-card);
  border: 1px solid var(--border-glass);
  border-radius: 8px;
  padding: 12px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}
.error-panel {
  border-color: rgba(239, 68, 68, 0.35);
}
.result-text {
  font-size: 13px;
  color: var(--text-secondary);
}
.result-text.error {
  color: var(--danger);
}
.pdf-preview-frame {
  width: 100%;
  height: 72vh;
  border: 1px solid var(--border-glass);
  border-radius: 8px;
  background: var(--bg-dark);
}
.operation-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}
.operation-item {
  min-height: 74px;
  padding: 12px 14px;
  border-radius: 8px;
  background: var(--bg-card);
  border: 1px solid var(--border-glass);
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.operation-label {
  font-size: 12px;
  color: var(--text-secondary);
}
.operation-value {
  font-size: 14px;
  color: var(--text-primary);
  font-weight: 600;
}
.operation-time {
  font-size: 12px;
  color: var(--text-muted);
}
.admin-history-viewer {
  max-height: 450px;
  overflow-y: auto;
  padding: 15px;
  background: var(--bg-dark);
  border-radius: 8px;
}
.history-msg-item {
  margin-bottom: 15px;
  padding: 12px 16px;
  border-radius: 8px;
}
.history-msg-item.user {
  background: var(--bg-glass);
  border: 1px solid var(--border-glass);
}
.history-msg-item.assistant {
  background: var(--bg-card);
  border: 1px solid var(--border-glass);
}
.msg-sender {
  font-size: 12px;
  font-weight: bold;
  color: var(--primary-color);
  margin-bottom: 6px;
}
.msg-text {
  font-size: 14px;
  color: var(--text-primary);
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
