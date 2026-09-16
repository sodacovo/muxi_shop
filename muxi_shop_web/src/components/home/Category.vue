<template>
  <div class="category-wrapper">
    <div class="category">
      <div class="goods" v-for="item in goods" :key="item.sku_id" @click="goDetail(item.sku_id)">
        <div class="img-row">
          <img :src="fixImageUrl(item.image)" alt="" @error="e => (e.target as HTMLImageElement).src = '/default.png'" />
        </div>
        <div class="name-row">{{ item.name }}</div>
        <div class="price-row">
          <small>￥</small><span>{{ item.jd_price }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { goodsApi } from '@/utils/api'

const props = defineProps<{ categoryId: number }>()
const router = useRouter()
const goods = ref<any[]>([])
const page = ref(1)

const IMAGE_BASE = 'https://www.nwq1309.shop/static/product_images/'

const fixImageUrl = (url?: string) => {
  if (!url) return '/default.png'
  let fixed = url.replace('8.138.126.24', 'www.nwq1309.shop').replace('http://', 'https://')
  if (!fixed.startsWith('https://')) fixed = IMAGE_BASE + fixed
  return fixed
}

const loadGoods = async (id: number, pg: number) => {
  try {
    const res = await goodsApi.category({ category_id: id, page: pg })
    const data: any[] = res.data || []
    if (pg === 1) {
      goods.value = data.map((item: any) => typeof item === 'string' ? JSON.parse(item) : item)
    } else {
      const parsed = data.map((item: any) => typeof item === 'string' ? JSON.parse(item) : item)
      goods.value.push(...parsed)
    }
  } catch {}
}

watch(() => props.categoryId, (id) => { goods.value = []; page.value = 1; loadGoods(id, 1) }, { immediate: true })

onMounted(() => {
  window.addEventListener('scroll', onScroll)
})

onUnmounted(() => {
  window.removeEventListener('scroll', onScroll)
})

const onScroll = () => {
  const { clientHeight, scrollTop, scrollHeight } = document.documentElement
  if (clientHeight + scrollTop >= scrollHeight - 100) {
    page.value++
    loadGoods(props.categoryId, page.value)
  }
}

const goDetail = (skuId: string) => { router.push(`/detail/${skuId}`) }
</script>

<style lang="less" scoped>
.category-wrapper {
  margin-top: 10px;
}
.category {
  width: 1190px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 10px;
}
.goods {
  background: #fff;
  padding: 10px;
  cursor: pointer;
  border-radius: 8px;
  transition: all 0.3s;
  display: flex;
  flex-direction: column;
  align-items: center;

  &:hover {
    transform: translateY(-4px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    .name-row {
      color: #e2231a;
    }
    .img-row img {
      transform: scale(1.05);
    }
  }
}
.img-row {
  width: 100%;
  height: 180px;
  display: flex;
  align-items: center;
  justify-content: center;

  img {
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
    transition: transform 0.3s;
  }
}
.name-row {
  width: 100%;
  font-size: 13px;
  color: #666;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  margin: 10px 0;
  min-height: 36px;
  line-height: 18px;
}
.price-row {
  color: #e2231a;
  font-size: 18px;
  font-weight: 700;
  align-self: flex-start;
}
</style>
