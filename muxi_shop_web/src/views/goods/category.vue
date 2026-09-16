<template>
  <div class="category-page">
    <div class="category-header">
      <h2>分类商品</h2>
    </div>

    <div v-loading="loading" class="goods-grid">
      <el-row :gutter="20">
        <el-col
          v-for="goods in goodsList"
          :key="goods.sku_id"
          :xs="12"
          :sm="8"
          :md="6"
          :lg="4"
          class="goods-col"
        >
          <el-card
            :body-style="{ padding: '0px' }"
            shadow="hover"
            @click="goToDetail(goods.sku_id)"
          >
            <div class="goods-image">
              <img :src="fixImageUrl(goods.image)" :alt="goods.name" />
            </div>
            <div class="goods-info">
              <h3 class="goods-name">{{ goods.name }}</h3>
              <div class="goods-price">
                <span class="current-price">¥{{ goods.p_price || goods.price }}</span>
                <span v-if="goods.jd_price" class="original-price">¥{{ goods.jd_price }}</span>
              </div>
              <div class="goods-shop">{{ goods.shop_name }}</div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <el-empty v-if="!loading && goodsList.length === 0" description="暂无商品" />
    </div>

    <div class="pagination">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next"
        @current-change="handlePageChange"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { goodsApi } from '@/utils/api'
import type { Goods } from '@/types'

const props = defineProps<{
  category_id: string
}>()

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const goodsList = ref<Goods[]>([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

const IMAGE_BASE = 'https://www.nwq1309.shop/static/product_images/'

const fixImageUrl = (url?: string) => {
  if (!url) return '/default.png'
  let fixed = url.replace('8.138.126.24', 'www.nwq1309.shop').replace('http://', 'https://')
  if (!fixed.startsWith('https://')) fixed = IMAGE_BASE + fixed
  return fixed
}

const loadGoods = async () => {
  loading.value = true
  try {
    const res = await goodsApi.category({
      category_id: Number(props.category_id),
      page: currentPage.value,
    })
    goodsList.value = res.data || []
    total.value = goodsList.value.length
  } catch (error) {
    ElMessage.error('加载商品失败')
  } finally {
    loading.value = false
  }
}

const handlePageChange = (page: number) => {
  currentPage.value = page
  loadGoods()
  window.scrollTo(0, 0)
}

const goToDetail = (sku_id: string) => {
  router.push(`/detail/${sku_id}`)
}

onMounted(() => {
  loadGoods()
})
</script>

<style scoped>
.category-page {
  padding: 20px 0;
}

.category-header {
  margin-bottom: 20px;
}

.goods-col {
  margin-bottom: 20px;
}

.goods-image {
  height: 200px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f5f5;
}

.goods-image img {
  max-width: 100%;
  max-height: 100%;
  object-fit: cover;
}

.goods-info {
  padding: 12px;
}

.goods-name {
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-bottom: 8px;
}

.goods-price {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.current-price {
  color: #f56c6c;
  font-size: 18px;
  font-weight: bold;
}

.original-price {
  color: #999;
  font-size: 12px;
  text-decoration: line-through;
}

.goods-shop {
  font-size: 12px;
  color: #666;
}

.pagination {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}
</style>
