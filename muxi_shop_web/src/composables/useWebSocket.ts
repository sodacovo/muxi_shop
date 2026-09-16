import { ref, onUnmounted } from 'vue'
import type { SeckillResult } from '@/types'

export function useWebSocket() {
  const ws = ref<WebSocket | null>(null)
  const connected = ref(false)
  const seckillResult = ref<SeckillResult | null>(null)

  const WS_URL = import.meta.env.VITE_WS_TORNADO_URL || 'ws://127.0.0.1:8666'

  function connect(taskId: string) {
    disconnect()
    ws.value = new WebSocket(`${WS_URL}/ws/seckill/${taskId}/`)

    ws.value.onopen = () => {
      connected.value = true
    }
    ws.value.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as SeckillResult
        seckillResult.value = data
      } catch {
        // ignore parse error
      }
    }
    ws.value.onclose = () => {
      connected.value = false
    }
    ws.value.onerror = () => {
      connected.value = false
    }
  }

  function disconnect() {
    if (ws.value) {
      ws.value.close()
      ws.value = null
      connected.value = false
    }
  }

  onUnmounted(disconnect)

  return { ws, connected, seckillResult, connect, disconnect }
}
