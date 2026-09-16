import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User } from '@/types'
import { userApi } from '@/utils/api'

export const useUserStore = defineStore('user', () => {
  const token = ref<string | null>(localStorage.getItem('token'))
  const userInfo = ref<User | null>(null)
  const cartCount = ref<number>(Number(localStorage.getItem('cartCount') || 0))
  const isLoading = ref(false)

  const isLoggedIn = computed(() => !!token.value)
  const userName = computed(() => userInfo.value?.name || userInfo.value?.email || '')
  const userAvatar = computed(() => userInfo.value?.avatar || '')

  function setToken(newToken: string) {
    token.value = newToken
    localStorage.setItem('token', newToken)
  }

  function setUserInfo(info: User) {
    userInfo.value = info
    localStorage.setItem('user', JSON.stringify(info))
  }

  function setCartCount(count: number) {
    cartCount.value = count
    localStorage.setItem('cartCount', String(count))
  }

  function clearAuth() {
    token.value = null
    userInfo.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  // 邮箱密码登录
  async function login(username: string, password: string) {
    isLoading.value = true
    try {
      // 后端存的是明文密码（前端传来的也是明文，MD5已在后端移除）
      const res = await userApi.login({ username, password })
      setToken(res.data.token)
      if (res.data.name) localStorage.setItem('username', res.data.name)
      await fetchUserInfo()
      return true
    } catch {
      return false
    } finally {
      isLoading.value = false
    }
  }

  // 微博扫码登录（用授权码换 token）
  async function weiboLogin(authCode: string, ticket: string) {
    isLoading.value = true
    try {
      const res = await userApi.weiboCallback({ code: authCode, ticket })
      setToken(res.data.token)
      if (res.data.name) localStorage.setItem('username', res.data.name)
      await fetchUserInfo()
      return true
    } catch {
      return false
    } finally {
      isLoading.value = false
    }
  }

  async function fetchUserInfo() {
    try {
      const res = await userApi.getCurrentUser()
      setUserInfo(res.data)
    } catch {
      // ignore
    }
  }

  function logout() {
    clearAuth()
    localStorage.removeItem('username')
    localStorage.removeItem('cartCount')
    cartCount.value = 0
  }

  function checkAuth() {
    const savedToken = localStorage.getItem('token')
    if (savedToken) {
      token.value = savedToken
      const savedUser = localStorage.getItem('user')
      if (savedUser) {
        try { userInfo.value = JSON.parse(savedUser) } catch { /* ignore */ }
      }
      fetchUserInfo()
    }
  }

  return {
    token, userInfo, cartCount, isLoading,
    isLoggedIn, userName, userAvatar,
    login, weiboLogin, logout, fetchUserInfo,
    setToken, setUserInfo, setCartCount, clearAuth, checkAuth,
  }
})
