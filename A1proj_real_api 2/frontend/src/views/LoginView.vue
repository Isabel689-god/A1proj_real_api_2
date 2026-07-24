<template>
  <div class="login-container">
    <ParticleBackground />

    <div class="login-card glass-card">
      <div class="login-header">
        <div class="logo">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2L2 7l10 5 10-5-10-5z" />
            <path d="M2 17l10 5 10-5" />
            <path d="M2 12l10 5 10-5" />
          </svg>
        </div>
        <h1>多模态设备检修中枢</h1>
        <p>Industrial Intelligence Maintenance System</p>
      </div>

      <el-form
        ref="loginFormRef"
        :model="loginForm"
        :rules="loginRules"
        class="login-form"
        @submit.prevent="handleLogin"
      >
        <el-form-item prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="请输入系统账号 (例如: admin / senior_01)"
            prefix-icon="User"
            size="large"
            class="login-input"
          />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="请输入密码"
            prefix-icon="Lock"
            size="large"
            class="login-input"
            @keyup.enter="handleLogin"
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            class="login-btn neon-btn"
            :loading="loading"
            @click="handleLogin"
          >
            鉴权登入中枢
          </el-button>
        </el-form-item>
      </el-form>

      <div class="login-footer">
        <p>© 2026 智能设备检修系统 | 工业4.0解决方案</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage, ElForm } from 'element-plus';
import { User, Lock } from '@element-plus/icons-vue';
import ParticleBackground from '../components/ParticleBackground.vue';
import { useChatStore } from '../stores/chat';

const router = useRouter();
const store = useChatStore();
const loginFormRef = ref<InstanceType<typeof ElForm>>();
const loading = ref(false);

const loginForm = reactive({
  username: '',
  password: ''
});

const loginRules = reactive({
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
});

const handleLogin = async () => {
  if (!loginFormRef.value) return;
  try {
    await loginFormRef.value.validate();
    loading.value = true;

    try {
      const API_BASE = import.meta.env.VITE_API_BASE ?? '';
      const response = await fetch(`${API_BASE}/user/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: loginForm.username,
          password: loginForm.password
        })
      });

      const data = await response.json();

      if (response.ok && data.success) {
        store.setUserLoggedIn(true, data.user.role, data.user.username, data.user.permissions);
        ElMessage.success(`欢迎回来，${data.user.role}！正在载入工作台...`);
        router.push(data.user.role === 'admin' ? '/admin' : '/chat');
      } else {
        ElMessage.error(data.detail || '用户名或密码错误');
      }
    } catch (err) {
      ElMessage.error('网络请求失败，请检查后端服务是否启动');
    }

    loading.value = false;
  } catch (error) {
    console.error('表单校验失败:', error);
  }
};
</script>

<style scoped>
.login-container {
  width: 100vw; height: 100vh;
  display: flex;
  align-items: center; justify-content: center;
  position: relative;
}

.login-card {
  width: 440px;
  padding: 50px 45px;
  position: relative;
  z-index: 10;
  background: rgba(15, 23, 42, 0.7);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(14, 165, 233, 0.4);
  border-radius: 20px;
  box-shadow:
    0 20px 50px rgba(0, 0, 0, 0.5),
    0 0 30px rgba(14, 165, 233, 0.2),
    inset 0 0 0 1px rgba(255, 255, 255, 0.05);
}

.login-header { text-align: center; margin-bottom: 40px; }
.logo {
  width: 80px; height: 80px; margin: 0 auto 20px;
  color: var(--primary-color);
  animation: pulse 2.5s infinite;
}
@keyframes pulse {
  0%, 100% { filter: drop-shadow(0 0 10px rgba(14, 165, 233, 0.6)); }
  50% { filter: drop-shadow(0 0 25px rgba(14, 165, 233, 1)); transform: scale(1.02); }
}

.login-header h1 {
  font-size: 26px;
  font-weight: 700; margin-bottom: 8px;
  background: linear-gradient(90deg, #38bdf8, #22d3ee);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text; letter-spacing: 2px;
}
.login-header p {
  color: var(--text-secondary); font-size: 13px; letter-spacing: 1px;
}

.login-form { margin-bottom: 30px; }
.login-input {
  background: rgba(255, 255, 255, 0.95) !important;
  border: 1px solid var(--border-glass); border-radius: 8px;
  height: 52px;
  transition: all 0.3s ease;
}
.login-input:focus-within {
  border-color: var(--primary-color); box-shadow: 0 0 15px rgba(14, 165, 233, 0.4);
}
.login-input :deep(.el-input__inner) {
  background: transparent !important; color: #1d2129 !important; font-weight: 500;
}
.login-input :deep(.el-input__inner::placeholder) { color: #86909c !important; }
.login-input :deep(.el-input__prefix) { color: #4e5969 !important; }

.login-btn {
  width: 100%; height: 52px; font-size: 16px;
  font-weight: bold; letter-spacing: 2px;
  background: linear-gradient(90deg, #0284c7, #38bdf8);
  border: none; border-radius: 8px;
}

.login-footer { text-align: center; color: rgba(148, 163, 184, 0.8); font-size: 12px; }
</style>