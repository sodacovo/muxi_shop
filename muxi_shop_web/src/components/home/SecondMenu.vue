<template>
  <div class="second">
    <div class="menu-content" v-for="item in showSubMenuData" :key="item.index">
      <div class="menu-title">
        <span v-for="d in item.data" :key="d.name">
          <a href="" v-if="d.type === 'channel'">{{ d.name }}<img src="@/assets/images/menu/arrows-white.png" alt="" /></a>
        </span>
      </div>
      <div class="menu-detail">
        <div class="menu-detail-item">
          <span v-for="d in item.data" :key="d.name">
            <span class="menu-detail-tit" v-if="d.type === 'dt'">
              <a :href="`/goods_list/${d.name}/1/1`">{{ d.name }}<img src="@/assets/images/menu/arrows-black.png" alt="" /></a>
            </span>
            <span class="menu-detail-data" v-else-if="d.type === 'dd'">
              <a :href="`/goods_list/${d.name}/1/1`">{{ d.name }}</a>
            </span>
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { goodsApi } from '@/utils/api'

const props = defineProps<{ showSecondMenuIndex: string }>()
const subMenuData = ref<any[]>([])

const loadSubMenu = async (id: string) => {
  try {
    const res = await goodsApi.subMenu(Number(id))
    const raw: any[] = res.data || []
    subMenuData.value = raw.map((item: any) => typeof item === 'string' ? JSON.parse(item) : item)
  } catch {}
}

watch(() => props.showSecondMenuIndex, (v) => { if (v) loadSubMenu(v) }, { immediate: true })

const showSubMenuData = ref<any[]>([])
watch(subMenuData, (data) => {
  const result: any[] = []
  let current: any = { index: '', data: [] }
  for (const item of data) {
    if (current.index !== '' && current.index !== item.sub_menu_id) {
      result.push(current)
      current = { index: '', data: [] }
    }
    current.index = item.sub_menu_id
    current.data.push({ name: item.sub_menu_name, type: item.sub_menu_type })
  }
  if (current.index) result.push(current)
  showSubMenuData.value = result
}, { deep: true })
</script>

<style lang="less" scoped>
@red: #e2231a;
.second { width: 1000px; background: #fff; border: 2px solid #e9e9e9; padding: 20px; }
.menu-content { margin-bottom: 10px; }
.menu-title a { display: inline-block; background: #333; color: #fff; margin-right: 10px; height: 25px; line-height: 25px; padding: 0 10px; font-size: 14px; text-decoration: none; }
.menu-title a:hover { background: @red; }
.menu-title img { height: 18px; vertical-align: middle; }
.menu-detail { margin-top: 10px; }
.menu-detail-tit a { color: #333; font-weight: 700; font-size: 14px; }
.menu-detail-tit a:hover { color: @red; }
.menu-detail-data a { color: #666; font-size: 14px; margin: 0 5px; }
.menu-detail-data a:hover { color: @red; }
</style>
