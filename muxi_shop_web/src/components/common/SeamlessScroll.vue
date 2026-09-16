<template>
  <div class="seamless-scroll" ref="containerRef" @mouseenter="stopScroll" @mouseleave="startScroll">
    <div class="scroll-content" :style="{ transform: `translateX(-${offset}px)` }">
      <slot></slot>
      <slot></slot>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const props = withDefaults(defineProps<{
  list: any[]
  step?: number
  hover?: boolean
  direction?: 'left' | 'right'
}>(), {
  step: 0.5,
  hover: true,
  direction: 'left'
})

const containerRef = ref<HTMLElement>()
const offset = ref(0)
let animationFrame: number | null = null
let isPaused = false

const getItemWidth = () => {
  if (!containerRef.value) return 200
  const firstItem = containerRef.value.querySelector('.item')
  return firstItem ? firstItem.offsetWidth + 15 : 200 // item width + gap
}

const animate = () => {
  if (isPaused) {
    animationFrame = requestAnimationFrame(animate)
    return
  }

  const itemWidth = getItemWidth()
  const listWidth = itemWidth * props.list.length

  if (props.direction === 'left') {
    offset.value += props.step
    if (offset.value >= listWidth) {
      offset.value = 0
    }
  } else {
    offset.value -= props.step
    if (offset.value <= 0) {
      offset.value = listWidth
    }
  }

  animationFrame = requestAnimationFrame(animate)
}

const stopScroll = () => {
  if (props.hover) {
    isPaused = true
  }
}

const startScroll = () => {
  isPaused = false
}

onMounted(() => {
  animationFrame = requestAnimationFrame(animate)
})

onUnmounted(() => {
  if (animationFrame) {
    cancelAnimationFrame(animationFrame)
  }
})
</script>

<style lang="less" scoped>
.seamless-scroll {
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.scroll-content {
  display: flex;
  gap: 15px;
  transition: transform 0ms linear;
  white-space: nowrap;
}
</style>
