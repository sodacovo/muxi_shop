<template>
  <div class="login" v-if="isMounted">
    <div class="title">
      <div class="logo">
        <img src="@/assets/images/logo/logo-big.png" alt="木犀商城" />
      </div>
      <div class="name">木犀推荐站</div>
      <div class="name">忘记密码</div>
    </div>

    <div class="login-info">
      <div class="login-content">
        <el-steps :active="currentStep" finish-status="success" class="step-bar" align-center>
          <el-step title="身份验证" icon="User" />
          <el-step title="验证码验证" icon="Message" />
          <el-step title="重置密码" icon="Key" />
        </el-steps>

        <!-- 步骤1：输入邮箱/手机号 -->
        <div v-show="currentStep === 0" class="step-content">
          <div class="login-name">请输入你的邮箱或手机号</div>
          <div class="login-account">
            <label for="account">
              <span class="icon-span">{{ isEmailInput ? '@' : '📱' }}</span>
            </label>
            <input type="text" id="account" :placeholder="isEmailInput ? '请输入邮箱' : '请输入手机号'" v-model="account" @input="clearError" @keyup.enter="handleStep1Submit" />
            <el-button type="text" class="switch-btn" @click="switchAccountType">{{ isEmailInput ? '使用手机号验证' : '使用邮箱验证' }}</el-button>
          </div>
          <div class="login-error" v-if="errorMsg">{{ errorMsg }}</div>
          <button class="login-commit" @click="handleStep1Submit" :disabled="!isAccountValid">
            <span v-if="!isLoading">发送验证码</span>
            <span v-else>发送中...</span>
          </button>
        </div>

        <!-- 步骤2：输入验证码 -->
        <div v-show="currentStep === 1" class="step-content">
          <div class="login-name">验证码已发送至 <span class="highlight">{{ maskedAccount }}</span></div>
          <div class="login-verification">
            <label for="verifyCode"><span class="icon-span">🔑</span></label>
            <input type="text" id="verifyCode" placeholder="请输入4位验证码" v-model="verifyCode" maxlength="4" @keyup.enter="handleStep2Submit" autofocus />
            <span class="resend-code" @click="resendCode" :style="{ cursor: !isCounting ? 'pointer' : 'default', color: !isCounting ? '#409eff' : '#999' }">
              {{ isCounting ? `${countdown}s后重发` : '重新发送' }}
            </span>
          </div>
          <div class="login-error" v-if="errorMsg">{{ errorMsg }}</div>
          <button class="login-commit" @click="handleStep2Submit" :disabled="verifyCode.length !== 4">
            <span v-if="!isLoading">下一步</span>
            <span v-else>验证中...</span>
          </button>
          <button class="login-back" @click="goBackToStep0">返回上一步</button>
        </div>

        <!-- 步骤3：设置新密码 -->
        <div v-show="currentStep === 2" class="step-content">
          <div class="login-name">设置新密码</div>
          <div class="login-password">
            <label for="newPassword"><span class="icon-span">🔒</span></label>
            <input type="password" id="newPassword" placeholder="6-20位（含字母+数字）" v-model="newPassword" @keyup.enter="handleStep3Submit" />
          </div>
          <div class="login-password" style="margin-top: 15px;">
            <label for="confirmPassword"><span class="icon-span">✅</span></label>
            <input type="password" id="confirmPassword" placeholder="再次输入新密码" v-model="confirmPassword" @keyup.enter="handleStep3Submit" />
          </div>
          <div class="login-error" v-if="confirmPassword && newPassword !== confirmPassword">两次密码不一致</div>
          <div class="login-error" v-if="errorMsg && newPassword === confirmPassword">{{ errorMsg }}</div>
          <button class="login-commit" @click="handleStep3Submit" :disabled="!isPasswordValid">
            <span v-if="!isLoading">确认重置</span>
            <span v-else>重置中...</span>
          </button>
          <button class="login-back" @click="currentStep = 1">返回上一步</button>
        </div>

        <!-- 步骤4：成功 -->
        <div v-show="currentStep === 3" class="success-content">
          <el-icon class="success-icon" color="#67c23a" :size="48"><SuccessFilled /></el-icon>
          <div class="success-title">密码重置成功！</div>
          <div class="success-desc">3秒后自动跳转至登录页</div>
          <button class="login-commit" @click="goToLogin" style="margin-top: 20px;">立即前往登录</button>
        </div>

        <div class="back-login" @click="goToLogin">← 返回登录页</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElSteps, ElStep } from 'element-plus'
import { SuccessFilled } from '@element-plus/icons-vue'
import { userApi } from '@/utils/api'

const router = useRouter()
const isMounted = ref(false)
const currentStep = ref(0)
const isLoading = ref(false)
const errorMsg = ref('')
const isCounting = ref(false)
const countdown = ref(60)
let countdownTimer: ReturnType<typeof setInterval> | null = null

const account = ref('')
const isEmailInput = ref(true)
const isAccountValid = computed(() => {
  const emailReg = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  const phoneReg = /^1[3-9]\d{9}$/
  return isEmailInput.value ? emailReg.test(account.value) : phoneReg.test(account.value)
})

const verifyCode = ref('')
const maskedAccount = ref('')
const resetToken = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const isPasswordValid = computed(() => {
  const pwdReg = /^(?=.*[a-zA-Z])(?=.*\d).{6,20}$/
  return pwdReg.test(newPassword.value) && newPassword.value === confirmPassword.value
})

isMounted.value = true

onUnmounted(() => {
  if (countdownTimer) clearInterval(countdownTimer)
})

const clearError = () => { errorMsg.value = '' }
const goToLogin = () => { router.push('/login') }

const switchAccountType = () => {
  isEmailInput.value = !isEmailInput.value
  account.value = ''
  verifyCode.value = ''
  resetToken.value = ''
  clearError()
}

const handleStep1Submit = async () => {
  if (!isAccountValid.value) return
  isLoading.value = true
  errorMsg.value = ''
  try {
    const data = isEmailInput.value ? { phone: account.value } : { phone: account.value }
    await userApi.sendVerifyCode(data)
    maskedAccount.value = isEmailInput.value
      ? account.value.substring(0, 3) + '***' + account.value.split('@')[1]
      : account.value.substring(0, 3) + '****' + account.value.substring(7)
    currentStep.value = 1
    startCountdown()
  } catch { /* interceptor handles */ } finally {
    isLoading.value = false
  }
}

const resendCode = async () => {
  if (isCounting.value) return
  await handleStep1Submit()
}

const startCountdown = () => {
  isCounting.value = true
  countdown.value = 60
  countdownTimer = setInterval(() => {
    countdown.value--
    if (countdown.value <= 0) { clearInterval(countdownTimer!); isCounting.value = false }
  }, 1000)
}

const goBackToStep0 = () => {
  currentStep.value = 0
  verifyCode.value = ''
  resetToken.value = ''
  if (countdownTimer) { clearInterval(countdownTimer!); isCounting.value = false }
}

const handleStep2Submit = async () => {
  if (verifyCode.value.length !== 4) return
  isLoading.value = true
  errorMsg.value = ''
  try {
    const data = isEmailInput.value ? { email: account.value, verify_code: verifyCode.value } : { phone: account.value, verify_code: verifyCode.value }
    await userApi.resetPasswordVerify(data)
    currentStep.value = 2
  } catch { /* interceptor handles */ } finally {
    isLoading.value = false
  }
}

const handleStep3Submit = async () => {
  if (!isPasswordValid.value) return
  isLoading.value = true
  errorMsg.value = ''
  try {
    await userApi.resetPassword({ reset_token: resetToken.value, new_password: newPassword.value })
    currentStep.value = 3
    setTimeout(goToLogin, 3000)
  } catch { /* interceptor handles */ } finally {
    isLoading.value = false
  }
}
</script>

<style scoped lang="less">
.login { min-height: 100vh; background: #f5f5f5; padding-top: 50px; box-sizing: border-box; background-image: url('@/assets/images/logo/login.png'); }
.title { text-align: center; margin-bottom: 30px; .logo { width: 100px; height: 30px; margin: 0 auto 20px; margin-left: 250px; img { width: 100%; } } .name { font-size: 24px; margin-bottom: 10px; color: #e93854; } }
.login-info { display: flex; justify-content: center; }
.login-content { width: 100%; max-width: 400px; background: #fff; border-radius: 8px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
.step-bar { margin-bottom: 30px; }
.login-name { font-size: 18px; font-weight: 600; color: #333; margin-bottom: 20px; }
.login-error { color: #f56c6c; font-size: 12px; height: 20px; margin-bottom: 10px; }
.login-commit { width: 100%; height: 44px; background-color: #409eff; color: #fff; border: none; border-radius: 4px; font-size: 16px; cursor: pointer; &:hover { background-color: #66b1ff; } &:disabled { background-color: #a0cfff; cursor: not-allowed; } }
.login-back { width: 100%; height: 44px; background-color: #f5f5f5; color: #666; border: none; border-radius: 4px; font-size: 16px; cursor: pointer; margin-top: 15px; &:hover { background-color: #eee; } }
.back-login { text-align: center; margin-top: 20px; font-size: 14px; color: #409eff; cursor: pointer; &:hover { text-decoration: underline; } }
.login-account, .login-verification, .login-password { position: relative; margin-bottom: 20px; label { position: absolute; left: 10px; top: 50%; transform: translateY(-50%); .icon-span { font-size: 20px; color: #666; } } input { width: 100%; height: 44px; padding-left: 40px; padding-right: 120px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; box-sizing: border-box; &:focus { outline: none; border-color: #409eff; } } .switch-btn { position: absolute; right: 10px; top: 50%; transform: translateY(-50%); padding: 0; font-size: 12px; } .resend-code { position: absolute; right: 10px; top: 50%; transform: translateY(-50%); font-size: 12px; } }
.highlight { color: #e93854; font-weight: 500; }
.success-content { text-align: center; padding: 20px 0; .success-title { font-size: 20px; color: #333; margin: 15px 0 10px; } .success-desc { font-size: 14px; color: #999; margin-bottom: 20px; } }
</style>
