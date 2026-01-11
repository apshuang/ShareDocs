import { ref, type Ref } from 'vue'

export interface WebSocketMessage {
  type: string
  data?: any
}

export class DocumentWebSocket {
  private ws: WebSocket | null = null
  private documentId: number | null = null
  private token: string | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000
  private isManualClose = false
  private messageHandlers: Map<string, (data: any) => void> = new Map()
  
  public connected = ref(false)
  public currentVersion = ref(0)

  constructor() {
    this.token = localStorage.getItem('access_token')
  }

  connect(documentId: number): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.token) {
        reject(new Error('未找到认证令牌'))
        return
      }

      this.documentId = documentId
      this.isManualClose = false

      const wsUrl = this.getWebSocketUrl(documentId, this.token)
      
      try {
        this.ws = new WebSocket(wsUrl)

        this.ws.onopen = () => {
          console.log('WebSocket 连接已建立')
          this.connected.value = true
          this.reconnectAttempts = 0
          this.send({ type: 'subscribe' })
          resolve()
        }

        this.ws.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data)
            this.handleMessage(message)
          } catch (error) {
            console.error('解析 WebSocket 消息失败:', error)
          }
        }

        this.ws.onerror = (error) => {
          console.error('WebSocket 错误:', error)
          reject(error)
        }

        this.ws.onclose = () => {
          this.connected.value = false
          console.log('WebSocket 连接已关闭')
          
          if (!this.isManualClose && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++
            const delay = this.reconnectDelay * this.reconnectAttempts
            console.log(`${delay}ms 后尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})`)
            setTimeout(() => {
              if (this.documentId) {
                this.connect(this.documentId).catch(console.error)
              }
            }, delay)
          }
        }
      } catch (error) {
        reject(error)
      }
    })
  }

  disconnect() {
    this.isManualClose = true
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    this.connected.value = false
  }

  send(message: WebSocketMessage) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message))
    } else {
      console.warn('WebSocket 未连接，无法发送消息')
    }
  }

  on(messageType: string, handler: (data: any) => void) {
    this.messageHandlers.set(messageType, handler)
  }

  off(messageType: string) {
    this.messageHandlers.delete(messageType)
  }

  private handleMessage(message: WebSocketMessage) {
    const handler = this.messageHandlers.get(message.type)
    if (handler) {
      handler(message.data)
    } else {
      console.log('未处理的消息类型:', message.type, message.data)
    }
  }

  private getWebSocketUrl(documentId: number, token: string): string {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
    const url = new URL(apiBaseUrl)
    const host = import.meta.env.VITE_WS_HOST || url.host
    return `${protocol}//${host}/ws?token=${encodeURIComponent(token)}&document_id=${documentId}`
  }
}

