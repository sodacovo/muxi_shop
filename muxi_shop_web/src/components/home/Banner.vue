<template>
  <div class="banner-wrapper">
    <el-carousel trigger="click" height="470px">
      <el-carousel-item v-for="(img, idx) in images" :key="idx">
        <div class="img-container">
          <img :src="img" alt="轮播图" />
        </div>
      </el-carousel-item>
    </el-carousel>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import banner1 from '@/assets/images/banner/lg2.png'
import banner2 from '@/assets/images/banner/lg4.png'
import banner3 from '@/assets/images/banner/lg7.png'
import banner4 from '@/assets/images/banner/lg0.png'
import banner5 from '@/assets/images/banner/lg8.png'
import banner6 from '@/assets/images/banner/lg9.png'

const images = ref([banner1, banner2, banner3, banner4, banner5, banner6])
</script>

<style scoped lang="less">
.banner-wrapper {
  width: 100%;
  max-width: 1000px;
  :deep(.el-carousel) {
    border-radius: 12px;
    overflow: hidden;
  }
  :deep(.el-carousel__item) {
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .img-container {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    img {
      width: 100%;
      height: 470px;
      object-fit: cover;
    }
  }
}
</style>
