<template>
  <div class="header-wrapper">
    <div class="header-container">
      <div class="user-menu">
        <template v-if="!isLoggedIn">
          <router-link to="/login" class="login-link">你好，请登录</router-link>
          <span class="separator">|</span>
          <router-link to="/register" class="register-link">免费注册</router-link>
        </template>
        <template v-else>
          <router-link to="/profile" class="username-link">{{ userName }}</router-link>
          <span class="separator">|</span>
          <a href="#" @click.prevent="logout" class="logout-link">退出</a>
        </template>
        <span class="separator">|</span>
        <router-link to="/profile?activeIndex=3" class="order-link">我的订单</router-link>
      </div>
      <div class="beian-container">
        <a target="_blank" href="https://beian.mps.gov.cn/#/query/webSearch?code=44122502000058" class="beian-item">
          <img src="@/assets/images/logo/gongan.png" alt="公安备案" style="height:14px;margin-right:4px;" />
          <span>粤公网安备44122502000058号</span>
        </a>
        <span class="beian-sep">|</span>
        <a target="_blank" href="https://beian.miit.gov.cn/" class="beian-item">粤ICP备2025484777号-1</a>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()
const isLoggedIn = computed(() => userStore.isLoggedIn)
const userName = computed(() => userStore.userName)

const logout = () => {
  userStore.logout()
  router.push('/')
}
</script>

<style lang="less" scoped>
@bg: #e3e4e5;
@gray: #999;
@dark: #666;
@red: #e1251b;
@hover: #c81623;

.header-wrapper {
  background: @bg;
  height: 30px;
  line-height: 30px;
  width: 100%;
  font-size: 12px;
}
.header-container {
  width: 1190px;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.user-menu {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  .separator {
    color: #ccc;
    margin: 0 8px;
  }
  a {
    color: @gray;
    text-decoration: none;
    transition: color 0.2s;
    white-space: nowrap;
    &:hover {
      color: @hover;
      text-decoration: underline;
    }
  }
  .login-link {
    margin-right: 4px;
  }
  .register-link {
    color: @red;
    font-weight: 500;
  }
  .username-link {
    color: @dark;
  }
}
.beian-container {
  display: flex;
  align-items: center;
  color: @gray;
  font-size: 12px;
  .beian-item {
    color: @gray;
    text-decoration: none;
    display: flex;
    align-items: center;
    transition: color 0.2s;
    white-space: nowrap;
    &:hover {
      color: @hover;
    }
  }
  .beian-sep {
    margin: 0 8px;
    color: #ccc;
  }
}
</style>
