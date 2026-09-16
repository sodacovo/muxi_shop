<template>
  <div class="shop-cart">
    <Shortcut />
    <Header />
    <div class="goods">
      <div class="goods-num">全部商品&nbsp;&nbsp;{{ cartSumNums }}</div>
      <table class="goods-table">
        <thead>
          <tr>
            <th width="50"><input type="checkbox" :checked="allChecked" @change="checkedAll" />全选</th>
            <th>商品</th><th></th><th>单价</th><th>数量</th><th>小计</th><th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in cartListData" :key="item.sku_id">
            <td><input type="checkbox" :checked="!!item.checked" @change="changeChecked(item.sku_id)" /></td>
            <td><img :src="item.goods?.image || ''" alt="" style="width:80px;height:80px;border:1px solid #eee;" /></td>
            <td style="width:300px;padding:0 10px;">{{ item.goods?.name || '商品信息缺失' }}</td>
            <td style="width:100px;text-align:center;">￥{{ (Number(item.goods?.jd_price) || 0).toFixed(2) }}</td>
            <td style="width:120px;text-align:center;">
              <el-input-number :model-value="item.nums" :min="1" :max="10" size="small" @change="(v: number) => handleChange(v, item)" />
            </td>
            <td style="width:120px;text-align:center;font-weight:700;">￥{{ ((Number(item.goods?.jd_price) || 0) * item.nums).toFixed(2) }}</td>
            <td style="width:80px;text-align:center;"><el-button type="text" size="small" @click="removeItem(item)">删除</el-button></td>
          </tr>
        </tbody>
      </table>
      <div class="bottom-tool">
        <div class="tool-left">
          <input type="checkbox" :checked="allChecked" @change="checkedAll" />全选
          <span class="delete-btn" @click="deleteGoods(0)">删除选中</span>
          <span class="clear-btn" @click="deleteGoods(1)">清理购物车</span>
        </div>
        <div class="tool-right">
          <span>已选 <em>{{ selectedCount }}</em> 件</span>
          <span class="total">总价: <em>￥{{ totalPrice.toFixed(2) }}</em></span>
          <a class="go-order" href="#" @click.prevent="goOrder">去结算</a>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import Shortcut from '@/components/common/Shortcut.vue'
import Header from '@/components/home/Header.vue'
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { cartApi, orderApi } from '@/utils/api'

const router = useRouter()
const cartListData = ref<any[]>([])
const allChecked = ref(false)
const selectedCount = computed(() => cartListData.value.filter(i => i.checked).length)
const totalPrice = computed(() => cartListData.value.filter(i => i.checked).reduce((t, i) => t + (Number(i.goods?.jd_price) || 0) * i.nums, 0))
const cartSumNums = computed(() => cartListData.value.reduce((t, i) => t + (Number(i.nums) || 0), 0))

onMounted(async () => {
  try {
    const res = await cartApi.detail()
    cartListData.value = (res.data || []).map((i: any) => ({ ...i, checked: false }))
  } catch { /* interceptor */ }
})

const handleChange = async (newVal: number, item: any) => {
  item.nums = newVal
  try { await cartApi.updateNum({ sku_id: item.sku_id, nums: newVal }) } catch { /* interceptor */ }
}

const checkedAll = () => {
  allChecked.value = !allChecked.value
  cartListData.value.forEach(i => { i.checked = allChecked.value })
}

const changeChecked = (skuId: string) => {
  const item = cartListData.value.find(i => i.sku_id === skuId)
  if (item) item.checked = !item.checked
  allChecked.value = cartListData.value.every(i => i.checked)
}

const removeItem = async (item: any) => {
  if (!confirm('删除此商品？')) return
  try {
    await cartApi.delete([item.sku_id])
    cartListData.value = cartListData.value.filter(i => i.sku_id !== item.sku_id)
  } catch { /* interceptor */ }
}

const deleteGoods = async (type: number) => {
  if (type === 0) {
    const checked = cartListData.value.filter(i => i.checked)
    if (!checked.length) { alert('请先选择商品'); return }
    if (!confirm('删除选中商品？')) return
    try {
      await cartApi.delete(checked.map(i => i.sku_id))
      cartListData.value = cartListData.value.filter(i => !i.checked)
    } catch { /* interceptor */ }
  } else {
    if (!confirm('清空购物车？')) return
    try {
      await cartApi.delete(cartListData.value.map(i => i.sku_id))
      cartListData.value = []
      location.href = '/'
    } catch { /* interceptor */ }
  }
}

const goOrder = async () => {
  const checked = cartListData.value.filter(i => i.checked)
  if (!checked.length) { alert('请选择商品'); return }
  try {
    const res = await orderApi.create({
      trade: { address_id: 0, order_amount: totalPrice.value },
      goods: checked.map(i => ({ sku_id: i.sku_id, nums: i.nums })),
    })
    router.push(`/order/${res.data.trade_no}`)
  } catch { /* interceptor */ }
}
</script>

<style lang="less" scoped>
.shop-cart { background: #f4f4f4; min-height: 100vh; }
.goods { width: 1190px; margin: 0 auto; background: #fff; padding: 20px; }
.goods-num { color: #e2231a; font-size: 16px; font-weight: 700; margin-bottom: 15px; }
.goods-table { width: 100%; border-collapse: collapse;
  th { background: #f3f3f3; height: 45px; padding: 0 10px; text-align: left; }
  td { padding: 10px; border-bottom: 1px solid #f0f0f0; }
}
.bottom-tool { margin-top: 10px; padding: 15px 20px; border: 1px solid #f0f0f0; display: flex; justify-content: space-between; align-items: center; }
.tool-left { display: flex; align-items: center; gap: 15px; font-size: 14px;
  .delete-btn, .clear-btn { cursor: pointer; color: #666; &:hover { color: #e2231a; } }
  .clear-btn { font-weight: 700; }
}
.tool-right { display: flex; align-items: center; gap: 15px; font-size: 14px; color: #999;
  .total { font-weight: 700; em { color: #e2231a; font-size: 16px; } }
}
.go-order { display: inline-block; width: 95px; height: 50px; line-height: 50px; text-align: center; background: #e2231a; color: #fff; font-size: 16px; font-weight: 700; margin-left: 20px; }
</style>
