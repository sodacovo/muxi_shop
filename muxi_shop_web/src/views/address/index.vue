<template>
  <div class="address-page">
    <div class="page-header">
      <h2>收货地址</h2>
      <el-button type="primary" @click="handleAdd">新增地址</el-button>
    </div>

    <div v-loading="loading">
      <el-empty v-if="!loading && addressList.length === 0" description="暂无收货地址">
        <el-button type="primary" @click="handleAdd">添加地址</el-button>
      </el-empty>

      <div v-else class="address-list">
        <el-card v-for="addr in addressList" :key="addr.id" class="address-card">
          <div class="address-content">
            <div class="address-info">
              <div class="consignee">
                <span class="name">{{ addr.signer_name }}</span>
                <span class="phone">{{ addr.telphone }}</span>
                <el-tag v-if="addr.default === 1" type="success" size="small">默认</el-tag>
              </div>
              <div class="address-detail">
                {{ addr.district }} {{ addr.signer_address }}
              </div>
            </div>
            <div class="address-actions">
              <el-button text type="primary" @click="handleEdit(addr)">编辑</el-button>
              <el-button text type="danger" @click="handleDelete(addr)">删除</el-button>
              <el-button
                v-if="addr.default !== 1"
                text
                @click="handleSetDefault(addr)"
              >
                设为默认
              </el-button>
            </div>
          </div>
        </el-card>
      </div>
    </div>

    <!-- 地址编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑地址' : '新增地址'"
      width="500px"
    >
      <el-form ref="formRef" :model="addressForm" :rules="rules" label-width="80px">
        <el-form-item label="收货人" prop="signer_name">
          <el-input v-model="addressForm.signer_name" />
        </el-form-item>
        <el-form-item label="手机号" prop="telphone">
          <el-input v-model="addressForm.telphone" />
        </el-form-item>
        <el-form-item label="地区" prop="district">
          <el-input v-model="addressForm.district" placeholder="如：广东省广州市天河区" />
        </el-form-item>
        <el-form-item label="详细地址" prop="signer_address">
          <el-input v-model="addressForm.signer_address" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item>
          <el-checkbox v-model="addressForm.is_default">设为默认地址</el-checkbox>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox, FormInstance, FormRules } from 'element-plus'
import { addressApi } from '@/utils/api'
import type { Address } from '@/types'

const loading = ref(false)
const addressList = ref<Address[]>([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref<FormInstance>()

const addressForm = reactive({
  id: undefined as number | undefined,
  signer_name: '',
  telphone: '',
  district: '',
  signer_address: '',
  is_default: false,
})

const rules: FormRules = {
  signer_name: [{ required: true, message: '请输入收货人', trigger: 'blur' }],
  telphone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '手机号格式不正确', trigger: 'blur' },
  ],
  district: [{ required: true, message: '请输入地区', trigger: 'blur' }],
  signer_address: [{ required: true, message: '请输入详细地址', trigger: 'blur' }],
}

const loadAddresses = async () => {
  loading.value = true
  try {
    const res = await addressApi.list()
    addressList.value = res.data || []
  } catch (error) {
    ElMessage.error('加载地址失败')
  } finally {
    loading.value = false
  }
}

const handleAdd = () => {
  isEdit.value = false
  Object.assign(addressForm, {
    id: undefined,
    signer_name: '',
    telphone: '',
    district: '',
    signer_address: '',
    is_default: false,
  })
  dialogVisible.value = true
}

const handleEdit = (addr: Address) => {
  isEdit.value = true
  Object.assign(addressForm, {
    id: addr.id,
    signer_name: addr.signer_name,
    telphone: addr.telphone,
    district: addr.district,
    signer_address: addr.signer_address,
    is_default: addr.default === 1,
  })
  dialogVisible.value = true
}

const handleDelete = async (addr: Address) => {
  try {
    await ElMessageBox.confirm('确定要删除这个地址吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await addressApi.delete(addr.id!)
    ElMessage.success('删除成功')
    loadAddresses()
  } catch {
    // 取消删除
  }
}

const handleSetDefault = async (addr: Address) => {
  try {
    await addressApi.setDefault(addr.id!)
    ElMessage.success('设置成功')
    loadAddresses()
  } catch {
    ElMessage.error('设置失败')
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (valid) {
      try {
        const data = {
          signer_name: addressForm.signer_name,
          telphone: addressForm.telphone,
          district: addressForm.district,
          signer_address: addressForm.signer_address,
        }

        if (isEdit.value && addressForm.id) {
          await addressApi.edit({ ...data, id: addressForm.id })
        } else {
          await addressApi.create(data)
        }

        ElMessage.success(isEdit.value ? '修改成功' : '添加成功')
        dialogVisible.value = false
        loadAddresses()
      } catch {
        ElMessage.error('操作失败')
      }
    }
  })
}

onMounted(() => {
  loadAddresses()
})
</script>

<style scoped>
.address-page {
  padding: 20px 0;
}

.address-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 20px;
}

.address-card {
  margin-bottom: 0;
}

.address-content {
  display: flex;
  justify-content: space-between;
}

.consignee {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.consignee .name {
  font-weight: bold;
  font-size: 16px;
}

.consignee .phone {
  color: #666;
}

.address-detail {
  color: #666;
}

.address-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
</style>
