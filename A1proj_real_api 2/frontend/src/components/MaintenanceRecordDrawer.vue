<template>
  <el-drawer
    v-model="visible"
    direction="rtl"
    size="720px"
    class="dark-drawer"
    :with-header="false"
    append-to-body
    @close="handleClose"
  >
    <div class="drawer-inner">
      <div class="drawer-header">
        <h3 class="drawer-title">🔧 维修总结</h3>
        <el-button type="primary" size="small" @click="openCreate">+ 新增记录</el-button>
      </div>

      <!-- 记录列表 -->
      <div class="records-section">
        <el-table
          :data="records"
          style="width: 100%"
          size="small"
          v-loading="loading"
          empty-text="暂无维修记录"
          row-class-name="dark-row"
        >
          <el-table-column prop="fault_type" label="故障类型" min-width="100" show-overflow-tooltip />
          <el-table-column prop="fault_resolved" label="解决" width="60">
            <template #default="{ row }">
              <el-tag :type="row.fault_resolved === '是' ? 'success' : 'danger'" size="small" effect="dark">
                {{ row.fault_resolved }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="synced" label="同步" width="75">
            <template #default="{ row }">
              <el-tag :type="row.synced === '已同步' ? 'success' : row.synced === '待确认' ? 'warning' : 'info'" size="small" effect="dark">
                {{ row.synced || '未同步' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="160" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" link size="small" @click="openView(row)">查看</el-button>
              <el-button type="warning" link size="small" @click="openEdit(row)">修改</el-button>
              <el-button type="danger" link size="small" @click="confirmDelete(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="pagination-row">
          <el-pagination
            v-model:current-page="page"
            :page-size="pageSize"
            :total="total"
            layout="prev, pager, next"
            small
            @current-change="fetchRecords"
          />
          <el-button type="success" plain size="small" @click="exportCsv">📥 导出CSV</el-button>
        </div>
      </div>
    </div>

    <!-- 新增 / 修改 / 查看 弹窗 -->
    <el-dialog
      v-model="showFormDialog"
      :title="formMode === 'view' ? '查看维修记录' : formMode === 'edit' ? '修改维修记录' : '新增维修记录'"
      width="600px"
      destroy-on-close
      class="dark-dialog"
    >
      <el-form
        ref="formRef"
        :model="form"
        label-width="100px"
        :disabled="formMode === 'view'"
      >
        <el-form-item label="故障类型">
          <el-input v-model="form.fault_type" placeholder="如：主轴异常" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="开始时间">
              <el-input v-model="form.repair_start_time" placeholder="2026-08-04 09:00" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="结束时间">
              <el-input v-model="form.repair_end_time" placeholder="2026-08-04 10:30" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="维修人员">
          <el-input v-model="form.technician" :placeholder="store.username || '维修员'" />
        </el-form-item>
        <el-form-item label="故障描述">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="描述故障现象" />
        </el-form-item>
        <el-form-item label="故障原因">
          <el-input v-model="form.fault_cause" type="textarea" :rows="5" placeholder="分析故障根本原因" />
        </el-form-item>
        <el-form-item label="维修方案">
          <el-input v-model="form.solution" type="textarea" :rows="6" placeholder="记录维修方案与总结" />
        </el-form-item>
        <el-form-item label="是否解决">
          <el-select v-model="form.fault_resolved" style="width: 100%">
            <el-option label="是" value="是" />
            <el-option label="否" value="否" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showFormDialog = false">{{ formMode === 'view' ? '关闭' : '取消' }}</el-button>
        <el-button v-if="formMode !== 'view'" type="primary" :loading="submitting" @click="handleSubmit">
          {{ formMode === 'edit' ? '保存修改' : '提交记录' }}
        </el-button>
      </template>
    </el-dialog>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useChatStore } from '../stores/chat'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ (e: 'update:modelValue', v: boolean): void }>()

const store = useChatStore()
const API_BASE = import.meta.env.VITE_API_BASE || ''

const visible = ref(props.modelValue)

watch(() => props.modelValue, (val) => {
  visible.value = val
  if (val) fetchRecords()
})
watch(visible, (val) => { if (!val) emit('update:modelValue', false) })
const loading = ref(false)
const submitting = ref(false)
const showFormDialog = ref(false)
const formMode = ref<'view' | 'edit' | 'create'>('create')
const editingRecordId = ref('')

const records = ref<any[]>([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

const formRef = ref()
const form = reactive({
  device_model: '',
  fault_type: '',
  repair_date: '',
  technician: '',
  description: '',
  solution: '',
  parts_replaced: '',
  status: '已完成',
  repair_start_time: '',
  repair_end_time: '',
  repair_duration: '',
  fault_cause: '',
  fault_resolved: '是',
})

function resetForm() {
  form.device_model = ''
  form.fault_type = ''
  form.repair_date = ''
  form.technician = store.username || ''
  form.description = ''
  form.solution = ''
  form.parts_replaced = ''
  form.status = '已完成'
  form.repair_start_time = ''
  form.repair_end_time = ''
  form.repair_duration = ''
  form.fault_cause = ''
  form.fault_resolved = '是'
}

async function fetchRecords() {
  loading.value = true
  try {
    const res = await fetch(`${API_BASE}/maintenance/records?user_id=${encodeURIComponent(store.username)}&page=${page.value}&page_size=${pageSize.value}`, { credentials: 'include' })
    const data = await res.json()
    records.value = (data.records || []).filter((r: any) =>
      (r.fault_type && r.fault_type.trim()) || (r.description && r.description.trim())
    );
    total.value = data.total || 0;
  } catch {
    ElMessage.error('加载记录失败')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  resetForm()
  formMode.value = 'create'
  editingRecordId.value = ''
  showFormDialog.value = true
}

function openView(row: any) {
  Object.assign(form, {
    device_model: row.device_model || '',
    fault_type: row.fault_type || '',
    repair_date: row.repair_date || '',
    technician: row.technician || '',
    description: row.description || '',
    solution: row.solution || '',
    parts_replaced: row.parts_replaced || '',
    status: row.status || '已完成',
    repair_start_time: row.repair_start_time || '',
    repair_end_time: row.repair_end_time || '',
    repair_duration: row.repair_duration || '',
    fault_cause: row.fault_cause || '',
    fault_resolved: row.fault_resolved || '是',
  })
  editingRecordId.value = row.record_id
  formMode.value = 'view'
  showFormDialog.value = true
}

function openEdit(row: any) {
  openView(row)
  formMode.value = 'edit'
}

async function handleSubmit() {
  submitting.value = true
  try {
    const body: any = { ...form }
    if (formMode.value === 'create') {
      const res = await fetch(`${API_BASE}/maintenance/records?user_id=${encodeURIComponent(store.username)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(body),
      })
      const data = await res.json()
      if (res.ok) {
        ElMessage.success('记录已创建')
        showFormDialog.value = false
        fetchRecords()
      } else {
        ElMessage.error(data.detail || '创建失败')
      }
    } else {
      const res = await fetch(`${API_BASE}/maintenance/records/${editingRecordId.value}?user_id=${encodeURIComponent(store.username)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(body),
      })
      const data = await res.json()
      if (res.ok) {
        ElMessage.success('记录已更新')
        showFormDialog.value = false
        fetchRecords()
      } else {
        ElMessage.error(data.detail || '更新失败')
      }
    }
  } catch (e: any) {
    ElMessage.error('操作失败: ' + (e?.message || e?.toString() || '未知错误'))
  } finally {
    submitting.value = false
  }
}

async function confirmDelete(row: any) {
  try {
    await ElMessageBox.confirm(`确定删除设备型号为「${row.device_model}」的维修记录吗？`, '确认删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    const res = await fetch(`${API_BASE}/maintenance/records/${row.record_id}?user_id=${encodeURIComponent(store.username)}`, {
      method: 'DELETE',
      credentials: 'include',
    })
    if (res.ok) {
      ElMessage.success('记录已删除')
      fetchRecords()
    } else {
      ElMessage.error('删除失败')
    }
  } catch {
    // 用户取消
  }
}

function exportCsv() {
  window.open(`${API_BASE}/maintenance/records/export?user_id=${encodeURIComponent(store.username)}`, '_blank')
}

function handleClose() {
  emit('update:modelValue', false)
}
</script>

<style scoped>
.drawer-inner {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  height: 100%;
  box-sizing: border-box;
}

.drawer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.drawer-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.records-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.pagination-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>

<style>
.dark-drawer .el-drawer__body {
  background: var(--bg-dark) !important;
}

.dark-dialog {
  --el-dialog-bg-color: var(--bg-dark);
}

.dark-row {
  background: var(--bg-soft) !important;
}
</style>
