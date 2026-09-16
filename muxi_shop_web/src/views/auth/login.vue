<template>
  <div class="login" v-if="isMounted">
    <!-- 微博扫码登录弹窗 -->
    <el-dialog v-model="showWeiboQr" title="微博扫码登录" width="300px" :close-on-click-modal="false" :before-close="handleQrModalClose">
      <div class="qr-container" v-loading="isQrLoading" element-loading-text="生成二维码中...">
        <div v-if="weiboQrUrl && weiboQrUrl.startsWith('data:image/png;base64,')" class="qr-img-wrapper">
          <img :src="weiboQrUrl" alt="微博登录二维码" class="qr-image" @error="handleQrImgError" />
          <p class="qr-tip">请用微博APP扫码登录</p>
          <p class="qr-expire">二维码有效期5分钟</p>
        </div>
        <div v-else-if="!isQrLoading" class="qr-load-error">
          二维码加载失败，请点击刷新
          <el-button type="text" @click="refreshWeiboQr">刷新</el-button>
        </div>
      </div>
      <div v-if="qrStatus" class="qr-status" :class="{ success: qrStatus === 'success', error: qrStatus === 'error' }">
        {{ qrStatusText }}
      </div>
    </el-dialog>

    <!-- 登录主体 -->
    <div class="title">
      <div class="logo">
        <img src="@/assets/images/logo/logo-big.png" alt="木犀商城" />
      </div>
      <div class="name">木犀推荐站</div>
      <div class="name">欢迎登录</div>
    </div>

    <div class="login-info">
      <div class="login-content">
        <div class="title-warning">
          <img src="@/assets/images/login/warning.png" alt="警告" />
          <span>不会以任何理由要求你转账，谨防诈骗。</span>
        </div>

        <div class="login-name">账户登录</div>

        <div class="login-username">
          <label for="username">
            <img src="@/assets/images/login/username.png" alt="用户名" />
          </label>
          <input type="text" id="username" placeholder="请输入你的邮箱" v-model="userInfo.username" @input="clearError" @keyup.enter="handleLogin" />
        </div>

        <div class="login-password">
          <label for="password">
            <img src="@/assets/images/login/password.png" alt="密码" />
          </label>
          <input type="password" id="password" placeholder="请输入密码" v-model="userInfo.password" @input="clearError" @keyup.enter="handleLogin" />
        </div>

        <div class="login-error" v-if="loginError">{{ loginError }}</div>

        <a href="javascript:void(0)" class="forget-password" @click="goToForgotPassword">忘记密码</a>

        <button class="login-commit" @click="handleLogin" :disabled="isLoading || !userInfo.username.trim() || !userInfo.password.trim()">
          <span v-if="!isLoading">登录</span>
          <span v-else>登录中...</span>
        </button>

        <div class="register">
          <span>还没有账号？</span>
          <a href="javascript:void(0)" @click="goToRegister">立即注册</a>
        </div>

        <div class="login-divider">
          <span class="line"></span>
          <span class="text">其他登录方式</span>
          <span class="line"></span>
        </div>

        <button class="weibo-btn" @click="openWeiboQrModal">
          <img src="@/assets/images/logo/weibo_qr.png" alt="微博登录" />
          微博扫码登录
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { userApi } from '@/utils/api'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const isMounted = ref(false)
const isLoading = ref(false)
const loginError = ref('')
const userInfo = reactive({ username: '', password: '' })

const showWeiboQr = ref(false)
const isQrLoading = ref(false)
const weiboQrUrl = ref('')
const weiboTicket = ref('')
const qrStatus = ref('')
const qrStatusText = ref('')
let qrPollTimer: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  isMounted.value = true
  if (userStore.isLoggedIn) {
    router.push('/')
  }
})

onBeforeUnmount(() => {
  if (qrPollTimer) clearInterval(qrPollTimer)
})

const clearError = () => { loginError.value = '' }

const goToRegister = () => { router.push('/register') }

const handleLogin = async () => {
  const { username, password } = userInfo
  if (!username.trim()) { loginError.value = '请输入邮箱'; return }
  if (!password.trim()) { loginError.value = '请输入密码'; return }
  const emailReg = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  if (!emailReg.test(username)) { loginError.value = '请输入正确的邮箱格式'; return }
  if (isLoading.value) return

  isLoading.value = true
  loginError.value = ''
  try {
    const ok = await userStore.login(username, password)
    if (ok) {
      ElMessage.success('登录成功，即将跳转首页')
      setTimeout(() => router.push('/'), 1000)
    } else {
      loginError.value = '用户名或密码错误'
    }
  } catch {
    loginError.value = '网络异常，登录失败'
  } finally {
    isLoading.value = false
  }
}

const openWeiboQrModal = async () => {
  showWeiboQr.value = true
  await refreshWeiboQr()
}

const refreshWeiboQr = async () => {
  isQrLoading.value = true
  qrStatus.value = ''
  qrStatusText.value = ''
  weiboQrUrl.value = ''
  try {
    const res = await userApi.getWeiboQrCode()
    if (res.data?.qrcode_url) {
      weiboQrUrl.value = res.data.qrcode_url
      weiboTicket.value = res.data.ticket
      startQrPoll()
    } else {
      qrStatus.value = 'error'
      qrStatusText.value = '二维码生成失败'
    }
  } catch {
    qrStatus.value = 'error'
    qrStatusText.value = '网络异常，二维码加载失败'
  } finally {
    isQrLoading.value = false
  }
}

const startQrPoll = () => {
  if (qrPollTimer) clearInterval(qrPollTimer)
  qrPollTimer = setInterval(async () => {
    try {
      const res = await userApi.checkWeiboQrStatus(weiboTicket.value)
      if (res.data?.status === 'success') {
        if (res.data.authorization_code) {
          clearInterval(qrPollTimer!)
          isQrLoading.value = true
          qrStatus.value = 'pending'
          qrStatusText.value = '登录中...'
          const ok = await userStore.weiboLogin(res.data.authorization_code, weiboTicket.value)
          if (ok) {
            qrStatus.value = 'success'
            qrStatusText.value = '登录成功，即将跳转...'
            ElMessage.success('微博登录成功')
            setTimeout(() => { showWeiboQr.value = false; router.push('/') }, 1000)
          } else {
            qrStatus.value = 'error'
            qrStatusText.value = '登录失败'
          }
        }
      } else if (res.data?.status === 'expired') {
        qrStatus.value = 'error'
        qrStatusText.value = '二维码已过期，请点击刷新'
        clearInterval(qrPollTimer!)
      } else {
        qrStatus.value = 'pending'
        qrStatusText.value = res.data?.msg || '请用微博APP扫码并确认登录'
      }
    } catch {
      clearInterval(qrPollTimer!)
    }
  }, 3000)
}

const handleQrImgError = () => { weiboQrUrl.value = '' }

const handleQrModalClose = () => {
  if (qrPollTimer) clearInterval(qrPollTimer)
  showWeiboQr.value = false
  weiboQrUrl.value = ''
  weiboTicket.value = ''
  qrStatus.value = ''
  qrStatusText.value = ''
}

const goToForgotPassword = () => { router.push('/forgot-password') }
</script>

<style scoped lang="less">
.login {
  min-height: 100vh;
  background: #f5f5f5;
  padding-top: 50px;
  box-sizing: border-box;
  background-image: url('@/assets/images/logo/login.png');
}
.title {
  text-align: center;
  margin-bottom: 30px;
  .logo { width: 100px; height: 30px; margin: 0 auto 20px; margin-left: 250px; img { width: 100%; height: 100%; } }
  .name { font-size: 24px; margin-bottom: 10px; color: #e93854; }
}
.login-info { display: flex; justify-content: center; }
.login-content {
  width: 100%; max-width: 400px; background: #fff; border-radius: 8px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}
.title-warning { display: flex; align-items: center; color: #f56c6c; font-size: 12px; margin-bottom: 20px; img { width: 16px; height: 16px; margin-right: 5px; } }
.login-name { font-size: 18px; font-weight: 600; color: #333; margin-bottom: 20px; }
.login-username, .login-password {
  position: relative; margin-bottom: 20px;
  label { position: absolute; left: 10px; top: 50%; transform: translateY(-50%); img { width: 20px; height: 20px; } }
  input { width: 100%; height: 44px; padding-left: 40px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; box-sizing: border-box; &:focus { outline: none; border-color: #409eff; } }
}
.login-error { color: #f56c6c; font-size: 12px; height: 20px; margin-bottom: 10px; }
.forget-password { display: block; text-align: right; color: #409eff; font-size: 14px; margin-bottom: 20px; text-decoration: none; &:hover { text-decoration: underline; } }
.login-commit {
  width: 100%; height: 44px; background-color: #409eff; color: #fff; border: none; border-radius: 4px; font-size: 16px; cursor: pointer;
  &:hover { background-color: #66b1ff; }
  &:disabled { background-color: #a0cfff; cursor: not-allowed; }
}
.register { text-align: center; margin-top: 20px; font-size: 14px; a { color: #409eff; text-decoration: none; margin-left: 5px; &:hover { text-decoration: underline; } } }
.login-divider { display: flex; align-items: center; margin: 20px 0; .line { flex: 1; height: 1px; background-color: #eee; } .text { padding: 0 10px; font-size: 12px; color: #999; } }
.weibo-btn {
  width: 100%; height: 44px; background-color: #e6162d; color: #fff; border: none; border-radius: 4px; font-size: 16px; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  img { width: 20px; height: 20px; margin-right: 10px; }
  &:hover { background-color: #c81623; }
}
.qr-container { text-align: center; padding: 10px 0; .qr-image { width: 180px; height: 180px; margin: 0 auto 10px; } .qr-tip { color: #333; font-size: 14px; margin-bottom: 5px; } .qr-expire { color: #999; font-size: 12px; } .qr-load-error { color: #f56c6c; padding: 20px 0; } }
.qr-status { margin-top: 10px; padding: 5px 0; font-size: 14px; &.success { color: #67c23a; } &.error { color: #f56c6c; } }
</style>
