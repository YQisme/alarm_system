import { createRouter, createWebHistory } from 'vue-router'
import MainView from '../views/MainView.vue'
import VideoMonitor from '../components/VideoMonitor.vue'
import LoginView from '../views/LoginView.vue'
import axios from 'axios'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: LoginView,
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    name: 'Main',
    component: MainView,
    meta: { requiresAuth: true }
  },
  {
    path: '/monitor',
    name: 'Monitor',
    component: VideoMonitor,
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach(async (to, from, next) => {
  // 检查登录配置
  try {
    const res = await axios.get('/api/login/status')
    const loginEnabled = res.data.login_enabled
    
    // 如果未启用登录，直接通过
    if (!loginEnabled) {
      next()
      return
    }
    
    // 如果已登录，直接通过
    if (res.data.logged_in) {
      // 如果访问登录页，重定向到首页
      if (to.path === '/login') {
        next('/')
      } else {
        next()
      }
      return
    }
    
    // 未登录，需要登录
    if (to.meta.requiresAuth !== false) {
      // 需要登录的页面，重定向到登录页
      next('/login')
    } else {
      // 登录页，允许访问
      next()
    }
  } catch (error) {
    // API调用失败，允许访问（可能是后端未启动）
    console.error('检查登录状态失败:', error)
    next()
  }
})

export default router

