<template>
  <div>
    <Shortcut />
    <Header />
    <div class="inner">
      <Navigation />
      <div class="find-goods">
        <FindGoods />
      </div>
      <div class="category clearfix">
        <div class="content fl" v-for="(item, index) in category" :key="index" @click="toCategory(item.typeId)">
          <div>
            <div class="category-title" :class="{ selected_title: item.selected }">{{ item.title }}</div>
            <div class="category-content" :class="{ selected_content: item.selected }">{{ item.content }}</div>
          </div>
        </div>
      </div>
      <Category :categoryId="categoryId" />
    </div>
    <el-backtop :right="40" :bottom="60" :visibility-height="300" class="custom-backtop">
      <div class="backtop-btn">
        <el-icon class="backtop-icon"><ArrowUp /></el-icon>
        <span class="backtop-text">回到顶部</span>
      </div>
    </el-backtop>
  </div>
</template>

<script setup lang="ts">
import Shortcut from '@/components/common/Shortcut.vue'
import Header from '@/components/home/Header.vue'
import Navigation from '@/components/home/Navigation.vue'
import FindGoods from '@/components/home/FindGoods.vue'
import Category from '@/components/home/Category.vue'
import { ArrowUp } from '@element-plus/icons-vue'
import { ref } from 'vue'

const category = ref([
  { typeId: 1, title: '精选', content: '猜你喜欢', selected: true },
  { typeId: 2, title: '智能先锋', content: '大电器城', selected: false },
  { typeId: 3, title: '居家优品', content: '品质生活', selected: false },
  { typeId: 4, title: '超市百货', content: '百货生鲜', selected: false },
  { typeId: 5, title: '时尚达人', content: '美妆穿搭', selected: false },
  { typeId: 6, title: '进口好物', content: '京东国际', selected: false },
])
const categoryId = ref(1)
const toCategory = (typeId: number) => {
  categoryId.value = typeId
  category.value.forEach((c, i) => {
    c.selected = (i + 1) === typeId
  })
}
</script>

<style lang="less" scoped>
.inner {
  background-color: #f4f4f4;
  min-height: 100vh;
}
.find-goods {
  width: 1190px;
  margin: 0 auto;
  padding: 15px 0;
}
.category {
  width: 1190px;
  margin: 0 auto 10px;
  background-color: #fff;
  height: 70px;
  display: flex;
  align-items: center;
  .content {
    flex: 1;
    cursor: pointer;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    border-right: 1px solid #e8e8e8;
    &:last-child {
      border-right: none;
    }
    &:hover {
      color: #e1251b;
      .category-content {
        color: #e1251b;
      }
    }
    .category-title {
      font-size: 16px;
      font-weight: 700;
      height: 30px;
      line-height: 30px;
      border-radius: 15px;
      padding: 0 15px;
      transition: all 0.3s;
      text-align: center;
    }
    .category-content {
      font-size: 14px;
      color: #999;
      margin-top: 4px;
      text-align: center;
      transition: color 0.3s;
    }
    .selected_title {
      background-color: #e1251b;
      color: #fff;
    }
    .selected_content {
      color: #e1251b;
    }
  }
}
.custom-backtop {
  .backtop-btn {
    width: 56px;
    height: 56px;
    border-radius: 50%;
    background: linear-gradient(135deg, #e1251b 0%, #c8102e 100%);
    box-shadow: 0 4px 16px rgba(225, 37, 27, 0.3);
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.3s ease;
    &:hover {
      transform: scale(1.08);
      box-shadow: 0 6px 20px rgba(225, 37, 27, 0.4);
    }
    .backtop-icon {
      color: #fff;
      font-size: 24px;
    }
    .backtop-text {
      position: absolute;
      right: 65px;
      top: 50%;
      transform: translateY(-50%);
      padding: 6px 12px;
      background: #fff;
      color: #e1251b;
      font-size: 14px;
      border-radius: 20px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
      opacity: 0;
      visibility: hidden;
      transition: all 0.3s ease;
    }
    &:hover .backtop-text {
      opacity: 1;
      visibility: visible;
      right: 60px;
    }
  }
}
</style>
