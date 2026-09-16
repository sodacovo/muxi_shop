<template>
  <div>
    <Shortcut />
    <div class="profile-page">
      <div class="profile-header" :style="bgStyle">
        <div class="avatar-wrapper">
          <el-avatar :size="80" :src="userInfo.avatar || ''" />
        </div>
        <div class="user-info">
          <div class="nickname">{{ userInfo.name || userInfo.email || '未登录' }}</div>
          <div class="edit-btn" @click="activeIndex = 0">编辑资料</div>
        </div>
      </div>
      <div class="profile-content">
        <div class="sidebar">
          <div class="menu-item" :class="{ active: activeIndex === 1 }" @click="activeIndex = 1">基本信息</div>
          <div class="menu-item" :class="{ active: activeIndex === 2 }" @click="activeIndex = 2">收货地址</div>
          <div class="menu-item" :class="{ active: activeIndex === 3 }" @click="activeIndex = 3">我的订单</div>
          <div class="menu-item" :class="{ active: activeIndex === 4 }" @click="activeIndex = 4">安全设置</div>
        </div>
        <div class="main-content">
          <!-- 基本信息 -->
          <div v-if="activeIndex === 0 || activeIndex === 1" class="panel">
            <h3>基本信息</h3>
            <el-form label-width="100px">
              <el-form-item label="头像">
                <el-upload :show-file-list="false" :before-upload="handleAvatarUpload">
                  <el-avatar :size="60" :src="form.avatar || ''" />
                  <span style="margin-left:10px">点击更换</span>
                </el-upload>
              </el-form-item>
              <el-form-item label="昵称"><el-input v-model="form.name" /></el-form-item>
              <el-form-item label="邮箱"><el-input v-model="form.email" disabled /></el-form-item>
              <el-form-item label="手机"><el-input v-model="form.mobile" /></el-form-item>
              <el-form-item><el-button type="primary" @click="saveBasicInfo">保存</el-button></el-form-item>
            </el-form>
          </div>
          <!-- 收货地址 -->
          <div v-if="activeIndex === 2" class="panel">
            <h3>收货地址 <el-button size="small" type="primary" @click="showAddressDialog()">新增地址</el-button></h3>
            <el-table :data="addressList" border>
              <el-table-column prop="signer_name" label="收货人" width="100" />
              <el-table-column prop="telphone" label="电话" width="130" />
              <el-table-column prop="district" label="地区" />
              <el-table-column prop="signer_address" label="详细地址" />
              <el-table-column label="默认" width="80">
                <template #default="{ row }">
                  <el-tag v-if="row.default" type="success">默认</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="150">
                <template #default="{ row }">
                  <el-button size="small" @click="editAddress(row)">编辑</el-button>
                  <el-button size="small" type="danger" @click="removeAddress(row.id)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
          <!-- 我的订单 -->
          <div v-if="activeIndex === 3" class="panel">
            <h3>我的订单</h3>
            <el-tabs v-model="orderStatus">
              <el-tab-pane label="全部" name="-1" />
              <el-tab-pane label="待支付" name="0" />
              <el-tab-pane label="已支付" name="1" />
            </el-tabs>
            <el-table :data="orderList" border>
              <el-table-column prop="trade_no" label="订单号" width="180" />
              <el-table-column prop="order_amount" label="金额" width="100">
                <template #default="{ row }">￥{{ row.order_amount }}</template>
              </el-table-column>
              <el-table-column prop="pay_status" label="状态" width="100">
                <template #default="{ row }">{{ statusMap[row.pay_status] || row.pay_status }}</template>
              </el-table-column>
              <el-table-column prop="create_time" label="创建时间" width="160" />
              <el-table-column label="操作" width="120">
                <template #default="{ row }">
                  <el-button size="small" @click="$router.push(`/order/${row.trade_no}`)">查看</el-button>
                  <el-button v-if="row.pay_status === '0'" size="small" type="primary" @click="$router.push({ path: '/Order/Pay', query: { tradeNo: row.trade_no } })">去支付</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
          <!-- 安全设置 -->
          <div v-if="activeIndex === 4" class="panel">
            <h3>安全设置</h3>
            <div class="security-item">
              <div><span class="label">当前密码</span><el-input type="password" v-model="pwdForm.old_password" style="width:200px" /></div>
              <div><span class="label">新密码</span><el-input type="password" v-model="pwdForm.new_password" style="width:200px" /></div>
              <div><span class="label">验证码</span><el-input v-model="pwdForm.verify_code" style="width:120px" /><el-button size="small" @click="sendPwdCode">获取验证码</el-button></div>
              <div><el-button type="primary" @click="changePassword">修改密码</el-button></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import Shortcut from '@/components/common/Shortcut.vue'
import { ref, reactive, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { userApi, addressApi, orderApi } from '@/utils/api'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const route = useRoute()
const activeIndex = ref(Number(route.query.activeIndex) || 1)
const userInfo = ref<any>(userStore.userInfo || {})
const form = reactive({ name: '', email: '', mobile: '', avatar: '' })
const addressList = ref<any[]>([])
const orderList = ref<any[]>([])
const orderStatus = ref('-1')
const statusMap: Record<string, string> = { '0': '待支付', '1': '已支付', '2': '已完成', '3': '已取消' }
const pwdForm = reactive({ old_password: '', new_password: '', verify_code: '', phone: '' })

const bgStyle = computed(() => userInfo.value.background ? { backgroundImage: `url(${userInfo.value.background})` } : { background: '#f0f0f0' })

onMounted(async () => {
  userStore.checkAuth()
  try {
    const res = await userApi.getCurrentUser()
    userInfo.value = res.data || {}
    Object.assign(form, userInfo.value)
  } catch { /* ignore */ }
  loadOrders()
  loadAddresses()
})

const saveBasicInfo = async () => {
  try {
    await userApi.updateUser({ name: form.name, mobile: form.mobile })
    ElMessage.success('保存成功')
  } catch { /* interceptor */ }
}

const handleAvatarUpload = async (file: File) => {
  try {
    const res = await userApi.uploadAvatar(file)
    form.avatar = res.data.avatar_url
    ElMessage.success('头像上传成功')
  } catch { /* interceptor */ }
  return false
}

const loadAddresses = async () => {
  try {
    const res = await addressApi.list()
    addressList.value = res.data || []
  } catch { /* ignore */ }
}

const showAddressDialog = () => {}
const editAddress = (row: any) => {}
const removeAddress = async (id: number) => {
  try { await addressApi.delete(id); loadAddresses() } catch { /* ignore */ }
}

const loadOrders = async () => {
  try {
    const res = await orderApi.list(orderStatus.value === '-1' ? undefined : orderStatus.value)
    orderList.value = res.data || []
  } catch { /* ignore */ }
}

const sendPwdCode = async () => {
  try { await userApi.sendVerifyCode({ phone: form.mobile || form.email }); ElMessage.success('验证码已发送') } catch { /* ignore */ }
}

const changePassword = async () => {
  try {
    await userApi.modifyPassword(pwdForm)
    ElMessage.success('密码修改成功')
    Object.assign(pwdForm, { old_password: '', new_password: '', verify_code: '' })
  } catch { /* ignore */ }
}
</script>

<style lang="less" scoped>
.profile-page { width: 1190px; margin: 0 auto; }
.profile-header { height: 200px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); display: flex; align-items: center; padding: 0 30px; background-size: cover; .avatar-wrapper { margin-right: 20px; } .user-info .nickname { color: #fff; font-size: 20px; font-weight: 600; } .edit-btn { color: #fff; font-size: 14px; margin-top: 5px; cursor: pointer; &:hover { text-decoration: underline; } } }
.profile-content { display: flex; margin-top: 20px; gap: 20px; }
.sidebar { width: 160px; background: #fff; border-radius: 8px; padding: 15px 0; .menu-item { padding: 12px 20px; cursor: pointer; font-size: 14px; &:hover { background: #f5f5f5; } &.active { color: #e93854; font-weight: 600; border-left: 3px solid #e93854; } } }
.main-content { flex: 1; background: #fff; border-radius: 8px; padding: 20px; }
.panel { h3 { font-size: 16px; margin-bottom: 20px; border-bottom: 1px solid #eee; padding-bottom: 10px; } }
.security-item { .label { display: inline-block; width: 80px; } div { margin-bottom: 15px; } }
</style>
