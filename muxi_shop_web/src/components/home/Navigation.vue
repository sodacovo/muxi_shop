<template>
  <div class="nav-wrapper">
    <div class="main">
      <div class="menu">
        <LeftMenu />
      </div>
      <div class="banner">
        <Banner />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import LeftMenu from './LeftMenu.vue'
import Banner from './Banner.vue'
</script>

<style lang="less" scoped>
.nav-wrapper {
  background: #fff;
  padding: 15px 0;
}
.main {
  width: 1190px;
  margin: 0 auto;
  display: flex;
  gap: 10px;
}
.menu {
  flex-shrink: 0;
}
.banner {
  flex: 1;
}
</style>
