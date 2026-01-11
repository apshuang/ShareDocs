<template>
  <div class="documents-container">
    <div class="documents-header">
      <h1>我的文档</h1>
      <button @click="showCreateModal = true" class="create-button">创建文档</button>
    </div>
    
    <div class="search-bar">
      <input
        v-model="searchQuery"
        type="text"
        placeholder="搜索文档..."
        @input="handleSearch"
      />
    </div>
    
    <div v-if="documentStore.loading" class="loading">加载中...</div>
    
    <div v-else-if="documentStore.documents.length === 0" class="empty-state">
      <p>还没有文档，创建第一个文档吧！</p>
    </div>
    
    <div v-else class="documents-list">
      <div
        v-for="doc in documentStore.documents"
        :key="doc.id"
        class="document-card"
        @click="openDocument(doc.id)"
      >
        <h3>
          {{ doc.title }}
          <span 
            v-if="doc.permission && !doc.is_owner" 
            :class="['permission-badge', `permission-${doc.permission}`]"
          >
            {{ getPermissionText(doc.permission) }}
          </span>
        </h3>
        <div class="document-meta">
          <span>版本: {{ doc.current_version }}</span>
          <span>{{ formatDate(doc.updated_at) }}</span>
        </div>
        <div class="document-actions">
          <button
            v-if="doc.is_owner"
            @click.stop="handleDelete(doc.id)"
            class="delete-button"
          >
            删除
          </button>
        </div>
      </div>
    </div>
    
    <!-- 分页 -->
    <div v-if="documentStore.pagination.total_pages > 1" class="pagination">
      <button
        @click="changePage(documentStore.pagination.page - 1)"
        :disabled="documentStore.pagination.page === 1"
      >
        上一页
      </button>
      <span>
        第 {{ documentStore.pagination.page }} / {{ documentStore.pagination.total_pages }} 页
        （共 {{ documentStore.pagination.total }} 条）
      </span>
      <button
        @click="changePage(documentStore.pagination.page + 1)"
        :disabled="documentStore.pagination.page === documentStore.pagination.total_pages"
      >
        下一页
      </button>
    </div>
    
    <!-- 创建文档模态框 -->
    <div v-if="showCreateModal" class="modal-overlay" @click="showCreateModal = false">
      <div class="modal-content" @click.stop>
        <h2>创建新文档</h2>
        <form @submit.prevent="handleCreate">
          <div class="form-group">
            <label>文档标题</label>
            <input v-model="newDocumentTitle" type="text" required placeholder="请输入文档标题" />
          </div>
          <div class="form-actions">
            <button type="button" @click="showCreateModal = false">取消</button>
            <button type="submit" :disabled="creating">创建</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useDocumentStore } from '@/stores/document'

const router = useRouter()
const documentStore = useDocumentStore()

const searchQuery = ref('')
const showCreateModal = ref(false)
const newDocumentTitle = ref('')
const creating = ref(false)

onMounted(() => {
  documentStore.fetchDocuments()
})

function handleSearch() {
  documentStore.fetchDocuments(1, 20, searchQuery.value || undefined)
}

function changePage(page: number) {
  documentStore.fetchDocuments(page, 20, searchQuery.value || undefined)
}

function openDocument(id: number) {
  router.push(`/documents/${id}`)
}

async function handleCreate() {
  if (!newDocumentTitle.value.trim()) return
  
  creating.value = true
  const result = await documentStore.createDocument(newDocumentTitle.value.trim())
  
  if (result.success && result.data) {
    showCreateModal.value = false
    newDocumentTitle.value = ''
    router.push(`/documents/${result.data.id}`)
  } else {
    alert(result.message || '创建失败')
  }
  
  creating.value = false
}

async function handleDelete(id: number) {
  if (!confirm('确定要删除这个文档吗？')) return
  
  const result = await documentStore.deleteDocument(id)
  if (!result.success) {
    alert(result.message || '删除失败')
  }
}

function formatDate(dateString: string) {
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN')
}

function getPermissionText(permission: string): string {
  const map: Record<string, string> = {
    'read': '只读',
    'edit': '编辑',
    'admin': '管理员'
  }
  return map[permission] || permission
}
</script>

<style scoped>
.documents-container {
  width: 100%;
  min-height: 100vh;
  margin: 0;
  padding: 2rem;
  box-sizing: border-box;
  background: #f5f5f5;
}

.documents-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

h1 {
  margin: 0;
  color: #333;
}

.create-button {
  background: #667eea;
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
  transition: background 0.3s;
}

.create-button:hover {
  background: #5568d3;
}

.search-bar {
  margin-bottom: 2rem;
}

.search-bar input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
  box-sizing: border-box;
}

.loading {
  text-align: center;
  padding: 2rem;
  color: #666;
}

.empty-state {
  text-align: center;
  padding: 4rem;
  color: #999;
}

.documents-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.document-card {
  background: white;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 1.5rem;
  cursor: pointer;
  transition: box-shadow 0.3s;
}

.document-card:hover {
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.document-card h3 {
  margin: 0 0 1rem 0;
  color: #333;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.permission-badge {
  font-size: 0.75rem;
  color: white;
  padding: 0.25rem 0.5rem;
  border-radius: 3px;
  font-weight: normal;
}

.permission-badge.permission-read {
  background: #95A5A6;
}

.permission-badge.permission-edit {
  background: #3498DB;
}

.permission-badge.permission-admin {
  background: #E67E22;
}

.document-meta {
  display: flex;
  justify-content: space-between;
  color: #666;
  font-size: 0.9rem;
  margin-bottom: 1rem;
}

.document-actions {
  display: flex;
  justify-content: flex-end;
}

.delete-button {
  background: #e74c3c;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
}

.delete-button:hover {
  background: #c0392b;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1rem;
  margin-top: 2rem;
}

.pagination button {
  padding: 0.5rem 1rem;
  border: 1px solid #ddd;
  background: white;
  border-radius: 4px;
  cursor: pointer;
}

.pagination button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  width: 90%;
  max-width: 500px;
}

.modal-content h2 {
  margin: 0 0 1.5rem 0;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  color: #555;
}

.form-group input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
  box-sizing: border-box;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
}

.form-actions button {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
}

.form-actions button[type="button"] {
  background: #ddd;
  color: #333;
}

.form-actions button[type="submit"] {
  background: #667eea;
  color: white;
}
</style>


