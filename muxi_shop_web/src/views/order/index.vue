<template>
  <div class="order-page">
    <div class="page-header">
      <h2>我的订单</h2>
    </div>

    <div class="order-tabs">
      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <el-tab-pane label="全部" name="-1" />
        <el-tab-pane label="待支付" name="0" />
        <el-tab-pane label="已支付" name="1" />
        <el-tab-pane label="已完成" name="2" />
      </el-tabs>
    </div>

    <div v-loading="loading">
      <el-empty v-if="!loading && orderList.length === 0" description="暂无订单">
        <el-button type="primary" @click="$router.push('/')">去购物</el-button>
      </el-empty>

      <div v-else class="order-list">
        <el-card v-for="order in orderList" :key="order.trade_no" class="order-card">
          <template #header>
            <div class="order-header">
              <span>订单号：{{ order.trade_no }}</span>
              <span>下单时间：{{ order.create_time }}</span>
              <el-tag :type="getStatusType(order.pay_status)">
                {{ getStatusText(order.pay_status) }}
              </el-tag>
            </div>
          </template>

          <div class="order-goods">
            <div v-for="goods in order.goods_list" :key="goods.sku_id" class="goods-item">
              <img :src="goods.goods?.image" class="goods-thumb" />
              <span class="goods-name">{{ goods.goods?.name }}</span>
              <span class="goods-price">¥{{ goods.goods?.p_price || goods.goods?.price }}</span>
              <span class="goods-num">x{{ goods.goods_num }}</span>
            </div>
          </div>

          <div class="order-footer">
            <div class="order-info">
              <span v-if="order.address">
                收货人：{{ order.address.signer_name }}，
                {{ order.address.telphone }}
              </span>
            </div>
            <div class="order-actions">
              <span class="total-amount">
                总计：<strong>¥{{ order.total_amount }}</strong>
              </span>
              <el-button v-if="order.pay_status === '0'" type="primary" @click="handlePay(order)">
                去支付
              </el-button>
              <el-button @click="goToDetail(order.trade_no)">查看详情</el-button>
            </div>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { orderApi } from '@/utils/api'
import type { Order } from '@/types'

const router = useRouter()

const loading = ref(false)
const orderList = ref<Order[]>([])
const activeTab = ref('-1')

const loadOrders = async () => {
  loading.value = true
  try {
    const payStatus = activeTab.value === '-1' ? undefined : activeTab.value
    const res = await orderApi.list(payStatus)
    orderList.value = res.data || []
  } catch (error) {
    ElMessage.error('加载订单失败')
  } finally {
    loading.value = false
  }
}

const handleTabChange = () => {
  loadOrders()
}

const getStatusType = (status?: string) => {
  const map: Record<string, string> = {
    '0': 'warning',
    '1': 'success',
    '2': 'info',
  }
  return map[status || '0'] || 'info'
}

const getStatusText = (status?: string) => {
  const map: Record<string, string> = {
    '0': '待支付',
    '1': '已支付',
    '2': '已完成',
  }
  return map[status || '0'] || '未知'
}

const handlePay = (order: Order) => {
  ElMessage.info('支付功能开发中...')
}

const goToDetail = (trade_no: string) => {
  router.push(`/order/${trade_no}`)
}

onMounted(() => {
  loadOrders()
})
</script>

<style scoped>
.order-page {
  padding: 20px 0;
}

.order-tabs {
  margin-bottom: 20px;
}

.order-card {
  margin-bottom: 20px;
}

.order-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.order-goods {
  margin-bottom: 20px;
}

.goods-item {
  display: flex;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid #f5f5f5;
}

.goods-item:last-child {
  border-bottom: none;
}

.goods-thumb {
  width: 60px;
  height: 60px;
  object-fit: cover;
  margin-right: 12px;
}

.goods-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.goods-price {
  width: 80px;
  text-align: center;
}

.goods-num {
  width: 50px;
  text-align: right;
  color: #999;
}

.order-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 10px;
  border-top: 1px solid #eee;
}

.total-amount {
  font-size: 16px;
}

.total-amount strong {
  color: #f56c6c;
  font-size: 20px;
}

.order-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}
</style>
