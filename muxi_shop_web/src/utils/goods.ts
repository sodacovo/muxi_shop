import { cartApi } from './api'

export const toGoodsDetail = (skuId: string) => {
  window.open(`/detail/${skuId}`)
}

export const addCartData = async (skuId: string, nums: number, isDelete = 0) => {
  try {
    await cartApi.add({ sku_id: skuId, nums })
  } catch { /* interceptor */ }
}
