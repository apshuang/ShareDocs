import { defineStore } from 'pinia'
import { ref } from 'vue'
import { authAPI } from '@/services/api'
import type { AxiosResponse } from 'axios'

interface User {
  id: number
  username: string
  email: string
}

interface LoginResponse {
  success: boolean
  data: {
    access_token: string
    token_type: string
    expires_in: number
    user: User
  }
  message: string
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const token = ref<string | null>(localStorage.getItem('access_token'))
  const isAuthenticated = ref<boolean>(!!token.value)

  // 初始化时从 localStorage 恢复用户信息
  const savedUser = localStorage.getItem('user')
  if (savedUser) {
    try {
      user.value = JSON.parse(savedUser)
    } catch (e) {
      console.error('Failed to parse user from localStorage', e)
    }
  }

  async function login(username: string, password: string) {
    try {
      const response: AxiosResponse<LoginResponse> = await authAPI.login({ username, password })
      
      if (response.data.success) {
        const { access_token, user: userData } = response.data.data
        token.value = access_token
        user.value = userData
        isAuthenticated.value = true
        
        // 保存到 localStorage
        localStorage.setItem('access_token', access_token)
        localStorage.setItem('user', JSON.stringify(userData))
        
        return { success: true }
      } else {
        return { success: false, message: response.data.message || '登录失败' }
      }
    } catch (error: any) {
      console.error('Login error:', error)
      
      // 处理网络错误
      if (!error.response) {
        if (error.code === 'ECONNREFUSED' || error.message?.includes('Network Error')) {
          return {
            success: false,
            message: '无法连接到服务器，请确保后端服务正在运行（http://localhost:8000）'
          }
        }
        return {
          success: false,
          message: `网络错误: ${error.message || '无法连接到服务器'}`
        }
      }
      
      // 处理 HTTP 错误响应
      const errorData = error.response?.data
      if (errorData?.error?.message) {
        return { success: false, message: errorData.error.message }
      }
      if (errorData?.detail) {
        return { success: false, message: errorData.detail }
      }
      if (errorData?.message) {
        return { success: false, message: errorData.message }
      }
      
      return {
        success: false,
        message: `登录失败: ${error.response?.status || '未知错误'}`
      }
    }
  }

  async function register(username: string, email: string, password: string) {
    try {
      const response = await authAPI.register({ username, email, password })
      
      if (response.data.success) {
        return { success: true, message: '注册成功，请登录' }
      } else {
        return { success: false, message: response.data.message || '注册失败' }
      }
    } catch (error: any) {
      console.error('Register error:', error)
      
      // 处理网络错误
      if (!error.response) {
        if (error.code === 'ECONNREFUSED' || error.message?.includes('Network Error')) {
          return {
            success: false,
            message: '无法连接到服务器，请确保后端服务正在运行（http://localhost:8000）'
          }
        }
        return {
          success: false,
          message: `网络错误: ${error.message || '无法连接到服务器'}`
        }
      }
      
      // 处理 HTTP 错误响应
      const errorData = error.response?.data
      if (errorData?.error?.message) {
        return { success: false, message: errorData.error.message }
      }
      if (errorData?.detail) {
        // FastAPI 验证错误
        if (Array.isArray(errorData.detail)) {
          const messages = errorData.detail.map((d: any) => d.msg || d.message).join(', ')
          return { success: false, message: messages }
        }
        return { success: false, message: errorData.detail }
      }
      if (errorData?.message) {
        return { success: false, message: errorData.message }
      }
      
      return {
        success: false,
        message: `注册失败: ${error.response?.status || '未知错误'}`
      }
    }
  }

  async function fetchUser() {
    try {
      const response = await authAPI.getMe()
      if (response.data.success) {
        user.value = response.data.data
        localStorage.setItem('user', JSON.stringify(response.data.data))
        return { success: true }
      }
    } catch (error) {
      console.error('Failed to fetch user', error)
      logout()
    }
  }

  function logout() {
    user.value = null
    token.value = null
    isAuthenticated.value = false
    localStorage.removeItem('access_token')
    localStorage.removeItem('user')
  }

  return {
    user,
    token,
    isAuthenticated,
    login,
    register,
    fetchUser,
    logout,
  }
})


