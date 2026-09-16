<template>
  <div>
    <Shortcut />
    <div class="order-detail">
      <div class="header">
        <div class="title">
          <div class="logo fl"><img src="@/assets/images/logo/logo-big.png" alt="" style="height:50px;" /></div>
          <div class="shop-name fl">木犀商城</div>
          <div class="page-title fl">订单详情</div>
        </div>
      </div>
      <div class="content">
        <div class="section-title">订单信息</div>
        <div class="order-info" v-if="orderData.trade_no">
          <p>订单号：<span>{{ orderData.trade_no }}</span></p>
          <p>订单金额：<span class="price">￥{{ orderData.order_amount }}</span></p>
          <p>订单状态：
            <el-tag :type="payStatusType(orderData.pay_status)">{{ payStatusText(orderData.pay_status) }}</el-tag>
          </p>
        </div>
        <div class="section-title">收货地址</div>
        <div class="address-info" v-if="addressData">
          <p>{{ addressData.signer_name }} {{ addressData.telphone }}</p>
          <p>{{ addressData.district }} {{ addressData.signer_address }}</p>
        </div>
        <div class="section-title">商品列表</div>
        <el-table :data="goodsList" border>
          <el-table-column prop="sku_id" label="商品ID" width="120" />
          <el-table-column prop="name" label="商品名称" />
          <el-table-column prop="goods_num" label="数量" width="80" />
          <el-table-column prop="jd_price" label="单价" width="100">
            <template #default="{ row }">￥{{ row.jd_price }}</template>
          </el-table-column>
          <el-table-column label="小计" width="100">
            <template #default="{ row }">￥{{ (row.jd_price * row.goods_num).toFixed(2) }}</template>
          </el-table-column>
        </el-table>
        <div class="action-bar" v-if="orderData.pay_status === '0'">
          <el-button type="primary" @click="goPay">去支付</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import Shortcut from '@/components/common/Shortcut.vue'
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { orderApi } from '@/utils/api'

const route = useRoute()
const router = useRouter()
const trade_no = route.params.trade_no as string
const orderData = ref<any>({})
const goodsList = ref<any[]>([])
const addressData = ref<any>(null)

const payStatusText = (s: string) => ({ '0': '待支付', '1': '已支付', '2': '已完成', '3': '已取消' }[s] || s)
const payStatusType = (s: string) => ({ '0': 'warning', '1': 'success', '2': 'success', '3': 'info' }[s] || '')

onMounted(async () => {
  try {
    const res = await orderApi.detail(trade_no)
    orderData.value = res.data || {}
    goodsList.value = res.data?.goods || []
    addressData.value = res.data?.address || null
  } catch { /* interceptor */ }
})

const goPay = () => {
  router.push({ path: '/Order/Pay', query: { tradeNo: trade_no } })
}
</script>

<style lang="less" scoped>
.order-detail { width: 1200px; margin: 0 auto; padding-bottom: 50px; }
.header { height: 100px; border-bottom: 1px solid #eee; display: flex; align-items: center; .title { display: flex; align-items: center; gap: 15px; } .shop-name { font-size: 28px; color: #e93854; font-weight: 700; } .page-title { font-size: 20px; color: #333; } }
.content { padding: 30px 0; .section-title { font-size: 16px; font-weight: 600; color: #333; margin: 20px 0 10px; border-left: 3px solid #e93854; padding-left: 10px; } }
.order-info, .address-info { background: #f9f9f9; padding: 15px; border-radius: 4px; p { margin: 5px 0; color: #666; span { color: #333; } .price { color: #e93854; font-size: 18px; font-weight: 700; } } }
.action-bar { text-align: right; margin-top: 20px; }
</style>
