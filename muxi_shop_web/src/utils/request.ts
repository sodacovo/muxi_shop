import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse, AxiosError } from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

const service: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

// 不需要 Token 的接口白名单
const NO_AUTH_URLS = [
  '/user/login/',
  '/user/register/',
  '/user/weibo/qrcode/',
  '/user/weibo/qrcode/check/',
  '/user/weibo/callback/',
  '/user/verify-code/',
  '/user/reset-password/verify/',
  '/user/reset-password/',
]

service.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    const urlWithoutParams = config.url!.split('?')[0]
    const isNoAuth = NO_AUTH_URLS.some(u => urlWithoutParams === u)

    if (!isNoAuth && token?.trim()) {
      config.headers.Authorization = `Token ${token.trim()}`
    } else {
      delete config.headers.Authorization
    }
    return config
  },
  (error) => Promise.reject(error)
)

service.interceptors.response.use(
  (response: AxiosResponse) => {
    // 支付宝返回 { alipay: "..." }，直接放行
    if (response.data && typeof response.data === 'object' && 'alipay' in response.data) {
      return response.data
    }
    // 微信二维码返回 arraybuffer，直接放行
    if (response.config.responseType === 'arraybuffer') return response.data
    // 搜索结果总数返回纯数字，直接放行
    if (typeof response.data === 'number') return response.data
    // 数组结果直接放行
    if (Array.isArray(response.data)) return response.data

    const { status, data } = response.data
    // 成功状态码列表（status % 1000 === 0）
    const SUCCESS = [1000, 2000, 3000, 4000, 5000, 6000, 7000]
    // 业务失败状态码列表（status % 1000 === 1，且不等于 1001）
    const FAIL = [2001, 3001, 4001, 4002, 5001, 6001, 7001, 7002]

    if (status !== undefined && SUCCESS.includes(status)) {
      return response.data
    }
    if (status !== undefined && FAIL.includes(status)) {
      const msg = typeof data === 'string' ? data : '操作失败'
      if (status === 4002) {
        const m = typeof data === 'string' ? data : ''
        const final = m.includes('用户名') ? '用户名或密码错误' : m.includes('ticket') ? '二维码已过期' : '操作失败'
        ElMessage.warning(final)
      } else {
        ElMessage.warning(msg)
      }
      return Promise.reject({ status, data })
    }
    // 未知状态码也放行（兼容未来新增）
    return response.data
  },
  (error: AxiosError<{ message?: string; detail?: string }>) => {
    if (error.response) {
      switch (error.response.status) {
        case 401:
          ElMessage.error('登录已过期，请重新登录')
          localStorage.removeItem('token')
          localStorage.removeItem('user')
          router.push('/login')
          break
        case 403: ElMessage.error('没有权限访问'); break
        case 404: ElMessage.error('请求的资源不存在'); break
        case 500: ElMessage.error('服务器错误'); break
        default:
          ElMessage.error(error.response.data?.message || error.response.data?.detail || '请求失败')
      }
    } else if (error.request) {
      ElMessage.error('网络连接失败，请检查网络')
    } else {
      ElMessage.error('请求配置错误')
    }
    return Promise.reject(error)
  }
)

export const request = {
  get<T = any>(url: string, params?: any, config?: AxiosRequestConfig): Promise<T> {
    return service.get(url, params ? { params, ...config } : config)
  },
  post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    return service.post(url, data, config)
  },
  put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    return service.put(url, data, config)
  },
  delete<T = any>(url: string, params?: any, config?: AxiosRequestConfig): Promise<T> {
    return service.delete(url, { params, ...config })
  },
}

export default service
