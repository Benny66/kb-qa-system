/**
 * Axios 实例封装
 * - 自动携带 JWT Token
 * - 统一错误处理（401 自动跳转登录）
 */
import axios from 'axios'

const request = axios.create({
  baseURL: '/api',
  timeout: 60000, // AI 接口可能较慢，设 60s
})

// 请求拦截：注入 Token
request.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截：统一处理错误
request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    const msg = error.response?.data?.msg || error.message || '请求失败'
    return Promise.reject(new Error(msg))
  }
)

export default request
