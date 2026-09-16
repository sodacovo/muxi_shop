<template>
  <div class="detail-page">
    <Shortcut />
    <Header />
    <div class="goods">
      <div class="goods-info">
        <div class="goods-image">
          <img :src="fixUrl(goodsData.image)" alt="商品图片" @error="e => (e.target as HTMLImageElement).src = '/default.png'" />
        </div>
        <div class="goods-content">
          <h1 class="goods-name">{{ goodsData.name || '加载中...' }}</h1>
          <div class="goods-price">
            <template v-if="goodsData.is_seckill && goodsData.is_seckill_valid">
              <span class="seckill-label">秒杀价</span>
              <span class="price-value">¥{{ goodsData.seckill_price || 0 }}</span>
              <span class="original-price"><del>原价 ¥{{ goodsData.jd_price }}</del></span>
            </template>
            <template v-else>
              <span class="price-label">价格</span>
              <span class="price-value">¥{{ goodsData.jd_price || 0 }}</span>
            </template>
          </div>
          <div class="goods-meta">
            <span v-if="goodsData.shop_name">店铺：{{ goodsData.shop_name }}</span>
          </div>
          <div class="goods-actions">
            <div class="count-wrapper">
              <span class="label">数量</span>
              <el-input-number v-model="num" :min="1" :max="10" size="default" />
            </div>
            <button class="add-cart-btn" @click="addCartData(goodsData.id, num, 0)" :disabled="!goodsData.id">
              {{ goodsData.id ? '加入购物车' : '加载中...' }}
            </button>
            <button class="buy-now-btn" @click="buyNow" :disabled="!goodsData.id">
              立即购买
            </button>
          </div>
        </div>
      </div>

      <div class="recommend" v-if="recommendList.length">
        <h2 class="recommend-title">为你推荐</h2>
        <div class="recommend-list">
          <div v-for="item in recommendList" :key="item.id" class="rec-item" @click="$router.push(`/detail/${item.id}`)">
            <div class="rec-image">
              <img :src="fixUrl(item.image)" alt="" @error="e => (e.target as HTMLImageElement).src = '/default.png'" />
            </div>
            <div class="rec-info">
              <p class="rec-name">{{ item.name }}</p>
              <p class="rec-price">¥{{ item.price || item.jd_price || 0 }}</p>
            </div>
          </div>
        </div>
      </div>
      <div class="recommend-empty" v-else>
        <p>暂无推荐商品</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import Shortcut from '@/components/common/Shortcut.vue'
import Header from '@/components/home/Header.vue'
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { goodsApi, cartApi } from '@/utils/api'

const route = useRoute()
const router = useRouter()
const skuId = ref('')
const num = ref(1)
const goodsData = reactive<any>({})
const recommendList = ref<any[]>([])

const IMAGE_BASE = 'https://www.nwq1309.shop/static/product_images/'

const fixUrl = (url?: string) => {
  if (!url) return '/default.png'
  let fixed = url.replace('8.138.126.24', 'www.nwq1309.shop').replace('http://', 'https://')
  if (!fixed.startsWith('https://')) fixed = IMAGE_BASE + fixed
  return fixed
}

const addCartData = async (id: string | number, nums: number, _isDelete = 0) => {
  try {
    await cartApi.add({ sku_id: String(id), nums })
    ElMessage.success('已加入购物车')
  } catch { /* interceptor */ }
}

const buyNow = () => {
  ElMessage.info('购买功能开发中')
}

onMounted(async () => {
  skuId.value = route.params.sku_id as string
  try {
    const res = await goodsApi.detail(skuId.value)
    Object.assign(goodsData, res.data || {})
    if (goodsData.id) goodsApi.recordBehavior(goodsData.id as number).catch(() => {})
  } catch { /* interceptor */ }
  try {
    const res = await goodsApi.recommend()
    recommendList.value = res.data || []
  } catch { recommendList.value = [] }
})
</script>

<style lang="less" scoped>
.detail-page {
  background: #f4f4f4;
  min-height: 100vh;
}

.goods {
  width: 1190px;
  margin: 0 auto;
  padding: 20px 0;
}

.goods-info {
  display: flex;
  gap: 30px;
  background: #fff;
  padding: 20px;
  border-radius: 8px;
}

.goods-image {
  flex-shrink: 0;
  width: 350px;
  height: 350px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fafafa;
  border-radius: 8px;
  overflow: hidden;

  img {
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
  }
}

.goods-content {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.goods-name {
  font-size: 20px;
  font-weight: 600;
  color: #333;
  margin-bottom: 20px;
  line-height: 1.4;
}

.goods-price {
  background: #f7f7f7;
  padding: 15px;
  margin-bottom: 20px;
  border-radius: 4px;

  .seckill-label,
  .price-label {
    color: #999;
    font-size: 14px;
    margin-right: 10px;
  }

  .seckill-label {
    background: #e2231a;
    color: #fff;
    padding: 2px 8px;
    border-radius: 2px;
  }

  .price-value {
    font-size: 28px;
    font-weight: 700;
    color: #e2231a;
    margin-right: 15px;
  }

  .original-price {
    color: #999;
    font-size: 14px;
  }
}

.goods-meta {
  margin-bottom: 20px;
  color: #666;
  font-size: 14px;
}

.goods-actions {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-top: auto;
}

.count-wrapper {
  display: flex;
  align-items: center;
  gap: 10px;

  .label {
    color: #666;
    font-size: 14px;
  }
}

.add-cart-btn {
  padding: 12px 40px;
  background: #fff;
  border: 2px solid #e2231a;
  color: #e2231a;
  font-size: 16px;
  font-weight: 600;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s;

  &:hover:not(:disabled) {
    background: #fff5f5;
  }

  &:disabled {
    border-color: #ccc;
    color: #ccc;
    cursor: not-allowed;
  }
}

.buy-now-btn {
  padding: 12px 40px;
  background: #e2231a;
  border: 2px solid #e2231a;
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s;

  &:hover:not(:disabled) {
    background: #c81e1a;
    border-color: #c81e1a;
  }

  &:disabled {
    background: #ccc;
    border-color: #ccc;
    cursor: not-allowed;
  }
}

.recommend {
  margin-top: 20px;
  background: #fff;
  padding: 20px;
  border-radius: 8px;
}

.recommend-title {
  font-size: 18px;
  color: #333;
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 2px solid #e2231a;
}

.recommend-list {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 15px;
}

.rec-item {
  cursor: pointer;
  background: #fafafa;
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.3s;

  &:hover {
    transform: translateY(-4px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }
}

.rec-image {
  width: 100%;
  height: 160px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  padding: 10px;

  img {
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
  }
}

.rec-info {
  padding: 10px;
}

.rec-name {
  font-size: 13px;
  color: #666;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-bottom: 8px;
}

.rec-price {
  font-size: 16px;
  font-weight: 600;
  color: #e2231a;
}

.recommend-empty {
  margin-top: 20px;
  background: #fff;
  padding: 40px;
  border-radius: 8px;
  text-align: center;
  color: #999;
}
</style>
