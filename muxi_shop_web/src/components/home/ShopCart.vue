<template>
  <router-link to="/cart/detail" class="shopcart-link">
    <div class="shopcart">
      <span class="iconfont icon-gouwuche"></span>
      <span class="text">购物车</span>
      <span class="count" v-if="cartCount > 0">{{ cartCount }}</span>
    </div>
  </router-link>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const cartCount = computed(() => userStore.cartCount)
</script>

<style lang="less" scoped>
.shopcart-link { text-decoration: none; }
.shopcart {
  position: relative; display: flex; align-items: center; gap: 5px;
  padding: 8px 15px; border: 1px solid #ddd; border-radius: 4px; cursor: pointer; transition: background 0.2s;
  &:hover { background: #f5f5f5; }
  .icon-gouwuche { font-size: 20px; }
  .text { font-size: 14px; }
  .count {
    position: absolute; top: -8px; right: -8px; background: #e93854; color: #fff; border-radius: 50%;
    min-width: 18px; height: 18px; font-size: 11px; display: flex; align-items: center; justify-content: center;
    padding: 0 4px; font-weight: 700;
  }
}
</style>
