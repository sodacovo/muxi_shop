<template>
  <div>
    <Shortcut />
    <div class="order-pay">
      <div class="header">
        <div class="title clearfix">
          <div class="logo fl"><img src="@/assets/images/logo/logo-big.png" alt="" style="height:50px;" /></div>
          <div class="shop-name fl">木犀商城</div>
          <div class="page-title fl">收银台</div>
        </div>
      </div>
      <div class="order-info" v-if="orderData.trade_no">
        <div class="order-num">订单提交成功，请尽快付款！订单号：<span>{{ orderData.trade_no }}</span></div>
        <div class="goods-list">
          <h3>商品清单</h3>
          <table>
            <thead><tr><th width="20%">商品ID</th><th width="30%">商品名称</th><th width="20%">数量</th><th width="30%">单价（元）</th></tr></thead>
            <tbody>
              <tr v-for="g in goodsList" :key="g.sku_id">
                <td>{{ g.sku_id }}</td>
                <td>{{ g.name || '未知商品' }}</td>
                <td>{{ g.goods_num }}</td>
                <td>￥{{ g.jd_price || '0.00' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="pay-mode">
          <div class="total-amount">应付金额：<span class="pay-count">{{ orderData.order_amount }}</span>元</div>
          <div class="pay-option" :class="{ selected: selectedPayType === 'alipay' }" @click="selectPayType('alipay')">
            <img src="@/assets/images/order/alipay.png" alt="支付宝" style="width:40px;height:40px;vertical-align:middle;margin-right:10px;" />
            支付宝支付
            <span v-if="selectedPayType === 'alipay'" class="selected-tag">已选择</span>
          </div>
          <div class="pay-option" :class="{ selected: selectedPayType === 'wechat' }" @click="selectPayType('wechat')">
            <img src="@/assets/images/order/wechat.png" alt="微信" style="width:40px;height:40px;vertical-align:middle;margin-right:10px;" />
            微信支付（扫码）
            <span v-if="selectedPayType === 'wechat'" class="selected-tag">已选择</span>
          </div>
        </div>
        <div v-if="selectedPayType === 'wechat'" class="wechat-qrcode-area">
          <div class="qrcode-container">
            <div v-if="!qrcodeUrl" class="loading">生成支付二维码中...</div>
            <img v-else :src="qrcodeUrl" alt="微信支付二维码" style="width:200px;height:200px;" />
          </div>
          <div class="pay-status" :style="{ color: statusColor }">{{ payStatusText }}</div>
        </div>
        <div class="pay-order">
          <button class="pay-btn" @click="handlePay" :disabled="isLoading">立即支付</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import Shortcut from '@/components/common/Shortcut.vue'
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { orderApi, payApi } from '@/utils/api'

const route = useRoute()
const router = useRouter()
const tradeNo = (route.query.tradeNo as string) || ''
const orderData = ref<any>({})
const goodsList = ref<any[]>([])
const selectedPayType = ref('alipay')
const qrcodeUrl = ref('')
const payStatusText = ref('')
const statusColor = ref('#333')
const isLoading = ref(false)
let pollTimer: ReturnType<typeof setInterval> | null = null

onMounted(async () => {
  if (!tradeNo) { alert('订单号不存在'); router.push('/cart'); return }
  try {
    const res = await orderApi.detail(tradeNo)
    orderData.value = res.data || {}
    goodsList.value = res.data?.goods || []
  } catch { /* interceptor */ }
})
onUnmounted(() => { if (pollTimer) clearInterval(pollTimer) })

const selectPayType = (type: string) => {
  selectedPayType.value = type
  if (type === 'wechat' && !qrcodeUrl.value) generateWechatQrcode()
}

const generateWechatQrcode = async () => {
  payStatusText.value = '生成支付二维码中...'
  statusColor.value = '#333'
  try {
    const res = await payApi.wechatQrcode({ trade_no: tradeNo })
    const url = URL.createObjectURL(res as unknown as Blob)
    qrcodeUrl.value = url
    startPoll()
  } catch {
    payStatusText.value = '生成二维码失败'
    statusColor.value = 'red'
  }
}

const startPoll = () => {
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = setInterval(async () => {
    try {
      const res = await payApi.wechatQuery({ trade_no: tradeNo })
      if (res.data?.pay_status === '2') {
        clearInterval(pollTimer!)
        payStatusText.value = '支付成功！正在跳转...'
        statusColor.value = 'green'
        setTimeout(() => router.push({ path: '/profile', query: { activeIndex: '3' } }), 1500)
      }
    } catch { /* ignore */ }
  }, 3000)
}

const handlePay = async () => {
  if (isLoading.value) return
  isLoading.value = true
  if (selectedPayType.value === 'alipay') {
    try {
      const res = await payApi.alipay({ tradeNo, orderAmount: orderData.value.order_amount || '0' })
      if (res.alipay) window.location.href = res.alipay
      else throw new Error()
    } catch { alert('生成支付链接失败') }
  } else {
    if (!qrcodeUrl.value) generateWechatQrcode()
    else alert('请用微信扫描上方二维码')
  }
  isLoading.value = false
}
</script>

<style lang="less" scoped>
.order-pay { width: 1200px; margin: 0 auto; padding-bottom: 50px; }
.header { height: 100px; border-bottom: 1px solid #eee; display: flex; align-items: center; }
.title { display: flex; align-items: center; gap: 15px; }
.shop-name { font-size: 28px; color: #e93854; font-weight: 700; }
.page-title { font-size: 20px; color: #333; }
.order-info { padding: 30px 0; }
.order-num { font-size: 20px; margin-bottom: 25px; span { color: #e93854; font-weight: 700; } }
.goods-list { border: 1px solid #eee; border-radius: 5px; padding: 20px; margin-bottom: 30px; h3 { font-size: 16px; margin-bottom: 15px; } table { width: 100%; border-collapse: collapse; text-align: center; th { background: #f5f5f5; padding: 12px 0; } td { padding: 15px 0; border: 1px solid #eee; } } }
.pay-mode { font-size: 16px; margin-bottom: 25px; }
.total-amount { margin-bottom: 20px; .pay-count { color: #e93854; font-size: 22px; font-weight: 700; margin: 0 5px; } }
.pay-option { display: inline-block; padding: 12px 20px; border: 1px solid #ddd; border-radius: 5px; margin-right: 30px; margin-bottom: 15px; cursor: pointer; &:hover { border-color: #108ee9; } &.selected { border-color: #108ee9; } .selected-tag { background: #108ee9; color: #fff; font-size: 12px; padding: 2px 8px; border-radius: 12px; margin-left: 10px; } }
.wechat-qrcode-area { border: 1px solid #eee; border-radius: 5px; padding: 25px; text-align: center; margin-bottom: 30px; .loading { color: #666; padding: 60px 0; } }
.pay-status { margin-top: 10px; font-size: 16px; }
.pay-order { text-align: right; margin-right: 200px; }
.pay-btn { width: 135px; height: 38px; background-color: #e93854; color: #fff; border: none; border-radius: 5px; font-size: 16px; cursor: pointer; &:hover { background-color: #d40a0a; } &:disabled { background-color: #ccc; cursor: not-allowed; } }
.clearfix::after { content: ''; display: block; clear: both; }
.fl { float: left; }
</style>
