<template>
  <div class="search-main">
    <div class="content">
      <input type="text" placeholder="亲,要购买什么呢~" v-model="searchWord" @keyup.enter="doSearch(searchWord)" />
      <span class="iconfont icon-fangdajing" @click="doSearch(searchWord)"></span>
    </div>
    <div class="hotword">
      <a v-for="item in hotWords" :key="item.word" :class="{ active: item.active }" href="#" @click.prevent="doSearch(item.word)">{{ item.word }}</a>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const searchWord = ref('')
const hotWords = ref([
  { word: '电脑', active: true },
  { word: '手机', active: false },
  { word: '手表', active: false },
  { word: '相机', active: false },
  { word: '休闲', active: false },
])

const doSearch = (keyword: string) => {
  if (!keyword?.trim()) return
  router.push(`/goods_list/${encodeURIComponent(keyword)}/1/1`)
  hotWords.value.forEach(d => { d.active = d.word === keyword })
}
</script>

<style lang="less" scoped>
@red: #e2231a;
.search-main {
  width: 100%;
  .content {
    width: 100%;
    max-width: 550px;
    height: 35px;
    border: 2px solid @red;
    display: flex;
    align-items: center;
    input {
      flex: 1;
      height: 35px;
      padding: 0 15px;
      border: none;
      outline: none;
      font-size: 14px;
    }
    span {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 50px;
      height: 35px;
      background: @red;
      color: #fff;
      cursor: pointer;
      font-size: 18px;
      &:hover {
        background: #c81623;
      }
    }
  }
  .hotword {
    margin-top: 10px;
    a {
      color: #999;
      margin-right: 10px;
      text-decoration: none;
      font-size: 14px;
      &:hover {
        color: @red;
      }
      &.active {
        color: @red;
        font-weight: 600;
      }
    }
  }
}
</style>
