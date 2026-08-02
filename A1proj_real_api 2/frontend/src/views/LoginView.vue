<template>
  <div class="login-container">
    <!-- 环境光晕 -->
    <div class="ambient-orb orb-1"></div>
    <div class="ambient-orb orb-2"></div>
    <div class="ambient-orb orb-3"></div>

    <ParticleBackground />

    <button class="login-theme-toggle" @click="toggleTheme" :title="theme === 'dark' ? '切换浅色模式' : '切换深色模式'">
      {{ theme === 'dark' ? '☀' : '☾' }}
    </button>

    <div class="login-card">
      <!-- 卡片顶部发光边框 -->
      <div class="card-glow-top"></div>

      <div class="login-header">
        <div class="logo-wrapper">
          <div class="logo-ring"></div>
          <svg class="logo-icon" viewBox="0 0 24 24" fill="none">
            <path d="M12 2L2 7l10 5 10-5-10-5z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
            <path d="M2 17l10 5 10-5" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
            <path d="M2 12l10 5 10-5" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
          </svg>
          <div class="logo-pulse"></div>
        </div>

        <h1 class="title-main">匠芯智修</h1>
        <p class="title-sub">工业设备智能检修中枢</p>
        <div class="title-divider">
          <span class="divider-line"></span>
          <span class="divider-dot"></span>
          <span class="divider-line"></span>
        </div>
      </div>

      <el-form
        ref="loginFormRef"
        :model="loginForm"
        :rules="loginRules"
        class="login-form"
        @submit.prevent="handleLogin"
      >
        <div class="input-group">
          <label class="input-label">系统账号</label>
          <el-input
            v-model="loginForm.username"
            placeholder="admin / senior_01 / employee_01"
            size="large"
            class="custom-input"
          >
            <template #prefix>
              <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                <circle cx="12" cy="7" r="4"/>
              </svg>
            </template>
          </el-input>
        </div>

        <div class="input-group">
          <label class="input-label">访问密码</label>
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="请输入密码"
            size="large"
            class="custom-input"
            show-password
            @keyup.enter="handleLogin"
          >
            <template #prefix>
              <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
              </svg>
            </template>
          </el-input>
        </div>

        <el-button
          class="login-btn"
          :loading="loading"
          @click="handleLogin"
        >
          <span v-if="!loading" class="btn-content">
            <span class="btn-text">进入系统</span>
            <svg class="btn-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M5 12h14M12 5l7 7-7 7"/>
            </svg>
          </span>
        </el-button>
      </el-form>

      <div class="login-footer">
        <span class="footer-dot"></span>
        <span>工业4.0智能解决方案 · 2026</span>
        <span class="footer-dot"></span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, inject } from 'vue';
import type { Ref } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage, ElForm } from 'element-plus';
import ParticleBackground from '../components/ParticleBackground.vue';
import { useChatStore } from '../stores/chat';

const router = useRouter();
const store = useChatStore();
const theme = inject<Ref<'dark' | 'light'>>('theme', ref<'dark' | 'light'>('dark'));
const toggleTheme = inject<() => void>('toggleTheme', () => {});
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
        store.setUserLoggedIn(true, data.user.group, data.user.username, data.user.permissions);
        ElMessage.success(`欢迎回来，${data.user.username}！正在载入工作台...`);
        router.push(data.user.group === '管理组' ? '/admin' : '/chat');
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
/* ==================== 容器 & 环境光 ==================== */
.login-container {
  --login-card-bg: rgba(8, 16, 32, 0.78);
  --login-card-border: rgba(0, 200, 180, 0.28);
  --login-input-bg: rgba(10, 18, 32, 0.72);
  --login-shadow: 0 0 80px rgba(0, 180, 160, 0.08), 0 20px 60px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.03);
  --login-subtitle: #cbd5e1;
  --login-muted: #94a3b8;
  --login-footer: #94a3b8;
  width: 100vw; height: 100vh;
  display: flex;
  align-items: center; justify-content: center;
  position: relative;
  overflow: hidden;
  background: radial-gradient(ellipse at 30% 20%, var(--bg-dark) 0%, var(--bg-darker) 60%, var(--bg-darker) 100%);
}

:global([data-theme="light"]) .login-container {
  --login-card-bg: rgba(255, 255, 255, 0.9);
  --login-card-border: rgba(0, 150, 136, 0.22);
  --login-input-bg: rgba(255, 255, 255, 0.88);
  --login-shadow: 0 18px 54px rgba(15, 23, 42, 0.12), inset 0 1px 0 rgba(255, 255, 255, 0.8);
  --login-subtitle: #334155;
  --login-muted: #475569;
  --login-footer: #64748b;
  background: radial-gradient(ellipse at 30% 20%, #f8fafc 0%, #e0f2fe 50%, #f1f5f9 100%);
}

:global([data-theme="light"] .login-container .particle-canvas) {
  display: none !important;
  opacity: 0 !important;
  background: transparent !important;
}

:global([data-theme="light"] .login-container .ambient-orb) {
  opacity: 0.08 !important;
  filter: blur(90px);
}

:global([data-theme="light"] .login-card) {
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
}

:global([data-theme="light"] .login-card .title-main) {
  background: linear-gradient(135deg, #0f766e 0%, #0f172a 52%, #0e7490 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

:global([data-theme="light"] .login-card .title-sub),
:global([data-theme="light"] .login-card .input-label),
:global([data-theme="light"] .login-card .login-footer),
:global([data-theme="light"] .login-card .input-icon),
:global([data-theme="light"] .login-card .el-input__prefix),
:global([data-theme="light"] .login-card .el-input__suffix) {
  color: #334155 !important;
}

:global([data-theme="light"] .login-card .custom-input .el-input__inner) {
  color: #0f172a !important;
  -webkit-text-fill-color: #0f172a !important;
}

:global([data-theme="light"] .login-card .custom-input .el-input__inner::placeholder) {
  color: #64748b !important;
  -webkit-text-fill-color: #64748b !important;
}

:global([data-theme="light"] .login-card .footer-dot),
:global([data-theme="light"] .login-card .divider-dot) {
  background: #0f766e;
  box-shadow: none;
}

:global([data-theme="light"] .login-card .divider-line) {
  background: linear-gradient(90deg, transparent, rgba(15, 118, 110, 0.45), transparent);
}

.login-theme-toggle {
  position: fixed;
  top: 22px;
  right: 24px;
  z-index: 4;
  width: 38px;
  height: 38px;
  border-radius: 50%;
  border: 1px solid var(--login-card-border);
  background: var(--login-card-bg);
  color: var(--primary-color);
  box-shadow: var(--login-shadow);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
}

.login-theme-toggle:hover {
  border-color: var(--primary-color);
  box-shadow: var(--shadow-neon-sm);
}

.ambient-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(120px);
  opacity: 0.35;
  pointer-events: none;
  z-index: 0;
}

.orb-1 {
  width: 600px; height: 600px;
  background: radial-gradient(circle, rgba(0, 200, 180, 0.25), transparent 70%);
  top: -200px; left: -150px;
  animation: orbFloat1 12s ease-in-out infinite;
}

.orb-2 {
  width: 500px; height: 500px;
  background: radial-gradient(circle, rgba(50, 120, 220, 0.2), transparent 70%);
  bottom: -180px; right: -120px;
  animation: orbFloat2 15s ease-in-out infinite;
}

.orb-3 {
  width: 350px; height: 350px;
  background: radial-gradient(circle, rgba(100, 80, 200, 0.18), transparent 70%);
  top: 45%; left: 55%;
  animation: orbFloat3 18s ease-in-out infinite;
}

@keyframes orbFloat1 {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(60px, 40px) scale(1.15); }
  66% { transform: translate(-30px, -20px) scale(0.9); }
}

@keyframes orbFloat2 {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(-50px, -30px) scale(1.1); }
  66% { transform: translate(40px, 20px) scale(0.95); }
}

@keyframes orbFloat3 {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(-40px, 50px) scale(1.2); }
}

/* ==================== 登录卡片 ==================== */
.login-card {
  width: 420px;
  padding: 48px 44px 40px;
  position: relative;
  z-index: 10;
  background: var(--login-card-bg);
  backdrop-filter: blur(32px);
  -webkit-backdrop-filter: blur(32px);
  border: 1px solid var(--login-card-border);
  border-radius: 24px;
  box-shadow: var(--login-shadow);
  transition: border-color 0.4s ease, box-shadow 0.4s ease;
}

.login-card:hover {
  border-color: rgba(0, 200, 180, 0.45);
  box-shadow:
    0 0 100px rgba(0, 180, 160, 0.12),
    0 20px 60px rgba(0, 0, 0, 0.5),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
}

.card-glow-top {
  position: absolute;
  top: -1px; left: 50%;
  transform: translateX(-50%);
  width: 60%;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(0, 200, 180, 0.6), transparent);
  border-radius: 50%;
}

/* ==================== 头部 Logo & 标题 ==================== */
.login-header {
  text-align: center;
  margin-bottom: 40px;
}

.logo-wrapper {
  position: relative;
  width: 80px; height: 80px;
  margin: 0 auto 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo-ring {
  position: absolute;
  inset: -6px;
  border-radius: 50%;
  border: 1.5px solid rgba(0, 200, 180, 0.3);
  animation: ringRotate 8s linear infinite;
}

@keyframes ringRotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.logo-icon {
  width: 40px; height: 40px;
  color: #00c8b4;
  filter: drop-shadow(0 0 12px rgba(0, 200, 180, 0.6));
  z-index: 1;
  animation: logoFloat 3s ease-in-out infinite;
}

@keyframes logoFloat {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-4px); }
}

.logo-pulse {
  position: absolute;
  inset: -12px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(0, 200, 180, 0.1), transparent 70%);
  animation: logoPulse 2.5s ease-in-out infinite;
}

@keyframes logoPulse {
  0%, 100% { transform: scale(1); opacity: 0.4; }
  50% { transform: scale(1.3); opacity: 0; }
}

.title-main {
  font-size: 30px;
  font-weight: 700;
  margin: 0 0 6px;
  background: linear-gradient(135deg, #00e5cc 0%, #00b4a0 40%, #38bdf8 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: 4px;
  text-shadow: none;
}

.title-sub {
  font-size: 12px;
  color: var(--login-subtitle);
  letter-spacing: 3px;
  text-transform: uppercase;
  margin: 0 0 16px;
}

.title-divider {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
}

.divider-line {
  width: 40px;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(0, 200, 180, 0.4), transparent);
}

.divider-dot {
  width: 4px; height: 4px;
  border-radius: 50%;
  background: #00c8b4;
  box-shadow: 0 0 8px rgba(0, 200, 180, 0.6);
}

/* ==================== 表单输入 ==================== */
.login-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
  margin-bottom: 0;
}

.login-form :deep(.el-form-item) {
  margin-bottom: 0;
}

.input-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.input-label {
  font-size: 12px;
  color: var(--login-muted);
  letter-spacing: 1px;
  font-weight: 500;
  padding-left: 4px;
}

.custom-input {
  --el-input-bg: var(--login-input-bg);
  --el-input-border-color: rgba(0, 200, 180, 0.15);
}

.custom-input :deep(.el-input__wrapper) {
  background: var(--login-input-bg) !important;
  border: 1px solid var(--border-light) !important;
  border-radius: 10px !important;
  box-shadow: none !important;
  padding: 2px 14px !important;
  height: 50px !important;
  transition: all 0.3s ease;
}

.custom-input :deep(.el-input__wrapper .el-input__inner),
.custom-input :deep(.el-input__wrapper input) {
  background-color: transparent !important;
  background-image: none !important;
  box-shadow: none !important;
}

.custom-input :deep(.el-input__wrapper:hover) {
  border-color: rgba(0, 200, 180, 0.3) !important;
}

.custom-input :deep(.el-input.is-focus .el-input__wrapper) {
  border-color: rgba(0, 200, 180, 0.5) !important;
  box-shadow: 0 0 20px rgba(0, 200, 180, 0.1) !important;
}

.custom-input :deep(.el-input__inner) {
  background: transparent !important;
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
  font-size: 15px !important;
  font-weight: 400;
}

.custom-input :deep(.el-input__inner::placeholder) {
  color: var(--login-muted) !important;
  -webkit-text-fill-color: var(--login-muted) !important;
  font-size: 13px;
}

.custom-input :deep(input:-webkit-autofill),
.custom-input :deep(input:-webkit-autofill:hover),
.custom-input :deep(input:-webkit-autofill:focus),
.custom-input :deep(input:-webkit-autofill:active) {
  box-shadow: 0 0 0 1000px var(--login-input-bg) inset !important;
  -webkit-box-shadow: 0 0 0 1000px var(--login-input-bg) inset !important;
  -webkit-text-fill-color: var(--text-primary) !important;
  caret-color: var(--primary-color) !important;
  transition: background-color 9999s ease-out 0s !important;
}

.custom-input :deep(.el-input__prefix) {
  margin-right: 10px;
}

.custom-input :deep(.el-input__suffix) {
  color: var(--login-muted);
}

.input-icon {
  width: 18px; height: 18px;
  color: var(--login-muted);
  transition: color 0.3s ease;
}

.custom-input :deep(.el-input.is-focus .el-input__prefix .input-icon) {
  color: #00c8b4;
}

/* ==================== 登录按钮 ==================== */
.login-btn {
  width: 100%; height: 52px;
  margin-top: 8px;
  font-size: 16px; font-weight: 600;
  letter-spacing: 2px;
  border: none;
  border-radius: 10px;
  background: linear-gradient(135deg, #009688 0%, #00b4a0 30%, #00d4c0 60%, #00e5cc 100%);
  color: #fff;
  position: relative;
  overflow: hidden;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
}

.login-btn::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, #00d4c0 0%, #38bdf8 100%);
  opacity: 0;
  transition: opacity 0.4s ease;
}

.login-btn:hover {
  transform: translateY(-2px);
  box-shadow:
    0 8px 30px rgba(0, 180, 150, 0.35),
    0 0 60px rgba(0, 200, 180, 0.15);
}

.login-btn:hover::before {
  opacity: 1;
}

.login-btn:active {
  transform: translateY(0);
}

.btn-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  position: relative;
  z-index: 1;
}

.btn-arrow {
  width: 18px; height: 18px;
  transition: transform 0.3s ease;
}

.login-btn:hover .btn-arrow {
  transform: translateX(4px);
}

/* ==================== 底部 ==================== */
.login-footer {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin-top: 32px;
  font-size: 11px;
  color: var(--login-footer);
  letter-spacing: 1px;
}

.footer-dot {
  width: 3px; height: 3px;
  border-radius: 50%;
  background: rgba(0, 200, 180, 0.3);
}
</style>

<style>
html[data-theme="light"] .login-container {
  background:
    radial-gradient(circle at 18% 18%, rgba(0, 150, 136, 0.12), transparent 28%),
    radial-gradient(circle at 82% 72%, rgba(8, 145, 178, 0.10), transparent 30%),
    linear-gradient(135deg, #f8fafc 0%, #eef6f8 45%, #f1f5f9 100%) !important;
}

html[data-theme="light"] .login-container .particle-canvas {
  display: none !important;
}

html[data-theme="light"] .login-container .ambient-orb {
  opacity: 0.06 !important;
}

html[data-theme="light"] .login-card {
  background: #ffffff !important;
  color: #0f172a !important;
  border: 1px solid rgba(15, 118, 110, 0.18) !important;
  box-shadow:
    0 24px 70px rgba(15, 23, 42, 0.12),
    0 0 0 1px rgba(255, 255, 255, 0.85) inset !important;
  backdrop-filter: none !important;
  -webkit-backdrop-filter: none !important;
}

html[data-theme="light"] .login-card:hover {
  border-color: rgba(15, 118, 110, 0.26) !important;
  box-shadow:
    0 28px 80px rgba(15, 23, 42, 0.14),
    0 0 0 1px rgba(255, 255, 255, 0.9) inset !important;
}

html[data-theme="light"] .login-card .logo-ring {
  border-color: rgba(15, 118, 110, 0.22) !important;
}

html[data-theme="light"] .login-card .logo-icon {
  color: #0f766e !important;
  filter: none !important;
}

html[data-theme="light"] .login-card .logo-pulse {
  background: radial-gradient(circle, rgba(15, 118, 110, 0.08), transparent 68%) !important;
}

html[data-theme="light"] .login-card .title-main {
  background: none !important;
  -webkit-text-fill-color: #0f172a !important;
  color: #0f172a !important;
  text-shadow: none !important;
}

html[data-theme="light"] .login-card .title-sub,
html[data-theme="light"] .login-card .input-label,
html[data-theme="light"] .login-card .login-footer {
  color: #475569 !important;
}

html[data-theme="light"] .login-card .divider-line {
  background: linear-gradient(90deg, transparent, rgba(15, 118, 110, 0.36), transparent) !important;
}

html[data-theme="light"] .login-card .divider-dot,
html[data-theme="light"] .login-card .footer-dot {
  background: #0f766e !important;
  box-shadow: none !important;
}

html[data-theme="light"] .login-card .custom-input .el-input__wrapper {
  background: #f8fafc !important;
  border-color: rgba(15, 23, 42, 0.14) !important;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04) inset !important;
}

html[data-theme="light"] .login-card .custom-input .el-input__wrapper:hover,
html[data-theme="light"] .login-card .custom-input .el-input__wrapper.is-focus,
html[data-theme="light"] .login-card .custom-input .el-input.is-focus .el-input__wrapper {
  background: #ffffff !important;
  border-color: #0f766e !important;
  box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.12) !important;
}

html[data-theme="light"] .login-card .custom-input .el-input__inner,
html[data-theme="light"] .login-card .custom-input input {
  color: #0f172a !important;
  -webkit-text-fill-color: #0f172a !important;
  background: transparent !important;
}

html[data-theme="light"] .login-card .custom-input .el-input__inner::placeholder {
  color: #94a3b8 !important;
  -webkit-text-fill-color: #94a3b8 !important;
}

html[data-theme="light"] .login-card .input-icon,
html[data-theme="light"] .login-card .el-input__prefix,
html[data-theme="light"] .login-card .el-input__suffix {
  color: #64748b !important;
}

html[data-theme="light"] .login-card .login-btn {
  background: linear-gradient(135deg, #0f766e 0%, #0891b2 100%) !important;
  color: #ffffff !important;
  box-shadow: 0 14px 28px rgba(8, 145, 178, 0.20) !important;
}

html[data-theme="light"] .login-theme-toggle {
  background: #ffffff !important;
  color: #0f766e !important;
  border-color: rgba(15, 118, 110, 0.18) !important;
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.10) !important;
}
</style>
