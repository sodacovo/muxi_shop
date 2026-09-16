<template>
  <div class="main-header">
    <div class="content">
      <div class="logo fl">
        <Logo />
      </div>
      <div class="search-box fl">
        <SearchBox />
      </div>
      <div class="shopcart fr">
        <ShopCart />
      </div>
      <div class="right fr">
        <img src="@/assets/images/header-right.png" alt="" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import Logo from '../common/Logo.vue'
import SearchBox from './SearchBox.vue'
import ShopCart from './ShopCart.vue'
</script>

<style lang="less" scoped>
.main-header {
  background: #fff;
  border-bottom: 2px solid #e2231a;
}
.content {
  width: 1190px;
  margin: 0 auto;
  height: 140px;
  display: flex;
  align-items: center;
}
.logo {
  width: 200px;
}
.search-box {
  flex: 1;
  margin: 0 50px;
}
.shopcart {
  margin-left: auto;
  margin-right: 30px;
}
.right {
  img {
    width: 200px;
  }
}
</style>
