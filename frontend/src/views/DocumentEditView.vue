<template>
  <div class="document-edit-container">
    <div v-if="documentStore.loading" class="loading">加载中...</div>
    
    <div v-else-if="!documentStore.currentDocument" class="error">
      文档不存在
    </div>
    
    <div v-else class="editor-wrapper">
      <div class="editor-header">
        <div class="header-left">
          <input
            v-model="documentTitle"
            @blur="saveTitle"
            @keyup.enter="saveTitle"
            :readonly="isReadOnly"
            :class="['title-input', { 'readonly': isReadOnly }]"
            type="text"
          />
          <span v-if="isReadOnly" class="readonly-badge">只读</span>
        </div>
        <div class="header-actions">
          <button 
            v-if="isOwner" 
            @click="openShareModal" 
            class="share-button"
          >
            分享
          </button>
          <button @click="goBack" class="back-button">返回</button>
        </div>
      </div>
      
      <div class="editor-meta" v-if="editors.length > 0 || lastUpdated">
        <div class="editors-list" v-if="editors.length > 0">
          <div
            v-for="editor in editors"
            :key="editor.user_id"
            class="editor-item"
          >
            <span
              class="color-dot"
              :style="{ backgroundColor: editor.color || '#FFA07A' }"
            ></span>
            <span class="editor-name">{{ truncateUsername(editor.username) }}</span>
          </div>
        </div>
        <div class="meta-divider" v-if="editors.length > 0 && lastUpdated">|</div>
        <div class="last-updated" v-if="lastUpdated">
          {{ formatDate(lastUpdated) }}
        </div>
      </div>
      
      <div class="editor-container">
        <EditorContent :editor="editor" />
      </div>
    </div>
    
    <!-- 分享模态框 -->
    <div v-if="showShareModal" class="modal-overlay" @click="showShareModal = false">
      <div class="modal-content share-modal" @click.stop>
        <div class="modal-header">
          <h2>分享文档</h2>
          <button @click="showShareModal = false" class="close-button">×</button>
        </div>
        
        <div class="share-section">
          <h3>添加协作者</h3>
          <div class="search-user">
            <input
              v-model="shareSearchQuery"
              @input="searchUsers"
              type="text"
              placeholder="搜索用户名或ID..."
              class="search-input"
            />
            <div v-if="searchResults.length > 0" class="search-results">
              <div
                v-for="user in searchResults"
                :key="user.id"
                class="user-item"
                @click="selectUser(user)"
              >
                <span class="user-name">{{ user.username }}</span>
                <span class="user-id">ID: {{ user.id }}</span>
              </div>
            </div>
          </div>
          
          <div v-if="selectedUser" class="selected-user">
            <span>已选择: {{ selectedUser.username }} (ID: {{ selectedUser.id }})</span>
            <select v-model="selectedPermission" class="permission-select">
              <option value="read">只读</option>
              <option value="edit">编辑</option>
              <option value="admin">管理员</option>
            </select>
            <button @click="shareDocument" class="share-confirm-button">确认分享</button>
          </div>
        </div>
        
        <div class="share-section">
          <h3>已分享的用户</h3>
          <div v-if="shares.length === 0" class="empty-shares">暂无分享</div>
          <div v-else class="shares-list">
            <div
              v-for="share in shares"
              :key="share.id"
              class="share-item"
            >
              <div class="share-info">
                <span class="share-username">{{ share.username }}</span>
                <span class="share-permission">{{ getPermissionText(share.permission) }}</span>
              </div>
              <button
                @click="unshareDocument(share.id)"
                class="unshare-button"
              >
                取消分享
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useEditor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import { useDocumentStore } from '@/stores/document'
import { useAuthStore } from '@/stores/auth'
import { documentAPI, authAPI } from '@/services/api'
import { htmlToMarkdown, markdownToHtml } from '@/utils/markdown'
import { DocumentWebSocket } from '@/services/websocket'
import { applyOperation } from '@/utils/operation'

const route = useRoute()
const router = useRouter()
const documentStore = useDocumentStore()
const authStore = useAuthStore()

const documentId = ref<number | null>(null)
const lastMarkdown = ref<string>('')
const currentVersion = ref<number>(0)
const isApplyingOperation = ref(false)
const isSendingOperation = ref(false)
const documentTitle = ref<string>('')
const editors = ref<Array<{ user_id: number; username: string; color: string; last_edit_time: string | null }>>([])
const lastUpdated = ref<string>('')
const isOwner = ref<boolean>(false)
const userPermission = ref<'read' | 'edit' | 'admin'>('read')
const isReadOnly = ref(false)
const showShareModal = ref(false)
const shareSearchQuery = ref('')
const searchResults = ref<Array<{ id: number; username: string; email: string }>>([])
const selectedUser = ref<{ id: number; username: string } | null>(null)
const selectedPermission = ref<'read' | 'edit' | 'admin'>('edit')
const shares = ref<Array<{ id: number; username: string; permission: string }>>([])
let debounceTimer: ReturnType<typeof setTimeout> | null = null
let searchDebounceTimer: ReturnType<typeof setTimeout> | null = null
let ws: DocumentWebSocket | null = null

const editor = useEditor({
  extensions: [StarterKit],
  content: '',
  editorProps: {
    attributes: {
      class: 'prose prose-sm sm:prose lg:prose-lg xl:prose-2xl mx-auto focus:outline-none',
    },
  },
  onUpdate: ({ editor }) => {
    if (isApplyingOperation.value || isReadOnly.value) {
      return
    }
    
    if (!documentId.value) {
      return
    }
    
    if (debounceTimer) {
      clearTimeout(debounceTimer)
    }
    
    debounceTimer = setTimeout(() => {
      const html = editor.getHTML()
      const newMarkdown = htmlToMarkdown(html)
      
      if (newMarkdown === lastMarkdown.value) {
        return
      }
      
      handleContentChange(lastMarkdown.value, newMarkdown)
      lastMarkdown.value = newMarkdown
    }, 300)
  },
})

function calculateDiff(oldText: string, newText: string): Array<{ type: 'insert' | 'delete' | 'replace', from_pos: number, to_pos: number, content?: string }> {
  const operations: Array<{ type: 'insert' | 'delete' | 'replace', from_pos: number, to_pos: number, content?: string }> = []
  
  let i = 0
  while (i < oldText.length && i < newText.length && oldText[i] === newText[i]) {
    i++
  }
  
  let oldEnd = oldText.length
  let newEnd = newText.length
  while (oldEnd > i && newEnd > i && oldText[oldEnd - 1] === newText[newEnd - 1]) {
    oldEnd--
    newEnd--
  }
  
  if (i === oldEnd && i === newEnd) {
    return []
  }
  
  const deleted = oldText.substring(i, oldEnd)
  const inserted = newText.substring(i, newEnd)
  
  if (deleted.length > 0 && inserted.length > 0) {
    operations.push({
      type: 'replace',
      from_pos: i,
      to_pos: oldEnd,
      content: inserted
    })
  } else if (deleted.length > 0) {
    operations.push({
      type: 'delete',
      from_pos: i,
      to_pos: oldEnd
    })
  } else if (inserted.length > 0) {
    operations.push({
      type: 'insert',
      from_pos: i,
      to_pos: i,
      content: inserted
    })
  }
  
  return operations
}

async function handleContentChange(oldMarkdown: string, newMarkdown: string) {
  if (!documentId.value || isSendingOperation.value) {
    return
  }
  
  const operations = calculateDiff(oldMarkdown, newMarkdown)
  if (operations.length === 0) {
    return
  }
  
  isSendingOperation.value = true
  
  try {
    for (const op of operations) {
      const operationData: any = {
        type: op.type === 'replace' ? 'replace' : op.type,
        from_pos: op.from_pos,
        to_pos: op.to_pos,
        base_version: currentVersion.value
      }
      
      if (op.type === 'insert' || op.type === 'replace') {
        operationData.content = op.content
      }
      
      const response = await documentAPI.applyOperation(documentId.value, operationData)
      
      if (response.data.success) {
        currentVersion.value = response.data.data.version
      } else {
        console.error('操作应用失败:', response.data.message)
        alert('操作应用失败: ' + response.data.message)
        break
      }
    
    await loadEditors()
    }
  } catch (error: any) {
    console.error('发送操作失败:', error)
    if (error.response?.status === 409) {
      alert('版本冲突，请刷新页面')
      location.reload()
    } else {
      alert('发送操作失败: ' + (error.response?.data?.detail || error.message))
    }
  } finally {
    isSendingOperation.value = false
  }
}

async function applyRemoteOperation(operation: any) {
  if (!editor.value || !documentId.value) {
    return
  }

  isApplyingOperation.value = true

  try {
    const currentMarkdown = lastMarkdown.value
    const newMarkdown = applyOperation(currentMarkdown, {
      type: operation.type,
      from_pos: operation.from_pos,
      to_pos: operation.to_pos,
      content: operation.content
    })

    const newHtml = markdownToHtml(newMarkdown)
    
    const selection = editor.value.state.selection
    const oldFrom = selection.from
    const oldTo = selection.to
    
    editor.value.commands.setContent(newHtml)
    lastMarkdown.value = newMarkdown
    currentVersion.value = operation.version

    await new Promise(resolve => setTimeout(resolve, 10))

    if (editor.value) {
      const doc = editor.value.state.doc
      const newFrom = Math.min(oldFrom, doc.content.size)
      const newTo = Math.min(oldTo, doc.content.size)
      
      try {
        editor.value.commands.setTextSelection({
          from: newFrom,
          to: newTo
        })
      } catch (error) {
        const safeFrom = Math.max(1, Math.min(newFrom, doc.content.size))
        const safeTo = Math.max(1, Math.min(newTo, doc.content.size))
        editor.value.commands.setTextSelection({
          from: safeFrom,
          to: safeTo
        })
      }
    }

  } catch (error) {
    console.error('应用远程操作失败:', error)
  } finally {
    isApplyingOperation.value = false
  }
}

onMounted(async () => {
  try {
    const id = parseInt(route.params.id as string)
    if (isNaN(id)) {
      alert('无效的文档ID')
      router.push('/documents')
      return
    }
    
    documentId.value = id
    
    const result = await documentStore.fetchDocument(id)
    
    if (result.success && documentStore.currentDocument) {
      documentTitle.value = documentStore.currentDocument.title
      isOwner.value = documentStore.currentDocument.owner_id === authStore.user?.id
      userPermission.value = documentStore.currentDocument.permission || 'read'
      isReadOnly.value = userPermission.value === 'read'
      
      if (editor.value && documentStore.currentDocument.content) {
        isApplyingOperation.value = true
        const markdown = documentStore.currentDocument.content
        const html = markdownToHtml(markdown)
        
        editor.value.setEditable(!isReadOnly.value)
        editor.value.commands.setContent(html)
        
        lastMarkdown.value = markdown
        currentVersion.value = documentStore.currentDocument.current_version
        isApplyingOperation.value = false
      }
      
      try {
        await loadEditors()
        if (isOwner.value) {
          await loadShares()
        }
      } catch (error) {
        console.error('加载编辑者信息失败:', error)
      }

      try {
        ws = new DocumentWebSocket()
        
        ws.on('connected', (data: any) => {
          console.log('WebSocket 已连接:', data)
          if (data && data.current_version !== undefined) {
            currentVersion.value = data.current_version
          }
        })

        ws.on('operation_applied', async (data: any) => {
          if (data && data.operation) {
            await applyRemoteOperation(data.operation)
            await loadEditors()
          }
        })

        ws.on('subscribed', (data: any) => {
          console.log('已订阅文档:', data)
          if (data && data.current_version !== undefined) {
            currentVersion.value = data.current_version
          }
        })

        await ws.connect(id)
      } catch (error) {
        console.error('WebSocket 连接失败:', error)
      }
    } else {
      alert(result.message || '加载文档失败')
      router.push('/documents')
    }
  } catch (error) {
    console.error('页面加载失败:', error)
    alert('页面加载失败，请重试')
    router.push('/documents')
  }
})

onBeforeUnmount(() => {
  if (debounceTimer) {
    clearTimeout(debounceTimer)
  }
  if (searchDebounceTimer) {
    clearTimeout(searchDebounceTimer)
  }
  if (ws) {
    ws.disconnect()
    ws = null
  }
  if (editor.value) {
    editor.value.destroy()
  }
  documentStore.clearCurrentDocument()
})

async function saveTitle() {
  if (!documentId.value || !documentStore.currentDocument) {
    return
  }
  
  const newTitle = documentTitle.value.trim()
  if (newTitle === documentStore.currentDocument.title || !newTitle) {
    documentTitle.value = documentStore.currentDocument.title
    return
  }
  
  try {
    const result = await documentStore.updateDocument(documentId.value, newTitle)
    if (result.success) {
      if (documentStore.currentDocument) {
        documentStore.currentDocument.title = newTitle
      }
      await loadEditors()
    } else {
      alert('保存标题失败: ' + result.message)
      if (documentStore.currentDocument) {
        documentTitle.value = documentStore.currentDocument.title
      }
    }
  } catch (error: any) {
    console.error('保存标题失败:', error)
    alert('保存标题失败: ' + (error.response?.data?.detail || error.message))
    if (documentStore.currentDocument) {
      documentTitle.value = documentStore.currentDocument.title
    }
  }
}

async function loadEditors() {
  if (!documentId.value) {
    return
  }
  
  try {
    const response = await documentAPI.getEditors(documentId.value)
    if (response.data.success) {
      editors.value = response.data.data.editors
      lastUpdated.value = response.data.data.last_updated
    }
  } catch (error: any) {
    console.error('加载编辑者信息失败:', error)
  }
}

function formatDate(dateString: string): string {
  if (!dateString) {
    return '未知'
  }
  const date = new Date(dateString)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const seconds = Math.floor(diff / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)
  const months = Math.floor(days / 30)
  const years = Math.floor(days / 365)
  
  if (years > 0) {
    return `${years}年前`
  } else if (months > 0) {
    return `${months}个月前`
  } else if (days > 0) {
    return `${days}天前`
  } else if (hours > 0) {
    return `${hours}小时前`
  } else if (minutes > 0) {
    return `${minutes}分钟前`
  } else if (seconds > 10) {
    return `${seconds}秒前`
  } else {
    return '刚刚'
  }
}

function truncateUsername(username: string, maxLength: number = 8): string {
  if (!username) {
    return ''
  }
  if (username.length <= maxLength) {
    return username
  }
  return username.substring(0, maxLength) + '....'
}

async function searchUsers() {
  if (searchDebounceTimer) {
    clearTimeout(searchDebounceTimer)
  }
  
  if (!shareSearchQuery.value.trim()) {
    searchResults.value = []
    return
  }
  
  searchDebounceTimer = setTimeout(async () => {
    try {
      const response = await authAPI.searchUsers({
        q: shareSearchQuery.value.trim(),
        limit: 10
      })
      if (response.data.success) {
        searchResults.value = response.data.data.users
      }
    } catch (error) {
      console.error('搜索用户失败:', error)
      searchResults.value = []
    }
  }, 300)
}

function selectUser(user: { id: number; username: string }) {
  selectedUser.value = user
  shareSearchQuery.value = ''
  searchResults.value = []
}

async function shareDocument() {
  if (!documentId.value || !selectedUser.value) {
    return
  }
  
  try {
    const response = await documentAPI.shareDocument(documentId.value, {
      user_id: selectedUser.value.id,
      permission: selectedPermission.value
    })
    
    if (response.data.success) {
      selectedUser.value = null
      shareSearchQuery.value = ''
      await loadShares()
      alert('分享成功')
    } else {
      alert('分享失败: ' + response.data.message)
    }
  } catch (error: any) {
    console.error('分享失败:', error)
    alert('分享失败: ' + (error.response?.data?.detail || error.message))
  }
}

async function loadShares() {
  if (!documentId.value || !isOwner.value) {
    return
  }
  
  try {
    const response = await documentAPI.getShares(documentId.value)
    if (response.data.success) {
      shares.value = response.data.data.shares.map((share: any) => ({
        id: share.id,
        username: share.username,
        permission: share.permission
      }))
    }
  } catch (error) {
    console.error('加载分享列表失败:', error)
  }
}

async function unshareDocument(shareId: number) {
  if (!documentId.value) {
    return
  }
  
  if (!confirm('确定要取消分享吗？')) {
    return
  }
  
  try {
    const response = await documentAPI.unshareDocument(documentId.value, shareId)
    if (response.data.success) {
      await loadShares()
      alert('取消分享成功')
    } else {
      alert('取消分享失败: ' + response.data.message)
    }
  } catch (error: any) {
    console.error('取消分享失败:', error)
    alert('取消分享失败: ' + (error.response?.data?.detail || error.message))
  }
}

function getPermissionText(permission: string): string {
  const map: Record<string, string> = {
    'read': '只读',
    'edit': '编辑',
    'admin': '管理员'
  }
  return map[permission] || permission
}

async function openShareModal() {
  showShareModal.value = true
  await loadShares()
}

function goBack() {
  router.push('/documents')
}
</script>

<style scoped>
.document-edit-container {
  width: 100%;
  min-height: 100vh;
  margin: 0;
  padding: 2rem;
  box-sizing: border-box;
  background: #f5f5f5;
}

.loading, .error {
  text-align: center;
  padding: 4rem;
  color: #666;
}

.editor-wrapper {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid #eee;
}

.header-actions {
  display: flex;
  gap: 0.75rem;
  align-items: center;
}

.header-left {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.title-input {
  flex: 1;
  font-size: 2rem;
  font-weight: bold;
  color: #333;
  border: none;
  outline: none;
  background: transparent;
  padding: 0.5rem 0;
  margin: 0;
  line-height: 1.2;
}

.title-input:focus {
  border-bottom: 2px solid #667eea;
  padding-bottom: 0.25rem;
}

.title-input.readonly {
  cursor: default;
  color: #666;
  user-select: none;
}

.title-input.readonly:focus {
  border-bottom: none;
  padding-bottom: 0.5rem;
}

.readonly-badge {
  font-size: 0.875rem;
  color: #999;
  margin-left: 0.5rem;
  padding: 0.25rem 0.5rem;
  background: #f0f0f0;
  border-radius: 3px;
}

.share-button {
  background: #52BE80;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.2s;
  font-size: 0.9rem;
}

.share-button:hover {
  background: #45A069;
}

.back-button {
  background: #667eea;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.2s;
}

.back-button:hover {
  background: #5568d3;
}

.editor-meta {
  display: flex;
  align-items: center;
  padding: 0.75rem 1.5rem;
  background: #f9f9f9;
  border-bottom: 1px solid #eee;
  font-size: 1rem;
  color: #666;
  gap: 0.75rem;
}

.editors-list {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.editor-item {
  display: flex;
  align-items: center;
  gap: 0.375rem;
}

.color-dot {
  width: 17px;
  height: 17px;
  border-radius: 50%;
  display: inline-block;
  flex-shrink: 0;
}

.editor-name {
  font-size: 1rem;
  color: #666;
}

.meta-divider {
  color: #ccc;
  margin: 0 0.25rem;
}

.last-updated {
  color: #666;
  font-size: 1rem;
}

.editor-container {
  padding: 2rem;
  min-height: 500px;
}

:deep(.ProseMirror) {
  outline: none;
  min-height: 500px;
}

:deep(.ProseMirror[contenteditable="false"]) {
  cursor: default;
  user-select: text;
}

:deep(.ProseMirror[contenteditable="false"] *) {
  cursor: default;
}

:deep(.ProseMirror p) {
  margin: 1rem 0;
}

:deep(.ProseMirror h1) {
  font-size: 2rem;
  font-weight: bold;
  margin: 1.5rem 0;
}

:deep(.ProseMirror h2) {
  font-size: 1.5rem;
  font-weight: bold;
  margin: 1.25rem 0;
}

:deep(.ProseMirror h3) {
  font-size: 1.25rem;
  font-weight: bold;
  margin: 1rem 0;
}

:deep(.ProseMirror strong) {
  font-weight: bold;
}

:deep(.ProseMirror em) {
  font-style: italic;
}

:deep(.ProseMirror code) {
  background: #f4f4f4;
  padding: 0.2rem 0.4rem;
  border-radius: 3px;
  font-family: monospace;
}

:deep(.ProseMirror pre) {
  background: #f4f4f4;
  padding: 1rem;
  border-radius: 4px;
  overflow-x: auto;
}

:deep(.ProseMirror ul, .ProseMirror ol) {
  margin: 1rem 0;
  padding-left: 2rem;
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

.share-modal {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  width: 90%;
  max-width: 600px;
  max-height: 80vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.modal-header h2 {
  margin: 0;
  color: #333;
}

.close-button {
  background: none;
  border: none;
  font-size: 2rem;
  color: #999;
  cursor: pointer;
  padding: 0;
  width: 2rem;
  height: 2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.close-button:hover {
  color: #333;
}

.share-section {
  margin-bottom: 2rem;
}

.share-section h3 {
  margin: 0 0 1rem 0;
  color: #555;
  font-size: 1.1rem;
}

.search-user {
  position: relative;
  margin-bottom: 1rem;
}

.search-input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
  box-sizing: border-box;
}

.search-results {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: white;
  border: 1px solid #ddd;
  border-radius: 4px;
  margin-top: 0.25rem;
  max-height: 200px;
  overflow-y: auto;
  z-index: 10;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.user-item {
  padding: 0.75rem;
  cursor: pointer;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.user-item:hover {
  background: #f5f5f5;
}

.user-item:last-child {
  border-bottom: none;
}

.user-name {
  font-weight: 500;
  color: #333;
}

.user-id {
  font-size: 0.875rem;
  color: #999;
}

.selected-user {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  background: #f9f9f9;
  border-radius: 4px;
  margin-bottom: 1rem;
}

.permission-select {
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 0.9rem;
}

.share-confirm-button {
  background: #52BE80;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
}

.share-confirm-button:hover {
  background: #45A069;
}

.empty-shares {
  color: #999;
  text-align: center;
  padding: 2rem;
}

.shares-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.share-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem;
  background: #f9f9f9;
  border-radius: 4px;
}

.share-info {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.share-username {
  font-weight: 500;
  color: #333;
}

.share-permission {
  font-size: 0.875rem;
  color: #666;
  padding: 0.25rem 0.5rem;
  background: #e8e8e8;
  border-radius: 3px;
}

.unshare-button {
  background: #e74c3c;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.875rem;
}

.unshare-button:hover {
  background: #c0392b;
}
</style>


