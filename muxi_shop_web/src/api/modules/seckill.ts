import { request } from '@/utils/request'
import type { SeckillSubmit, SeckillResult, SeckillStock, BackendResponse } from '@/types'

/** 提交秒杀（⚠️ 字段是 product_id，不是 goods_id） */
export function submitSeckill(data: SeckillSubmit) {
  return request.post<BackendResponse<SeckillSubmitResult>>('/seckill/submit/', data)
}

/** 查询秒杀结果 */
export function getSeckillResult(taskId: string) {
  return request.get<BackendResponse<SeckillResult>>('/seckill/result/', { task_id: taskId })
}

/** 批量获取秒杀库存 */
export function getSeckillStock(productIds: number[]) {
  return request.get<BackendResponse<{ stock_list: SeckillStock[]; total_count: number; update_time: string }>>(
    `/seckill/stock/`,
    { product_ids: productIds.join(',') }
  )
}

export interface SeckillSubmitResult {
  task_id: string
  mode: 'rabbitmq' | 'celery'
  trade_no: string
  msg: string
  expire_seconds: number
  code: number
}
