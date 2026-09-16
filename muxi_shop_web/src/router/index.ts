import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useUserStore } from '@/stores/user'

const routes: RouteRecordRaw[] = [
  // ====== 首页（不带 MainLayout，和 legacy 一致）======
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/home/index.vue'),
    meta: { title: '木犀推荐站' },
  },

  // ====== 商品列表页（legacy: /goods_list/:keyword/:page/:order?）======
  {
    path: '/goods_list/:keyword/:page/:order?',
    name: 'GoodsList',
    component: () => import('@/views/goods/goods-list.vue'),
    meta: { title: '商品列表页' },
    props: true,
  },

  // ====== 商品详情页（legacy: /detail/:sku_id）======
  {
    path: '/detail/:sku_id',
    name: 'GoodsDetail',
    component: () => import('@/views/goods/detail.vue'),
    meta: { title: '商品详情页' },
    props: true,
  },

  // ====== 登录页（legacy: /login/ 和 /login）======
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/auth/login.vue'),
    meta: { title: '欢迎登录' },
    alias: '/login/',
  },

  // ====== 微博回调页（legacy: /weibo/callback）======
  {
    path: '/weibo/callback',
    name: 'WeiboCallback',
    component: () => import('@/views/auth/weibo-callback.vue'),
    meta: { title: '微博登录回调' },
  },

  // ====== 注册页（legacy: /register 和 /register/）======
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/auth/register.vue'),
    meta: { title: '用户注册' },
    alias: '/register/',
  },

  // ====== 忘记密码页（legacy: /forgot-password）======
  {
    path: '/forgot-password',
    name: 'ForgotPassword',
    component: () => import('@/views/auth/forgot-password.vue'),
    meta: { title: '忘记密码' },
  },

  // ====== 购物车（legacy: /cart/detail）======
  {
    path: '/cart/detail',
    name: 'Cart',
    component: () => import('@/views/cart/index.vue'),
    meta: { title: '购物车', requiresAuth: true },
  },

  // ====== 订单页（legacy: /order/:trade_no）======
  {
    path: '/order/:trade_no',
    name: 'Order',
    component: () => import('@/views/order/order.vue'),
    meta: { title: '订单页面', requiresAuth: true },
    props: true,
  },

  // ====== 支付页（legacy: /Order/Pay）======
  {
    path: '/Order/Pay',
    name: 'OrderPay',
    component: () => import('@/views/order/order-pay.vue'),
    meta: { title: '收银台', requiresAuth: true },
  },

  // ====== 个人中心（legacy: /profile）======
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('@/views/user/profile.vue'),
    meta: { title: '个人中心', requiresAuth: true },
  },

  // ====== 秒杀页 ======
  {
    path: '/seckill',
    name: 'Seckill',
    component: () => import('@/views/seckill/index.vue'),
    meta: { title: '限时秒杀' },
  },

  // ====== 用户个人页（老路由）======
  {
    path: '/user',
    name: 'User',
    component: () => import('@/views/user/index.vue'),
    meta: { title: '用户中心', requiresAuth: true },
  },

  // ====== 收货地址管理 ======
  {
    path: '/address',
    name: 'Address',
    component: () => import('@/views/address/index.vue'),
    meta: { title: '收货地址', requiresAuth: true },
  },

  // ====== 搜索页（老路由）======
  {
    path: '/search',
    name: 'Search',
    component: () => import('@/views/goods/search.vue'),
    meta: { title: '商品搜索' },
  },

  // ====== 分类页（老路由）======
  {
    path: '/category/:category_id',
    name: 'Category',
    component: () => import('@/views/goods/category.vue'),
    meta: { title: '商品分类' },
    props: true,
  },

  // ====== 404 ======
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/error/404.vue'),
    meta: { title: '页面不存在' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ left: 0, top: 0 }),
})

router.beforeEach((to) => {
  if (to.meta.title) {
    document.title = to.meta.title as string
  }
  const userStore = useUserStore()
  if (to.meta.requiresAuth && !userStore.isLoggedIn) {
    return { name: 'Login', query: { redirect: to.fullPath } }
  }
})

export default router
