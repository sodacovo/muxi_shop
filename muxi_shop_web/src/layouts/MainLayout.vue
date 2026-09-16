<template>
  <div class="main-layout">
    <!-- 顶部导航 -->
    <header class="header">
      <div class="header-content">
        <div class="logo" @click="$router.push('/')">
          <el-icon><Shop /></el-icon>
          <span>木犀商城</span>
        </div>

        <div class="search-box">
          <el-input
            v-model="searchKeyword"
            placeholder="搜索商品"
            @keyup.enter="handleSearch"
          >
            <template #append>
              <el-button :icon="Search" @click="handleSearch" />
            </template>
          </el-input>
        </div>

        <div class="nav-links">
          <el-menu mode="horizontal" :ellipsis="false">
            <el-menu-item index="/" @click="$router.push('/')">首页</el-menu-item>
            <el-menu-item index="/seckill" @click="$router.push('/seckill')">秒杀</el-menu-item>
            <el-menu-item index="/cart" @click="goToCart">购物车</el-menu-item>
            <el-sub-menu index="user">
              <template #title>
                <el-avatar v-if="userStore.isLoggedIn" :src="userStore.userAvatar" />
                <span v-else>用户</span>
              </template>
              <template v-if="userStore.isLoggedIn">
                <el-menu-item index="/user" @click="$router.push('/user')">个人中心</el-menu-item>
                <el-menu-item index="/order" @click="$router.push('/order')">我的订单</el-menu-item>
                <el-menu-item index="/address" @click="$router.push('/address')">收货地址</el-menu-item>
                <el-menu-item index="logout" @click="handleLogout">退出登录</el-menu-item>
              </template>
              <template v-else>
                <el-menu-item index="/login" @click="$router.push('/login')">登录</el-menu-item>
                <el-menu-item index="/register" @click="$router.push('/register')">注册</el-menu-item>
              </template>
            </el-sub-menu>
          </el-menu>
        </div>
      </div>
    </header>

    <!-- 主内容区 -->
    <main class="main-content">
      <router-view />
    </main>

    <!-- 底部 -->
    <footer class="footer">
      <p>© 2024 木犀商城 - 为您提供优质的商品</p>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Search, Shop } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import { ElMessageBox } from 'element-plus'

const router = useRouter()
const userStore = useUserStore()
const searchKeyword = ref('')

const handleSearch = () => {
  if (searchKeyword.value.trim()) {
    router.push({
      name: 'Search',
      query: { keyword: searchKeyword.value.trim() },
    })
  }
}

const goToCart = () => {
  if (userStore.isLoggedIn) {
    router.push('/cart')
  } else {
    router.push('/login')
  }
}

const handleLogout = () => {
  ElMessageBox.confirm('确定要退出登录吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  })
    .then(() => {
      userStore.logout()
      router.push('/')
    })
    .catch(() => {})
}
</script>

<style scoped>
.main-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.header {
  background: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
  display: flex;
  align-items: center;
  gap: 40px;
  height: 60px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 20px;
  font-weight: bold;
  color: var(--el-color-primary);
  cursor: pointer;
}

.search-box {
  flex: 1;
  max-width: 400px;
}

.main-content {
  flex: 1;
  max-width: 1200px;
  width: 100%;
  margin: 0 auto;
  padding: 20px;
}

.footer {
  background: #f5f5f5;
  text-align: center;
  padding: 20px;
  color: #666;
  margin-top: auto;
}
</style>
