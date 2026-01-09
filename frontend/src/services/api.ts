import axios, { type AxiosInstance, type AxiosRequestConfig } from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// 创建 axios 实例
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器：添加 Token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器：处理错误
apiClient.interceptors.response.use(
  (response) => {
    return response
  },
  async (error) => {
    if (error.response?.status === 401) {
      // Token 过期，清除本地存储并跳转到登录页
      localStorage.removeItem('access_token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// 认证 API
export const authAPI = {
  register: (data: { username: string; email: string; password: string }) =>
    apiClient.post('/api/auth/register', data),
  
  login: (data: { username: string; password: string }) =>
    apiClient.post('/api/auth/login', data),
  
  refresh: () =>
    apiClient.post('/api/auth/refresh'),
  
  getMe: () =>
    apiClient.get('/api/auth/me'),
}

// 文档 API
export const documentAPI = {
  create: (data: { title: string; content: string }) =>
    apiClient.post('/api/documents', data),
  
  list: (params?: { page?: number; page_size?: number; search?: string }) =>
    apiClient.get('/api/documents', { params }),
  
  get: (id: number) =>
    apiClient.get(`/api/documents/${id}`),
  
  update: (id: number, data: { title?: string }) =>
    apiClient.patch(`/api/documents/${id}`, data),
  
  delete: (id: number) =>
    apiClient.delete(`/api/documents/${id}`),
  
  applyOperation: (id: number, operation: {
    type: 'insert' | 'delete' | 'format' | 'replace'
    from_pos: number
    to_pos: number
    content?: string
    marks?: Record<string, any>
    base_version: number
  }) =>
    apiClient.post(`/api/documents/${id}/operations`, operation),
}

export default apiClient


