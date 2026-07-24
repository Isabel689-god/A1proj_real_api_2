// frontend/src/router/index.ts
import { createRouter, createWebHistory } from 'vue-router';
import { useChatStore } from '../stores/chat';

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/login'
    },
    {
      path: '/login',
      name: 'Login',
      component: () => import('../views/LoginView.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/chat',
      name: 'Chat',
      component: () => import('../views/ChatView.vue'),
      meta: { requiresAuth: true } // 不再硬编码role，由store校验
    },
    // 管理端路由
    {
      path: '/admin',
      name: 'Admin',
      component: () => import('../views/AdminView.vue'),
      meta: { requiresAuth: true, role: 'admin' }
    },
    // 数字大屏
    {
      path: '/dashboard',
      name: 'Dashboard',
      component: () => import('../views/DashboardView.vue'),
      meta: { requiresAuth: true }
    },
    // 新能源汽车大屏
    {
      path: '/automotive',
      name: 'Automotive',
      component: () => import('../views/AutomotiveDashboard.vue'),
      meta: { requiresAuth: true }
    }
  ]
});

// 路由守卫
router.beforeEach((to, from, next) => {
  const store = useChatStore();

  if (to.meta.requiresAuth && !store.isLoggedIn) {
    next('/login');
  } else if (to.path === '/login' && store.isLoggedIn) {
    next(store.role === 'admin' ? '/admin' : '/chat');
  } else if (to.meta.role && to.meta.role !== store.role && store.isLoggedIn) {
    // 防止越权访问
    next(store.role === 'admin' ? '/admin' : '/chat');
  } else {
    next();
  }
});

export default router;