import { createRouter, createWebHistory } from 'vue-router'
import MainView from '../views/MainView.vue'
import VideoMonitor from '../components/VideoMonitor.vue'

const routes = [
  {
    path: '/',
    name: 'Main',
    component: MainView
  },
  {
    path: '/monitor',
    name: 'Monitor',
    component: VideoMonitor
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router

