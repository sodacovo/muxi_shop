<template>
  <div class="seckill-page">
    <div class="page-header">
      <h2>限时秒杀</h2>
    </div>

    <div v-loading="loading" class="seckill-list">
      <el-row :gutter="20">
        <el-col
          v-for="item in seckillList"
          :key="item.product_id"
          :xs="12"
          :sm="8"
          :md="6"
          :lg="4"
        >
          <el-card class="seckill-card" shadow="hover">
            <div class="seckill-image">
              <img :src="fixImageUrl(item.image)" :alt="item.product_name" />
              <div v-if="item.is_valid" class="seckill-tag">秒杀中</div>
              <div v-else class="seckill-tag disabled">未开始</div>
            </div>
            <div class="seckill-info">
              <h3 class="product-name">{{ item.product_name }}</h3>
              <div class="price-row">
                <span class="seckill-price">¥{{ item.seckill_price }}</span>
                <span class="original-price">¥{{ item.original_price }}</span>
              </div>
              <div class="stock-info">
                <span>库存: {{ item.current_stock }}</span>
                <span>剩余时间: {{ item.remain_time }}</span>
              </div>
              <div class="time-info">
                <span>{{ item.start_time }} ~ {{ item.end_time }}</span>
              </div>
              <el-button
                type="danger"
                :disabled="!item.is_valid || item.current_stock <= 0"
                style="width: 100%; margin-top: 10px"
                @click="handleSeckill(item)"
              >
                {{ item.current_stock <= 0 ? '已售罄' : '立即秒杀' }}
              </el-button>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <el-empty v-if="!loading && seckillList.length === 0" description="暂无秒杀活动" />
    </div>

    <!-- 秒杀结果对话框 -->
    <el-dialog v-model="resultDialogVisible" title="秒杀结果" width="400px">
      <div class="result-content">
        <el-icon v-if="seckillResult?.status === 'success'" color="#67c23a" size="60">
          <CircleCheck />
        </el-icon>
        <el-icon v-else color="#f56c6c" size="60">
          <CircleClose />
        </el-icon>
        <p class="result-msg">{{ seckillResult?.msg }}</p>
        <p v-if="seckillResult?.trade_no" class="result-trade">
          订单号：{{ seckillResult.trade_no }}
        </p>
      </div>
      <template #footer>
        <el-button @click="resultDialogVisible = false">关闭</el-button>
        <el-button v-if="seckillResult?.status === 'success'" type="primary" @click="goToPay">
          去支付
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { CircleCheck, CircleClose } from '@element-plus/icons-vue'
import { seckillApi, goodsApi } from '@/utils/api'
import { useUserStore } from '@/stores/user'
import { useRouter } from 'vue-router'
import type { SeckillResult } from '@/types'

const router = useRouter()
const userStore = useUserStore()

const loading = ref(false)
const seckillList = ref<any[]>([])
const resultDialogVisible = ref(false)
const seckillResult = ref<SeckillResult | null>(null)

const IMAGE_BASE = 'https://www.nwq1309.shop/static/product_images/'

const fixImageUrl = (url?: string) => {
  if (!url) return '/default.png'
  let fixed = url.replace('8.138.126.24', 'www.nwq1309.shop').replace('http://', 'https://')
  if (!fixed.startsWith('https://')) fixed = IMAGE_BASE + fixed
  return fixed
}

const loadSeckillGoods = async () => {
  loading.value = true
  try {
    // 获取秒杀商品列表
    // 这里需要从后端获取秒杀商品列表，暂时用模拟数据
    // 实际应该调用商品列表接口，筛选 is_seckill=true 的商品
    const res = await goodsApi.find()
    const seckillGoods = (res.data || []).filter((g: any) => g.is_seckill)

    const product_ids = seckillGoods.map((g: any) => g.id)
    if (product_ids.length > 0) {
      const stockRes = await seckillApi.stock(product_ids)
      seckillList.value = stockRes.data?.stock_list || []
    }
  } catch (error) {
    console.error('加载秒杀数据失败', error)
  } finally {
    loading.value = false
  }
}

const handleSeckill = async (item: any) => {
  if (!userStore.isLoggedIn) {
    ElMessage.warning('请先登录')
    router.push('/login')
    return
  }

  try {
    const res = await seckillApi.submit({ product_id: item.product_id })
    seckillResult.value = res.data
    resultDialogVisible.value = true

    // 如果需要查询结果，定时刷新
    if (res.data.task_id && res.data.status === 'pending') {
      pollResult(res.data.task_id)
    }
  } catch (error: any) {
    ElMessage.error(error.message || '秒杀失败')
  }
}

const pollResult = async (task_id: string) => {
  const interval = setInterval(async () => {
    try {
      const res = await seckillApi.result(task_id)
      if (res.data.status !== 'pending') {
        seckillResult.value = res.data
        clearInterval(interval)
      }
    } catch {
      clearInterval(interval)
    }
  }, 1000)

  setTimeout(() => clearInterval(interval), 60000)
}

const goToPay = () => {
  resultDialogVisible.value = false
  if (seckillResult.value?.trade_no) {
    router.push(`/order/${seckillResult.value.trade_no}`)
  }
}

let refreshTimer: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  loadSeckillGoods()
  // 每30秒刷新秒杀库存
  refreshTimer = setInterval(loadSeckillGoods, 30000)
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})
</script>

<style scoped>
.seckill-page {
  padding: 20px 0;
}

.seckill-card {
  margin-bottom: 20px;
}

.seckill-image {
  position: relative;
  height: 200px;
  overflow: hidden;
  background: #f5f5f5;
  display: flex;
  align-items: center;
  justify-content: center;
}

.seckill-image img {
  max-width: 100%;
  max-height: 100%;
  object-fit: cover;
}

.seckill-tag {
  position: absolute;
  top: 10px;
  right: 10px;
  background: #f56c6c;
  color: #fff;
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 12px;
}

.seckill-tag.disabled {
  background: #909399;
}

.seckill-info {
  padding: 12px 0;
}

.product-name {
  font-size: 14px;
  margin-bottom: 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.price-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.seckill-price {
  color: #f56c6c;
  font-size: 20px;
  font-weight: bold;
}

.original-price {
  color: #999;
  font-size: 14px;
  text-decoration: line-through;
}

.stock-info {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #666;
  margin-bottom: 4px;
}

.time-info {
  font-size: 12px;
  color: #999;
}

.result-content {
  text-align: center;
  padding: 20px;
}

.result-msg {
  margin-top: 16px;
  font-size: 16px;
}

.result-trade {
  margin-top: 8px;
  color: #666;
}
</style>
