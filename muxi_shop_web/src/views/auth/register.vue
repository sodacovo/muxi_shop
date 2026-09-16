<template>
  <div class="register-container">
  <div class="login" v-if="isMounted">
    <div class="logo-area">
      <img src="@/assets/images/logo/logo-big.png" alt="木犀商城" />
    </div>
    <div class="name">木犀推荐站  欢迎注册</div>
    <div class="register-box">
      <h2>用户注册（后续用邮箱登录）</h2>

      <div class="verify-type">
        <button :class="verifyType === 'email' ? 'active' : ''" @click="verifyType = 'email'" type="button">邮箱接收验证码</button>
        <button :class="verifyType === 'phone' ? 'active' : ''" @click="verifyType = 'phone'" type="button">手机号接收验证码</button>
      </div>

      <form @submit.prevent="handleRegister" class="register-form">
        <div class="form-item">
          <input type="email" v-model="form.email" placeholder="请输入邮箱（用于登录，必填）" required />
        </div>
        <div class="form-item">
          <input type="text" v-model="verifyAccount" :placeholder="verifyType === 'email' ? '请输入邮箱（需与登录邮箱一致）' : '请输入11位手机号'" required />
        </div>
        <div class="form-item verify-code">
          <input type="text" v-model="form.verify_code" placeholder="请输入4位验证码" maxlength="4" required autocomplete="off" />
          <button type="button" class="send-code" :disabled="isSending" @click="handleSendVerifyCode">{{ isSending ? `重新发送(${count}s)` : '发送验证码' }}</button>
        </div>
        <div class="form-item">
          <input type="text" v-model="form.name" placeholder="请输入姓名" required autocomplete="off" />
        </div>
        <div class="form-item">
          <input type="password" v-model="form.password" placeholder="请输入密码（至少6位）" maxlength="20" required autocomplete="new-password" />
        </div>
        <button type="submit" class="register-btn">注册并前往登录</button>
      </form>

      <div class="login-link">已有账号？<a href="/login" @click.prevent="$router.push('/login')">立即登录（用邮箱+密码）</a></div>
    </div>
  </div>
</div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { userApi } from '@/utils/api'

const router = useRouter()
const verifyType = ref<'email' | 'phone'>('email')
const isSending = ref(false)
const count = ref(60)
const verifyAccount = ref('')
const form = reactive({ email: '', verify_code: '', name: '', password: '', mobile: '' })

const handleSendVerifyCode = async () => {
  if (isSending.value) return
  if (!form.email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) { alert('请输入正确的邮箱'); return }
  if (!verifyAccount.value) { alert('请输入收验证码的账号'); return }
  if (verifyType.value === 'email' && verifyAccount.value !== form.email) { alert('收验证码的邮箱需与登录邮箱一致'); return }
  if (verifyType.value === 'phone' && !/^1[3-9]\d{9}$/.test(verifyAccount.value)) { alert('请输入正确的手机号'); return }
  try {
    isSending.value = true
    await userApi.sendVerifyCode({ phone: verifyAccount.value })
    alert('验证码发送成功')
    const timer = setInterval(() => {
      count.value--
      if (count.value <= 0) { clearInterval(timer); isSending.value = false; count.value = 60 }
    }, 1000)
  } catch { isSending.value = false; count.value = 60 }
}

const handleRegister = async () => {
  if (!form.email || !form.verify_code || !form.name || !form.password) { alert('请填写完整信息'); return }
  if (form.password.length < 6) { alert('密码至少6位'); return }
  try {
    // @ts-ignore
    await userApi.register({
      email: form.email, name: form.name, password: form.password,
      verify_code: form.verify_code,
      phone: verifyAccount.value,
      mobile: verifyType.value === 'phone' ? verifyAccount.value : '',
    } as any)
    alert(`注册成功！即将跳转到登录页（请用邮箱 ${form.email} 登录）`)
    router.push('/login')
  } catch { /* interceptor handles */ }
}
</script>

<style scoped lang="less">
.register-container { width: 100%; min-height: 100vh; padding: 20px; box-sizing: border-box; background-color: #f5f5f5; display: flex; justify-content: center; align-items: center; background-image: url("@/assets/images/logo/register.png"); }
.logo-area { height: 650px; margin-right: 150px; img { height: 100%; } }
.name { margin-bottom: 550px; margin-right: 180px; font-size: 30px; font-weight: 700; color: #e93854; }
.register-box { width: 100%; max-width: 420px; padding: 30px; background-color: #fff; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.08); box-sizing: border-box; h2 { margin: 0 0 24px; font-size: 20px; color: #333; text-align: center; } }
.verify-type { display: flex; gap: 12px; margin-bottom: 24px; button { flex: 1; padding: 10px 0; border: 1px solid #e5e7eb; border-radius: 4px; background-color: #fff; color: #666; font-size: 14px; cursor: pointer; transition: all 0.2s; &.active { border-color: #409eff; background-color: #f0f7ff; color: #409eff; } } }
.register-form .form-item { margin-bottom: 16px; input { width: 100%; padding: 12px 16px; border: 1px solid #e5e7eb; border-radius: 4px; font-size: 14px; color: #333; box-sizing: border-box; &:focus { outline: none; border-color: #409eff; } } }
.verify-code { display: flex; gap: 12px; .send-code { width: 130px; padding: 0; border: none; border-radius: 4px; background-color: #409eff; color: #fff; font-size: 14px; cursor: pointer; &:disabled { background-color: #a0cfff; cursor: not-allowed; } } }
.register-btn { width: 100%; padding: 12px 0; border: none; border-radius: 4px; background-color: #409eff; color: #fff; font-size: 16px; cursor: pointer; &:hover { background-color: #3086e8; } }
.login-link { margin-top: 20px; font-size: 14px; color: #666; text-align: center; a { color: #409eff; text-decoration: none; &:hover { text-decoration: underline; } } }
</style>
