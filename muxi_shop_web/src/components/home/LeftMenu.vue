<template>
  <div class="left-menu" @mouseleave="hideSubMenu">
    <ul>
      <li v-for="item in showMainData" :key="item.index" @mouseenter="showSub(item.index)">
        <span v-for="(d, i) in item.data" :key="i">
          <a :href="`/goods_list/${d.name}/1/1`">{{ d.name }}</a>
          <span v-if="i < item.data.length - 1">/</span>
        </span>
      </li>
    </ul>
    <div class="second-item" v-show="showSubMenu">
      <SecondMenu :showSecondMenuIndex="showSecondMenuIndex" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import SecondMenu from './SecondMenu.vue'
import { goodsApi } from '@/utils/api'

const leftMenuData = ref<any[]>([])
onMounted(async () => {
  try {
    const res = await goodsApi.mainMenu()
    const raw: any[] = res.data || []
    leftMenuData.value = raw.map((item: any) => typeof item === 'string' ? JSON.parse(item) : item)
  } catch {}
})

const showMainData = computed(() => {
  const result: any[] = []
  let current: any = { index: '', data: [] }
  for (const item of leftMenuData.value) {
    if (current.index !== '' && current.index !== item.main_menu_id) {
      result.push(current)
      current = { index: '', data: [] }
    }
    current.index = item.main_menu_id
    current.data.push({ name: item.main_menu_name })
  }
  if (current.index) result.push(current)
  return result
})

const showSubMenu = ref(false)
const showSecondMenuIndex = ref('')
const showSub = (index: string) => { showSubMenu.value = true; showSecondMenuIndex.value = index }
const hideSubMenu = () => { showSubMenu.value = false }
</script>

<style lang="less" scoped>
@red: #e2231a;
.left-menu {
  position: relative;
  background: #fff;
  width: 190px;
  height: 470px;
  flex-shrink: 0;
  ul {
    padding-top: 15px;
    margin: 0;
    list-style: none;
  }
  li {
    padding-left: 15px;
    line-height: 30px;
    height: 30px;
    cursor: pointer;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    &:hover {
      background: #d9d9d9;
    }
    span {
      font-size: 14px;
      color: #333;
    }
    a {
      font-size: 14px;
      color: #333;
      text-decoration: none;
      &:hover {
        color: @red;
      }
    }
    span:last-child {
      color: #ccc;
      margin: 0 4px;
    }
  }
  .second-item {
    position: absolute;
    top: 0;
    left: 190px;
    z-index: 999;
  }
}
</style>
