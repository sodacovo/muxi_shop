<template>
  <div>
    <Shortcut />
    <Header />
    <div class="all-goods">
      <div>
        <span>全部商品分类</span>
      </div>
    </div>
    <div class="all-goods-list">
      <div class="result-keyword">
        <span class="all-result-font">全部结果&nbsp;&nbsp;>&nbsp;&nbsp;</span>
        <span class="search-word">"{{ keyword }}"</span>
      </div>
      <div class="goods-list">
        <div class="search-condition">
          <a href="#" v-for="(item, index) in orderTypes" :key="index" @click.prevent="changeOrder(item.order, item.index)" :class="item.isActive ? 'current-condition' : 'not-current-condition'">
            <span>{{ item.name }}</span>
          </a>
        </div>
        <div class="list-detail clearfix">
          <div class="every-goods fl" v-for="(item, index) in goodsListData" :key="index">
            <div><img :src="fixImageUrl(item.image)" class="goods_image" alt="" /></div>
            <div class="price">￥{{ item.p_price }}</div>
            <div class="name cs2">{{ item.name }}</div>
            <div class="comment-count"><span class="count">{{ item.comment_count || 0 }}</span><span class="comment">条评价</span></div>
            <div class="shop-name">{{ item.shop_name }}</div>
            <div class="add-cart cs" @click="addCartData(item.sku_id, 1, 0)">
              <img src="@/assets/images/cart/add-cart1.png" alt="" />加入购物车
            </div>
          </div>
        </div>
      </div>
      <div class="change_page">
        <el-pagination layout="prev, pager, next" :total="goodsCount" :page-size="15" @current-change="handleCurrentChange" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import Shortcut from '@/components/common/Shortcut.vue'
import Header from '@/components/home/Header.vue'
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { goodsApi, cartApi } from '@/utils/api'

const router = useRouter()
const route = useRoute()

const orderTypes = ref([
  { index: 1, order: 1, name: '综合', isActive: true },
  { index: 2, order: 1, name: '评论数', isActive: false },
  { index: 3, order: 2, name: '价格', isActive: false },
])
const goodsListData = ref<any[]>([])
const goodsCount = ref(0)

const IMAGE_BASE = 'https://www.nwq1309.shop/static/product_images/'

const fixImageUrl = (url?: string) => {
  if (!url) return '/default.png'
  let fixed = url.replace('8.138.126.24', 'www.nwq1309.shop').replace('http://', 'https://')
  if (!fixed.startsWith('https://')) fixed = IMAGE_BASE + fixed
  return fixed
}

const getSearchData = async (keyword: string, pg: number, order: number) => {
  try {
    const res = await goodsApi.search({ keyword, page: pg, order_by: order })
    goodsListData.value = []
    for (const item of res.data || []) {
      goodsListData.value.push(typeof item === 'string' ? JSON.parse(item) : item)
    }
  } catch { /* handled by interceptor */ }
}

const getKeywordGoodsCount = async (keyword: string) => {
  try {
    const res = await goodsApi.searchCount(keyword)
    goodsCount.value = res as unknown as number
  } catch { goodsCount.value = 0 }
}

const keyword = computed(() => route.params.keyword as string || '')
const page = computed(() => Number(route.params.page) || 1)
const order = computed(() => Number(route.params.order) || 1)

onMounted(() => {
  getSearchData(keyword.value, page.value, order.value)
  getKeywordGoodsCount(keyword.value)
})

watch(keyword, (v) => { getSearchData(v, 1, 1); getKeywordGoodsCount(v) })
watch(page, (v) => { getSearchData(keyword.value, v, 1) })
watch(order, (v) => { getSearchData(keyword.value, 1, v) })

const changeOrder = (currentOrder: number, idx: number) => {
  router.push(`/goods_list/${keyword.value}/1/${currentOrder}`)
  orderTypes.value.forEach((o, i) => { o.isActive = (i + 1) === idx })
}

const handleCurrentChange = (val: number) => {
  router.push(`/goods_list/${keyword.value}/${val}/${order.value}`)
}

const addCartData = async (_skuId: string, _nums: number, _isDelete = 0) => {}
</script>

<style lang="less" scoped>
.all-goods {
  border-bottom: 2px solid #f30213;
  div { width: 1190px; margin: 0 auto; span { display: block; background-color: #f30213; color: white; font-size: 14px; height: 33px; line-height: 33px; text-align: center; width: 190px; } }
}
.all-goods-list {
  width: 1190px; margin: 0 auto;
  .result-keyword { margin-top: 20px; .all-result-font { color: #666; font-size: 12px; } .search-word { color: #666; font-weight: 700; font-size: 12px; } }
  .search-condition { margin-top: 10px; background-color: #f1f1f1; height: 40px; line-height: 40px;
    .current-condition { background-color: #e4393c; border: 1px solid #e4393c; color: #fff; display: inline-block; text-align: center; height: 25px; line-height: 25px; width: 80px; font-size: 14px; margin-left: 10px; }
    .not-current-condition { background-color: #fff; border: 1px solid #ddd; color: #333; display: inline-block; text-align: center; height: 25px; line-height: 25px; width: 80px; font-size: 14px; margin-left: 10px; &:hover { border-color: #e4393c; } }
  }
  .list-detail {
    .every-goods { margin-top: 10px; border: 1px solid #fff; width: 238px; height: 400px; &:hover { border-color: #e3e4e5; } cursor: pointer;
      .goods_image { margin-top: 10px; width: 220px; height: 220px; }
      .price { margin-left: 5px; margin-top: 10px; color: #e4393c; font-size: 20px; }
      .name { margin-top: 10px; font-size: 12px; color: #666; margin-left: 5px; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
      .comment-count { margin-top: 10px; margin-left: 5px; .count { color: #646fb0; font-weight: 700; } .comment { color: #a7a7a7; } }
      .shop-name { margin-top: 10px; margin-left: 5px; color: #999; }
      .add-cart { margin-top: 10px; border: 1px solid #e4393c; text-align: center; padding: 5px; img { width: 20px; vertical-align: middle; } &:hover { color: #e4393c; } }
    }
  }
  .change_page { margin-top: 20px; margin-left: 75%; margin-bottom: 20px; }
}
</style>
