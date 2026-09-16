<template>
  <div class="find-goods">
    <img class="bg-img" src="@/assets/images/find-goods.png" alt="背景" />
    <div class="scroll-container">
      <SeamlessScroll v-if="goodsList.length" :list="goodsList" direction="left" :step="1" :hover="true" class="scroll">
        <ul class="scroll-list">
          <li v-for="item in goodsList" :key="item.id" class="item" @click="handleGoodsClick(item)">
            <div class="seckill-tag" v-if="item.is_seckill && isSeckillValid(item)">秒杀</div>
            <img :src="fixImageUrl(item.image)" class="goods-img" @error="e => (e.target as HTMLImageElement).src = '/default.png'" />
            <span class="name">{{ item.name }}</span>
            <span class="price" v-if="item.is_seckill && isSeckillValid(item)">秒杀价：{{ item.seckill_price }}元</span>
            <span class="price" v-else>￥{{ item.jd_price }}</span>
          </li>
        </ul>
      </SeamlessScroll>
    </div>

    <!-- 秒杀弹窗 -->
    <div class="seckill-modal" v-if="showSeckillModal">
      <div class="modal-mask" @click="closeSeckillModal"></div>
      <div class="modal-content">
        <div class="modal-close" @click="closeSeckillModal">×</div>
        <h3>秒杀商品</h3>
        <div class="modal-goods-info">
          <img :src="fixImageUrl(currentSeckillGoods.image) || '/default.png'" class="modal-img" />
          <div>
            <p>{{ currentSeckillGoods.name }}</p>
            <p>原价：<del>{{ currentSeckillGoods.jd_price }}元</del></p>
            <p>秒杀价：<span class="seckill-price">{{ currentSeckillGoods.seckill_price }}元</span></p>
          </div>
        </div>
        <div class="modal-stock">
          <span>剩余库存：{{ currentStock }}</span>
          <span>倒计时：{{ countdownText }}</span>
        </div>
        <div class="modal-btn">
          <button class="seckill-btn" @click="handleSubmitSeckill" :disabled="isBtnDisabled">{{ btnText }}</button>
          <p class="result-tip" :class="resultClass">{{ resultTip }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import SeamlessScroll from '@/components/common/SeamlessScroll.vue'
import { goodsApi } from '@/utils/api'
import { submitSeckill as apiSubmitSeckill, getSeckillStock } from '@/api/modules/seckill'
import { settings } from '@/config/settings'

const router = useRouter()
const goodsList = ref<any[]>([])
const showSeckillModal = ref(false)
const currentSeckillGoods = ref<any>({})
const currentStock = ref(0)
const countdownText = ref('')
const btnText = ref('立即秒杀')
const isBtnDisabled = ref(false)
const resultTip = ref('')
const resultClass = ref('')
const timers = ref<any>({})

const IMAGE_BASE = 'https://www.nwq1309.shop/static/product_images/'

const fixImageUrl = (url?: string) => {
  if (!url) return '/default.png'
  let fixed = url.replace('8.138.126.24', 'www.nwq1309.shop').replace('http://', 'https://')
  if (!fixed.startsWith('https://')) fixed = IMAGE_BASE + fixed
  return fixed
}

const isSeckillValid = (item: any) => {
  if (item.is_seckill_valid !== undefined) return item.is_seckill_valid
  if (!item.is_seckill) return false
  const parseTime = (t: string) => t ? new Date(t) : null
  const now = new Date()
  const start = parseTime(item.seckill_start_time)
  const end = parseTime(item.seckill_end_time)
  return !!(start && end && now >= start && now <= end)
}

onMounted(async () => {
  try {
    const res = await goodsApi.find()
    const data: any[] = res.data || []
    goodsList.value = data.length <= 8 ? [...data, ...data] : [...data.slice(0, 8), ...data.slice(0, 8)]
  } catch {}
})

const handleGoodsClick = async (item: any) => {
  if (!item.is_seckill || !isSeckillValid(item)) {
    router.push(`/detail/${item.id || item.sku_id}`)
    return
  }
  currentSeckillGoods.value = item
  showSeckillModal.value = true
  await loadStock(item.id || item.sku_id)
  startCountdown()
}

const loadStock = async (id: number) => {
  try {
    const res = await getSeckillStock([id])
    if (res.data?.stock_list?.[0]) {
      currentStock.value = res.data.stock_list[0].current_stock
    }
  } catch {}
}

const startCountdown = () => {
  const end = new Date(currentSeckillGoods.value.seckill_end_time || Date.now() + 3600000)
  const tick = () => {
    const diff = end.getTime() - Date.now()
    if (diff <= 0) { countdownText.value = '已结束'; return }
    const h = Math.floor(diff / 3600000).toString().padStart(2, '0')
    const m = Math.floor((diff % 3600000) / 60000).toString().padStart(2, '0')
    const s = Math.floor((diff % 60000) / 1000).toString().padStart(2, '0')
    countdownText.value = `${h}:${m}:${s}`
  }
  tick()
  timers.value.cd = setInterval(tick, 1000)
}

const handleSubmitSeckill = async () => {
  if (currentStock.value <= 0) { resultTip.value = '库存已耗尽'; resultClass.value = 'fail'; return }
  isBtnDisabled.value = true
  btnText.value = '处理中...'
  resultTip.value = '秒杀请求已提交...'
  resultClass.value = 'processing'
  try {
    const res = await apiSubmitSeckill({ product_id: Number(currentSeckillGoods.value.id) })
    if (res.data?.trade_no) {
      resultTip.value = '秒杀成功！去支付'
      resultClass.value = 'success'
      btnText.value = '秒杀成功'
      setTimeout(() => router.push({ path: '/Order/Pay', query: { tradeNo: res.data.trade_no } }), 1500)
    } else {
      resultTip.value = res.data?.msg || '秒杀失败'
      resultClass.value = 'fail'
      btnText.value = '立即秒杀'
      isBtnDisabled.value = false
    }
  } catch {
    resultTip.value = '秒杀失败，请重试'
    resultClass.value = 'fail'
    btnText.value = '立即秒杀'
    isBtnDisabled.value = false
  }
}

const closeSeckillModal = () => {
  showSeckillModal.value = false
  if (timers.value.cd) clearInterval(timers.value.cd)
  if (timers.value.stock) clearInterval(timers.value.stock)
}
</script>

<style lang="less" scoped>
.find-goods {
  display: flex;
  gap: 10px;
  width: 1190px;
  margin: 0 auto;
}
.bg-img {
  width: 190px;
  height: 260px;
  object-fit: cover;
  border-radius: 12px;
  flex-shrink: 0;
}
.scroll-container {
  flex: 1;
  height: 260px;
  overflow: hidden;
  background: #fff;
  border-radius: 12px;
}
.scroll {
  width: 100%;
  height: 100%;
}
.scroll-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  width: max-content;
  height: 100%;
  align-items: center;
}
.item {
  flex-shrink: 0;
  width: 220px;
  height: 240px;
  margin: 0 15px;
  background: #fafafa;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  position: relative;
  cursor: pointer;
  .seckill-tag {
    position: absolute;
    top: 10px;
    left: 10px;
    background: #ff4400;
    color: #fff;
    font-size: 12px;
    padding: 2px 6px;
    border-radius: 4px;
    z-index: 1;
  }
  .goods-img {
    width: 150px;
    height: 150px;
    border-radius: 12px;
    object-fit: cover;
  }
  .name {
    width: 180px;
    margin-top: 8px;
    font-size: 14px;
    color: #333;
    text-align: center;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
  }
  .price {
    margin-top: 8px;
    font-size: 16px;
    font-weight: 700;
    color: #e4393c;
  }
}
.seckill-modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 1000;
  .modal-mask {
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.5);
  }
  .modal-content {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 90%;
    max-width: 500px;
    background: #fff;
    border-radius: 12px;
    padding: 20px;
    .modal-close {
      position: absolute;
      top: 15px;
      right: 15px;
      font-size: 24px;
      cursor: pointer;
      color: #999;
    }
    h3 {
      text-align: center;
      margin-bottom: 15px;
    }
    .modal-goods-info {
      display: flex;
      gap: 15px;
      margin-bottom: 15px;
      .modal-img {
        width: 120px;
        height: 120px;
        border-radius: 8px;
        object-fit: cover;
      }
      .seckill-price {
        color: #e4393c;
        font-weight: 700;
        font-size: 18px;
      }
    }
    .modal-stock {
      display: flex;
      justify-content: space-between;
      margin-bottom: 15px;
    }
    .seckill-btn {
      width: 100%;
      height: 44px;
      background: #ff4400;
      color: #fff;
      border: none;
      border-radius: 22px;
      font-size: 16px;
      cursor: pointer;
      &:disabled {
        background: #ccc;
      }
    }
    .result-tip {
      text-align: center;
      margin-top: 10px;
      font-size: 14px;
      &.success {
        color: #67c23a;
      }
      &.fail {
        color: #f56c6c;
      }
      &.processing {
        color: #e6a23c;
      }
    }
  }
}
</style>
