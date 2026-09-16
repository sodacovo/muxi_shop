<template>
  <div class="user-page">
    <div class="page-header">
      <h2>个人中心</h2>
    </div>

    <el-row :gutter="20">
      <el-col :span="8">
        <el-card class="user-card">
          <div class="user-info">
            <el-avatar :size="80" :src="userStore.userInfo?.avatar">
              {{ userStore.userInfo?.name?.charAt(0) || 'U' }}
            </el-avatar>
            <h3>{{ userStore.userInfo?.name || '未设置昵称' }}</h3>
            <p>{{ userStore.userInfo?.email }}</p>
          </div>
        </el-card>

        <el-card class="menu-card">
          <el-menu :default-active="activeMenu" @select="handleMenuSelect">
            <el-menu-item index="info">
              <el-icon><User /></el-icon>
              <span>基本信息</span>
            </el-menu-item>
            <el-menu-item index="password">
              <el-icon><Lock /></el-icon>
              <span>修改密码</span>
            </el-menu-item>
          </el-menu>
        </el-card>
      </el-col>

      <el-col :span="16">
        <!-- 基本信息 -->
        <el-card v-if="activeMenu === 'info'">
          <template #header>
            <span>基本信息</span>
          </template>
          <el-form :model="userForm" label-width="100px">
            <el-form-item label="头像">
              <el-upload
                :show-file-list="false"
                :before-upload="handleAvatarUpload"
                action="#"
              >
                <el-avatar :size="80" :src="userForm.avatar">
                  {{ userForm.name?.charAt(0) || 'U' }}
                </el-avatar>
                <span class="upload-tip">点击更换头像</span>
              </el-upload>
            </el-form-item>

            <el-form-item label="昵称">
              <el-input v-model="userForm.name" />
            </el-form-item>

            <el-form-item label="邮箱">
              <el-input v-model="userForm.email" disabled />
            </el-form-item>

            <el-form-item label="手机号">
              <el-input v-model="userForm.mobile" />
            </el-form-item>

            <el-form-item label="生日">
              <el-date-picker
                v-model="userForm.birthday"
                type="date"
                placeholder="选择日期"
                format="YYYY-MM-DD"
                value-format="YYYY-MM-DD"
              />
            </el-form-item>

            <el-form-item>
              <el-button type="primary" @click="handleUpdateInfo">保存修改</el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 修改密码 -->
        <el-card v-if="activeMenu === 'password'">
          <template #header>
            <span>修改密码</span>
          </template>
          <el-form ref="passwordFormRef" :model="passwordForm" :rules="passwordRules" label-width="100px">
            <el-form-item label="手机号" prop="phone">
              <el-input v-model="passwordForm.phone" />
            </el-form-item>
            <el-form-item label="验证码" prop="verify_code">
              <el-input v-model="passwordForm.verify_code" style="width: 150px" />
              <el-button style="margin-left: 10px" @click="handleSendCode" :disabled="codeCooldown > 0">
                {{ codeCooldown > 0 ? `${codeCooldown}s` : '发送验证码' }}
              </el-button>
            </el-form-item>
            <el-form-item label="旧密码" prop="old_password">
              <el-input v-model="passwordForm.old_password" type="password" show-password />
            </el-form-item>
            <el-form-item label="新密码" prop="new_password">
              <el-input v-model="passwordForm.new_password" type="password" show-password />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleChangePassword">修改密码</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { User, Lock } from '@element-plus/icons-vue'
import { ElMessage, FormInstance, FormRules } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { userApi } from '@/utils/api'

const userStore = useUserStore()

const activeMenu = ref('info')
const userForm = reactive({
  name: '',
  email: '',
  mobile: '',
  birthday: '',
  avatar: '',
})

const passwordFormRef = ref<FormInstance>()
const codeCooldown = ref(0)
let codeTimer: ReturnType<typeof setInterval> | null = null

const passwordForm = reactive({
  phone: '',
  verify_code: '',
  old_password: '',
  new_password: '',
})

const passwordRules: FormRules = {
  phone: [{ required: true, message: '请输入手机号', trigger: 'blur' }],
  verify_code: [{ required: true, message: '请输入验证码', trigger: 'blur' }],
  old_password: [{ required: true, message: '请输入旧密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' },
    {
      pattern: /^(?=.*[a-zA-Z])(?=.*\d).{6,20}$/,
      message: '密码需包含字母和数字，长度6-20位',
      trigger: 'blur',
    },
  ],
}

const handleMenuSelect = (index: string) => {
  activeMenu.value = index
}

const handleUpdateInfo = async () => {
  try {
    await userApi.updateUser(userForm)
    ElMessage.success('修改成功')
    userStore.fetchUserInfo()
  } catch {
    ElMessage.error('修改失败')
  }
}

const handleAvatarUpload = async (file: File) => {
  try {
    const res = await userApi.uploadAvatar(file)
    userForm.avatar = res.data.avatar_url
    ElMessage.success('头像上传成功')
  } catch {
    ElMessage.error('头像上传失败')
  }
  return false
}

const handleSendCode = async () => {
  if (!passwordForm.phone) {
    ElMessage.warning('请输入手机号')
    return
  }
  try {
    await userApi.sendVerifyCode({ phone: passwordForm.phone })
    ElMessage.success('验证码已发送')
    codeCooldown.value = 60
    codeTimer = setInterval(() => {
      codeCooldown.value--
      if (codeCooldown.value <= 0) {
        clearInterval(codeTimer!)
      }
    }, 1000)
  } catch {
    ElMessage.error('发送失败')
  }
}

const handleChangePassword = async () => {
  if (!passwordFormRef.value) return

  await passwordFormRef.value.validate(async (valid) => {
    if (valid) {
      try {
        await userApi.modifyPassword(passwordForm)
        ElMessage.success('密码修改成功')
        passwordFormRef.value?.resetFields()
      } catch {
        ElMessage.error('修改失败')
      }
    }
  })
}

onMounted(() => {
  if (userStore.userInfo) {
    Object.assign(userForm, userStore.userInfo)
  }
})
</script>

<style scoped>
.user-page {
  padding: 20px 0;
}

.user-info {
  text-align: center;
}

.user-info h3 {
  margin: 12px 0 4px;
}

.user-info p {
  color: #666;
  font-size: 14px;
}

.menu-card {
  margin-top: 20px;
}

.upload-tip {
  display: block;
  margin-top: 8px;
  color: #409eff;
  font-size: 12px;
}
</style>
