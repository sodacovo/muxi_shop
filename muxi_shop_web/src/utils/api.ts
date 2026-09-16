import { request } from './request'
import type {
  LoginForm,
  RegisterForm,
  User,
  LoginResponse,
  BackendResponse,
  Goods,
  CartItem,
  AddToCartParams,
  CreateOrderParams,
  Address,
  SeckillSubmit,
  SeckillResult,
  SeckillStock,
  GoodsSearchParams,
  CategoryGoodsParams,
  SearchResult,
  Comment,
} from '@/types'

// ========== 用户模块 ==========

export const userApi = {
  // 登录
  login: (data: LoginForm) => {
    return request.post<BackendResponse<LoginResponse>>('/user/login/', data)
  },

  // 注册
  register: (data: RegisterForm) => {
    return request.post<BackendResponse<User>>('/user/register/', data)
  },

  // 微博扫码登录 - 获取二维码
  getWeiboQrCode: () => {
    return request.get<BackendResponse<{ qrcode_url: string; ticket: string }>>('/user/weibo/qrcode/')
  },

  // 微博扫码登录 - 轮询状态
  checkWeiboQrStatus: (ticket: string) => {
    return request.get<BackendResponse<{ status: 'success' | 'pending' | 'expired'; msg: string; authorization_code?: string }>>('/user/weibo/qrcode/check/', { ticket })
  },

  // 微博扫码登录 - 回调确认
  weiboCallback: (params: { code: string; ticket: string }) => {
    return request.get<BackendResponse<LoginResponse>>('/user/weibo/callback/', params)
  },

  // 获取当前用户信息
  getCurrentUser: () => {
    return request.get<BackendResponse<User>>('/user/current/')
  },

  // 更新用户信息
  updateUser: (data: Partial<User>) => {
    return request.put<BackendResponse<User>>('/user/', data)
  },

  // 发送验证码
  sendVerifyCode: (data: { email?: string; phone?: string }) => {
    return request.post<BackendResponse<any>>('/user/verify-code/', data)
  },

  // 重置密码 - 验证
  resetPasswordVerify: (data: { email?: string; phone?: string; verify_code: string }) => {
    return request.post<BackendResponse<{ reset_token: string }>>('/user/reset-password/verify/', data)
  },

  // 重置密码 - 设置新密码
  resetPassword: (data: { reset_token: string; new_password: string }) => {
    return request.post<BackendResponse<any>>('/user/reset-password/', data)
  },

  // 修改密码
  modifyPassword: (data: {
    old_password: string
    new_password: string
    phone: string
    verify_code: string
  }) => {
    return request.post<BackendResponse<any>>('/user/update-password/', data)
  },

  // 上传头像
  uploadAvatar: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return request.post<BackendResponse<{ avatar_url: string }>>('/user/upload/avatar/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  // 上传背景
  uploadBackground: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return request.post<BackendResponse<{ background_url: string }>>('/user/upload/background/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
}

// ========== 商品模块 ==========

export const goodsApi = {
  // 商品发现页（精选）
  find: () => {
    return request.get<BackendResponse<Goods[]>>('/goods/find/')
  },

  // 分类商品列表
  category: (params: CategoryGoodsParams) => {
    return request.get<BackendResponse<Goods[]>>(
      `/goods/category/${params.category_id}/${params.page}/`
    )
  },

  // 搜索商品（搜索结果只有6个字段：comment_count, image, name, p_price, shop_name, sku_id）
  search: (params: GoodsSearchParams) => {
    return request.get<BackendResponse<SearchResult[]>>(
      `/goods/search/${params.keyword}/${params.page || 1}/${params.order_by || 0}/`
    )
  },

  // 搜索结果总数（返回纯数字）
  searchCount: (keyword: string) => {
    return request.get<number>(`/goods/get_keyword_data_count/${keyword}/`)
  },

  // 获取商品详情
  detail: (sku_id: string) => {
    return request.get<BackendResponse<Goods>>(`/goods/${sku_id}/`)
  },

  // 记录用户行为埋点（⚠️ 用的是商品数据库 id，不是 sku_id）
  recordBehavior: (goodsId: number) => {
    return request.post<BackendResponse<any>>(`/goods/behavior/${goodsId}/`)
  },

  // 推荐商品
  recommend: () => {
    return request.get<BackendResponse<Goods[]>>('/goods/recommend/')
  },

  // 获取菜单
  mainMenu: () => {
    return request.get<BackendResponse<any[]>>('/main_menu/')
  },

  subMenu: (main_menu_id: number) => {
    return request.get<BackendResponse<any[]>>('/sub_menu/', { main_menu_id })
  },
}

// ========== 购物车模块 ==========

export const cartApi = {
  // 获取购物车列表（GET，不是 POST）
  list: () => {
    return request.get<BackendResponse<CartItem[]>>('/cart/')
  },

  // 获取购物车详情（含商品信息，POST）
  detail: () => {
    return request.post<BackendResponse<CartItem[]>>('/cart/detail/')
  },

  // 添加到购物车
  add: (data: AddToCartParams) => {
    return request.post<BackendResponse<any>>('/cart/', data)
  },

  // 更新购物车数量（POST /cart/num/，不是 /cart/update/）
  updateNum: (data: { sku_id: string; nums: number }) => {
    return request.post<BackendResponse<any>>('/cart/num/', data)
  },

  // 删除购物车商品（请求体是数组）
  delete: (sku_ids: string[]) => {
    return request.post<BackendResponse<any>>('/cart/delete/', sku_ids)
  },

  // 获取购物车数量（POST /cart/counts/，不是 /cart/count/）
  count: () => {
    return request.post<BackendResponse<{ nums__sum: number }>>('/cart/counts/')
  },
}

// ========== 订单模块 ==========

export const orderApi = {
  // 创建订单
  create: (data: CreateOrderParams) => {
    return request.post<BackendResponse<any>>('/order/', data)
  },

  // 获取订单列表（pay_status=-1 获取全部）
  list: (pay_status?: string) => {
    return request.get<BackendResponse<any[]>>('/order/', {
      params: pay_status && pay_status !== '-1' ? { pay_status } : {},
    })
  },

  // 获取订单详情（路径是 /order/goods/<trade_no>/）
  detail: (trade_no: string) => {
    return request.get<BackendResponse<any>>(`/order/goods/${trade_no}/`)
  },

  // 更新订单
  update: (data: {
    trade_no: string
    address_id?: number
    pay_status?: string
    ali_trade_no?: string
  }) => {
    return request.post<BackendResponse<any>>('/order/update/', data)
  },
}

// ========== 收货地址模块 ==========

export const addressApi = {
  // 获取地址列表
  list: () => {
    return request.get<BackendResponse<Address[]>>('/address/')
  },

  // 创建地址
  create: (data: Omit<Address, 'id'>) => {
    return request.post<BackendResponse<Address>>('/address/', data)
  },

  // 编辑地址
  edit: (data: Address) => {
    return request.post<BackendResponse<any>>('/address/edit/', data)
  },

  // 删除地址
  delete: (id: number) => {
    return request.post<BackendResponse<any>>('/address/delete/', { id })
  },

  // 设置默认地址
  setDefault: (id: number) => {
    return request.post<BackendResponse<any>>('/address/setDefault/', { id })
  },
}

// ========== 秒杀模块 ==========

export const seckillApi = {
  // 提交秒杀
  submit: (data: SeckillSubmit) => {
    return request.post<BackendResponse<SeckillResult>>('/seckill/submit/', data)
  },

  // 查询秒杀结果
  result: (task_id: string) => {
    return request.get<BackendResponse<SeckillResult>>('/seckill/result/', { task_id })
  },

  // 获取秒杀库存
  stock: (product_ids: number[]) => {
    return request.get<BackendResponse<{ stock_list: SeckillStock[] }>>(
      `/seckill/stock/?product_ids=${product_ids.join(',')}`
    )
  },
}

// ========== 支付模块 ==========
export const payApi = {
  // 发起支付宝支付
  alipay: (data: { tradeNo: string; orderAmount: string }) => {
    return request.post<BackendResponse<{ alipay: string }>>('/pay/alipay/', data)
  },

  // 获取微信二维码
  wechatQrcode: (params: { trade_no: string }) => {
    return request.get<ArrayBuffer>('/pay/wechat/qrcode/', params, { responseType: 'arraybuffer' })
  },

  // 查询微信支付状态
  wechatQuery: (params: { trade_no: string }) => {
    return request.get<BackendResponse<{ pay_status: string }>>('/pay/wechat/query/', params)
  },
}

export const commentApi = {
  // 获取评论总数
  count: (sku_id: string) => {
    return request.get<BackendResponse<number>>('/comment/count/', { sku_id })
  },

  // 获取评论列表（每页15条）
  list: (sku_id: string, page = 1) => {
    return request.get<BackendResponse<Comment[]>>('/comment/detail/', {
      sku_id, page,
    })
  },

  // 我的评论列表
  myList: () => {
    return request.get<BackendResponse<Comment[]>>('/comment/')
  },

  // 发布评论
  create: (data: { sku_id: string; content: string; score: number }) => {
    return request.post<BackendResponse<Comment>>('/comment/', data)
  },

  // 编辑评论
  update: (id: number, data: { content?: string; score?: number }) => {
    return request.put<BackendResponse<Comment>>(`/comment/${id}/`, data)
  },

  // 删除评论
  delete: (id: number) => {
    return request.delete<BackendResponse<Comment>>(`/comment/${id}/`)
  },
}
