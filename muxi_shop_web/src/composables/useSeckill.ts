import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import router from '@/router'
import { useUserStore } from '@/stores/user'
import { submitSeckill, getSeckillResult } from '@/api/modules/seckill'
import { useWebSocket } from './useWebSocket'

export function useSeckill(productId: number) {
  const userStore = useUserStore()
  const ws = useWebSocket()
  const isSubmitting = ref(false)
  const currentResult = ref<Awaited<ReturnType<typeof getSeckillResult>>['data'] | null>(null)

  async function handleSeckill() {
    if (!userStore.isLoggedIn) {
      ElMessage.warning('请先登录')
      router.push({ name: 'Login', query: { redirect: router.currentRoute.value.fullPath } })
      return
    }

    isSubmitting.value = true
    try {
      const res = await submitSeckill({ product_id: productId })
      const submitData = res.data

      if (submitData.mode === 'rabbitmq') {
        // WebSocket 模式：连接 Tornado WS 实时接收结果
        ws.connect(submitData.task_id)
        let checked = false
        const checkResult = () => {
          if (checked) return
          if (ws.seckillResult.value) {
            checked = true
            const r = ws.seckillResult.value
            currentResult.value = r
            if (r.status === 'success') {
              ElMessage.success('恭喜，抢购成功！')
              router.push(`/pay/${r.trade_no}`)
            } else {
              ElMessage.warning(r.msg || '抢购失败')
            }
            ws.disconnect()
          } else {
            setTimeout(checkResult, 500)
          }
        }
        setTimeout(checkResult, 500)
      } else {
        // Celery 轮询模式
        const r = await pollResult(submitData.task_id)
        currentResult.value = r
        if (r.status === 'success') {
          ElMessage.success('恭喜，抢购成功！')
          router.push(`/pay/${r.trade_no}`)
        } else {
          ElMessage.warning(r.msg || '抢购失败')
        }
      }
    } catch (e: any) {
      ElMessage.error(e.message || '提交失败')
    } finally {
      isSubmitting.value = false
    }
  }

  async function pollResult(taskId: string, timeout = 30000) {
    const start = Date.now()
    return new Promise<NonNullable<typeof currentResult.value>>((resolve, reject) => {
      const timer = setInterval(async () => {
        try {
          const res = await getSeckillResult(taskId)
          const r = res.data
          if (r.status !== 'pending') {
            clearInterval(timer)
            resolve(r)
          }
        } catch {
          clearInterval(timer)
          reject(new Error('查询失败'))
        }
        if (Date.now() - start > timeout) {
          clearInterval(timer)
          reject(new Error('查询超时'))
        }
      }, 1000)
    })
  }

  return {
    isSubmitting,
    currentResult,
    handleSeckill,
    pollResult,
  }
}
