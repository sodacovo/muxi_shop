// ========== 通用响应格式 ==========

/** 后端统一响应格式：{ status, data } */
export interface BackendResponse<T = any> {
  status: number
  data: T
}

// ========== 用户相关 ==========

export interface User {
  id?: number
  email: string
  name?: string
  mobile?: string
  avatar?: string
  background?: string
  birthday?: string
  gender?: string
  create_time?: string
}

export interface LoginForm {
  username: string
  password: string
}

export interface LoginResponse {
  token: string
  name: string
}

export interface RegisterForm {
  email: string
  name: string
  password: string
  verify_code: string
  phone?: string
}

// ========== 商品相关 ==========

/** 完整商品对象 */
export interface Goods {
  id?: number
  sku_id?: string
  name?: string
  p_price?: number
  jd_price?: number
  price?: number
  image?: string
  shop_name?: string
  shop_id?: number
  type_id?: number
  comment_count?: number
  find?: number
  is_seckill?: boolean
  seckill_price?: number
  seckill_stock?: number
  seckill_start_time?: string
  seckill_end_time?: string
  is_seckill_valid?: boolean
  mk_price?: number
  create_time?: string
}

/** 搜索结果（只有6个字段，与完整Goods不同） */
export interface SearchResult {
  comment_count: number
  image: string
  name: string
  p_price: number
  shop_name: string
  sku_id: string
}

export interface GoodsSearchParams {
  keyword: string
  page?: number
  order_by?: number
}

export interface CategoryGoodsParams {
  category_id: number
  page: number
}

// ========== 购物车相关 ==========

export interface CartItem {
  sku_id: string
  nums: number
  is_delete?: number
  email?: string
  create_time?: string
  goods?: Goods
}

export interface AddToCartParams {
  sku_id: string
  nums: number
}

// ========== 订单相关 ==========

export interface OrderGoods {
  trade_no: string
  sku_id: string
  goods_num: number
  name?: string
  jd_price?: number
  image?: string
  shop_name?: string
  create_time?: string
}

export interface Address {
  id?: number
  email?: string
  signer_name: string
  telphone: string
  district?: string
  signer_address: string
  default?: number
  is_delete?: number
  create_time?: string
}

export interface Order {
  id?: number
  trade_no: string
  order_amount?: number
  address_id?: number
  pay_status?: string
  pay_time?: string
  ali_trade_no?: string
  create_time?: string
  goods?: OrderGoods[]
  address?: Address
}

export interface CreateOrderParams {
  trade: {
    address_id: number
    order_amount: number
  }
  goods: Array<{
    sku_id: string
    nums: number
  }>
}

// ========== 评论相关 ==========

export interface Comment {
  id: number
  user_id: number
  sku_id: string
  content: string
  user_image_url?: string
  reference_name?: string
  score: number
  nickname: string
  reply_count: string
  create_time: string
}

// ========== 秒杀相关 ==========

export interface SeckillSubmit {
  product_id: number
}

/** 秒杀提交返回（code 在 data 内部，和外层 status 不一致） */
export interface SeckillSubmitResult {
  task_id: string
  mode: 'rabbitmq' | 'celery'
  trade_no: string
  msg: string
  expire_seconds: number
  code: number
}

export interface SeckillResult {
  status: 'pending' | 'success' | 'fail'
  trade_no?: string
  order_amount?: number
  msg?: string
  code?: number
}

export interface SeckillStock {
  product_id: number
  product_name: string
  seckill_price: number
  current_stock: number
  is_valid: boolean
  start_time: string
  end_time: string
}
