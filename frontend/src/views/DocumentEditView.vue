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
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useEditor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import { useDocumentStore } from '@/stores/document'

const route = useRoute()
const router = useRouter()
const documentStore = useDocumentStore()

const editor = useEditor({
  extensions: [StarterKit],
  content: '',
  editorProps: {
    attributes: {
      class: 'prose prose-sm sm:prose lg:prose-lg xl:prose-2xl mx-auto focus:outline-none',
    },
  },
})

onMounted(async () => {
  const documentId = parseInt(route.params.id as string)
  const result = await documentStore.fetchDocument(documentId)
  
  if (result.success && documentStore.currentDocument) {
    // 加载文档内容到编辑器
    if (editor.value && documentStore.currentDocument.content) {
      editor.value.commands.setContent(documentStore.currentDocument.content)
    }
  } else {
    alert(result.message || '加载文档失败')
    router.push('/documents')
  }
})

onBeforeUnmount(() => {
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


