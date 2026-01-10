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
            class="title-input"
            type="text"
          />
        </div>
        <button @click="goBack" class="back-button">返回</button>
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
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useEditor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import { useDocumentStore } from '@/stores/document'
import { documentAPI } from '@/services/api'
import { htmlToMarkdown, markdownToHtml } from '@/utils/markdown'

const route = useRoute()
const router = useRouter()
const documentStore = useDocumentStore()

const documentId = ref<number | null>(null)
const lastMarkdown = ref<string>('')
const currentVersion = ref<number>(0)
const isApplyingOperation = ref(false)
const isSendingOperation = ref(false)
const documentTitle = ref<string>('')
const editors = ref<Array<{ user_id: number; username: string; color: string; last_edit_time: string | null }>>([])
const lastUpdated = ref<string>('')
let debounceTimer: ReturnType<typeof setTimeout> | null = null

const editor = useEditor({
  extensions: [StarterKit],
  content: '',
  editorProps: {
    attributes: {
      class: 'prose prose-sm sm:prose lg:prose-lg xl:prose-2xl mx-auto focus:outline-none',
    },
  },
  onUpdate: ({ editor }) => {
    if (isApplyingOperation.value) {
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

onMounted(async () => {
  const id = parseInt(route.params.id as string)
  documentId.value = id
  
  const result = await documentStore.fetchDocument(id)
  
  if (result.success && documentStore.currentDocument) {
    documentTitle.value = documentStore.currentDocument.title
    if (editor.value && documentStore.currentDocument.content) {
      isApplyingOperation.value = true
      const markdown = documentStore.currentDocument.content
      const html = markdownToHtml(markdown)
      editor.value.commands.setContent(html)
      lastMarkdown.value = markdown
      currentVersion.value = documentStore.currentDocument.current_version
      isApplyingOperation.value = false
    }
    await loadEditors()
  } else {
    alert(result.message || '加载文档失败')
    router.push('/documents')
  }
})

onBeforeUnmount(() => {
  if (debounceTimer) {
    clearTimeout(debounceTimer)
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

.header-left {
  flex: 1;
}

.title-input {
  width: 100%;
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
</style>


