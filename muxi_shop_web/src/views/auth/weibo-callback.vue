<template>
  <div style="text-align:center;padding:100px;">
    <p v-if="!error">微博登录处理中...</p>
    <p v-else style="color:red;">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const error = ref('')

onMounted(async () => {
  const code = route.query.code as string
  const ticket = route.query.ticket as string
  if (!code || !ticket) { error.value = '参数缺失'; return }
  const ok = await userStore.weiboLogin(code, ticket)
  if (ok) {
    router.push('/')
  } else {
    error.value = '登录失败，请重试'
    setTimeout(() => router.push('/login'), 2000)
  }
})
</script>
