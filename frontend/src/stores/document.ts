import { defineStore } from 'pinia'
import { ref } from 'vue'
import { documentAPI } from '@/services/api'
import type { AxiosResponse } from 'axios'

interface Document {
  id: number
  title: string
  owner_id: number
  content?: string
  current_version: number
  created_at: string
  updated_at: string
}

interface DocumentListResponse {
  success: boolean
  data: {
    items: Document[]
    total: number
    page: number
    page_size: number
    total_pages: number
  }
  message: string
}

export const useDocumentStore = defineStore('document', () => {
  const documents = ref<Document[]>([])
  const currentDocument = ref<Document | null>(null)
  const loading = ref(false)
  const pagination = ref({
    page: 1,
    page_size: 20,
    total: 0,
    total_pages: 0,
  })

  async function fetchDocuments(page = 1, pageSize = 20, search?: string) {
    loading.value = true
    try {
      const response: AxiosResponse<DocumentListResponse> = await documentAPI.list({
        page,
        page_size: pageSize,
        search,
      })
      
      if (response.data.success) {
        documents.value = response.data.data.items
        pagination.value = {
          page: response.data.data.page,
          page_size: response.data.data.page_size,
          total: response.data.data.total,
          total_pages: response.data.data.total_pages,
        }
        return { success: true }
      } else {
        return { success: false, message: response.data.message || '获取文档列表失败' }
      }
    } catch (error: any) {
      return {
        success: false,
        message: error.response?.data?.error?.message || error.message || '获取文档列表失败'
      }
    } finally {
      loading.value = false
    }
  }

  async function fetchDocument(id: number) {
    loading.value = true
    try {
      const response = await documentAPI.get(id)
      
      if (response.data.success) {
        currentDocument.value = response.data.data
        return { success: true }
      } else {
        return { success: false, message: response.data.message || '获取文档失败' }
      }
    } catch (error: any) {
      return {
        success: false,
        message: error.response?.data?.error?.message || error.message || '获取文档失败'
      }
    } finally {
      loading.value = false
    }
  }

  async function createDocument(title: string, content = '') {
    loading.value = true
    try {
      const response = await documentAPI.create({ title, content })
      
      if (response.data.success) {
        return { success: true, data: response.data.data }
      } else {
        return { success: false, message: response.data.message || '创建文档失败' }
      }
    } catch (error: any) {
      return {
        success: false,
        message: error.response?.data?.error?.message || error.message || '创建文档失败'
      }
    } finally {
      loading.value = false
    }
  }

  async function updateDocument(id: number, title?: string) {
    loading.value = true
    try {
      const response = await documentAPI.update(id, { title })
      
      if (response.data.success) {
        // 更新本地文档列表
        const index = documents.value.findIndex(doc => doc.id === id)
        if (index !== -1 && title && documents.value[index]) {
          documents.value[index].title = title
        }
        return { success: true }
      } else {
        return { success: false, message: response.data.message || '更新文档失败' }
      }
    } catch (error: any) {
      return {
        success: false,
        message: error.response?.data?.error?.message || error.message || '更新文档失败'
      }
    } finally {
      loading.value = false
    }
  }

  async function deleteDocument(id: number) {
    loading.value = true
    try {
      const response = await documentAPI.delete(id)
      
      if (response.data.success) {
        // 从列表中移除
        documents.value = documents.value.filter(doc => doc.id !== id)
        return { success: true }
      } else {
        return { success: false, message: response.data.message || '删除文档失败' }
      }
    } catch (error: any) {
      return {
        success: false,
        message: error.response?.data?.error?.message || error.message || '删除文档失败'
      }
    } finally {
      loading.value = false
    }
  }

  function clearCurrentDocument() {
    currentDocument.value = null
  }

  return {
    documents,
    currentDocument,
    loading,
    pagination,
    fetchDocuments,
    fetchDocument,
    createDocument,
    updateDocument,
    deleteDocument,
    clearCurrentDocument,
  }
})

