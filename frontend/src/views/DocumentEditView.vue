<template>
  <div class="document-edit-container">
    <div v-if="documentStore.loading" class="loading">加载中...</div>
    
    <div v-else-if="!documentStore.currentDocument" class="error">
      文档不存在
    </div>
    
    <div v-else class="editor-wrapper">
      <div class="editor-header">
        <h1>{{ documentStore.currentDocument.title }}</h1>
        <button @click="goBack" class="back-button">返回</button>
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
import { htmlToMarkdown } from '@/utils/markdown'

const route = useRoute()
const router = useRouter()
const documentStore = useDocumentStore()

const documentId = ref<number | null>(null)
const lastMarkdown = ref<string>('')
const currentVersion = ref<number>(0)
const isApplyingOperation = ref(false)
const isSendingOperation = ref(false)
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
    if (editor.value && documentStore.currentDocument.content) {
      isApplyingOperation.value = true
      editor.value.commands.setContent(documentStore.currentDocument.content)
      const html = editor.value.getHTML()
      lastMarkdown.value = htmlToMarkdown(html)
      currentVersion.value = documentStore.currentDocument.current_version
      isApplyingOperation.value = false
    }
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

.editor-header h1 {
  margin: 0;
  color: #333;
}

.back-button {
  background: #667eea;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
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


