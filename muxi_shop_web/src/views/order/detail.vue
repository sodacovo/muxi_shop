<template>
  <div class="order-detail-page">
    <div class="page-header">
      <el-button @click="$router.back()">返回</el-button>
      <h2>订单详情</h2>
    </div>

    <div v-loading="loading">
      <el-card v-if="order" class="detail-card">
        <template #header>
          <div class="card-header">
            <span>订单号：{{ order.trade_no }}</span>
            <el-tag :type="getStatusType(order.pay_status)">
              {{ getStatusText(order.pay_status) }}
            </el-tag>
          </div>
        </template>

        <div class="detail-section">
          <h3>收货信息</h3>
          <div v-if="order.address" class="address-info">
            <p>{{ order.address.signer_name }} {{ order.address.telphone }}</p>
            <p>{{ order.address.district }} {{ order.address.signer_address }}</p>
          </div>
        </div>

        <el-divider />

        <div class="detail-section">
          <h3>商品信息</h3>
          <div class="goods-list">
            <div v-for="goods in order.goods_list" :key="goods.sku_id" class="goods-item">
              <img :src="goods.goods?.image" class="goods-thumb" />
              <div class="goods-info">
                <div class="goods-name">{{ goods.goods?.name }}</div>
                <div class="goods-price">¥{{ goods.goods?.p_price }} x {{ goods.goods_num }}</div>
              </div>
              <div class="goods-subtotal">
                ¥{{ ((goods.goods?.p_price || 0) * goods.goods_num).toFixed(2) }}
              </div>
            </div>
          </div>
        </div>

        <el-divider />

        <div class="detail-section total-section">
          <span>订单总价：</span>
          <span class="total-price">¥{{ order.total_amount }}</span>
        </div>

        <div class="detail-section">
          <h3>订单信息</h3>
          <div class="info-grid">
            <div class="info-item">
              <span class="label">下单时间：</span>
              <span class="value">{{ order.create_time }}</span>
            </div>
            <div v-if="order.update_time" class="info-item">
              <span class="label">更新时间：</span>
              <span class="value">{{ order.update_time }}</span>
            </div>
          </div>
        </div>

        <div v-if="order.pay_status === '0'" class="action-section">
          <el-button type="primary" size="large" @click="handlePay">去支付</el-button>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { orderApi } from '@/utils/api'
import type { Order } from '@/types'

const props = defineProps<{
  trade_no: string
}>()

const loading = ref(false)
const order = ref<Order | null>(null)

const loadOrderDetail = async () => {
  loading.value = true
  try {
    const res = await orderApi.detail(props.trade_no)
    order.value = res.data
  } catch (error) {
    ElMessage.error('加载订单详情失败')
  } finally {
    loading.value = false
  }
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

const handlePay = () => {
  ElMessage.info('支付功能开发中...')
}

onMounted(() => {
  loadOrderDetail()
})
</script>

<style scoped>
.order-detail-page {
  padding: 20px 0;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.detail-section {
  margin-bottom: 20px;
}

.detail-section h3 {
  margin-bottom: 12px;
  font-size: 16px;
}

.address-info p {
  margin: 4px 0;
  color: #666;
}

.goods-list {
  border: 1px solid #eee;
  border-radius: 8px;
  overflow: hidden;
}

.goods-item {
  display: flex;
  align-items: center;
  padding: 12px;
  border-bottom: 1px solid #eee;
}

.goods-item:last-child {
  border-bottom: none;
}

.goods-thumb {
  width: 80px;
  height: 80px;
  object-fit: cover;
  margin-right: 12px;
}

.goods-info {
  flex: 1;
}

.goods-name {
  margin-bottom: 8px;
}

.goods-price {
  color: #999;
  font-size: 14px;
}

.goods-subtotal {
  font-size: 16px;
  font-weight: bold;
  color: #f56c6c;
}

.total-section {
  text-align: right;
  font-size: 18px;
}

.total-price {
  color: #f56c6c;
  font-weight: bold;
  font-size: 24px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.info-item .label {
  color: #999;
}

.action-section {
  margin-top: 30px;
  text-align: center;
}
</style>
