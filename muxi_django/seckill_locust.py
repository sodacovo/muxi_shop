from locust import HttpUser, task, between
import json
import logging
import random

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seckill_locust")

# 定义压测用的用户ID池（200个不同用户：26~225）
USER_ID_POOL = list(range(26, 226))  # 26、27、28…225，共200个不同user_id
# 秒杀商品ID
TEST_PRODUCT_ID = 4

class SeckillUser(HttpUser):
    """
    秒杀压测用户类：200个不同用户，每个仅发1次秒杀请求
    """
    wait_time = between(1, 3)
    
    def on_start(self):
        """
        每个用户启动时：
        1. 随机分配唯一user_id（从200个池中选，避免重复）
        2. 登录（用分配的user_id对应账号，或统一测试账号+不同user_id）
        3. 标记是否已秒杀（初始为False，确保仅1次请求）
        """
        # 核心改1：为每个用户分配唯一user_id（26~225）
        self.user_id = random.choice(USER_ID_POOL)
        # 核心改2：标志位——记录该用户是否已发过秒杀请求（初始未发）
        self.has_seckilled = False
        
        try:
            # 登录逻辑：如果你的系统是“用户名=user{user_id}”，则动态生成
            login_data = {
                "username": f"test_user{self.user_id}",  # 不同用户：test_user26、test_user27…
                "password": "test123456"  # 所有测试账号统一密码
            }
            login_response = self.client.post(
                url="/user/login/",
                json=login_data,
                timeout=5
            )
            login_result = login_response.json()
            if "token" in login_result:
                self.token = login_result["token"]
                logger.info(f"用户{self.user_id}登录成功，token={self.token[:10]}...")
            else:
                raise Exception(f"用户{self.user_id}登录失败：{login_result}")
        except Exception as e:
            logger.error(f"用户{self.user_id}登录异常：{str(e)}")
            raise e

    @task(1)
    def seckill_full_flow(self):
        """
        核心改3：每个用户仅执行1次秒杀请求，触发后标记为已秒杀
        """
        # 如果已发过秒杀请求，直接返回（不再执行）
        if self.has_seckilled:
            return
        
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

        try:
            # 步骤1：查询商品详情
            goods_detail_url = f"/goods/detail/{TEST_PRODUCT_ID}/"
            goods_response = self.client.get(goods_detail_url, headers=headers, timeout=3)
            goods_result = goods_response.json()
            if not goods_result.get("is_seckill", False):
                logger.warning(f"用户{self.user_id}：商品{TEST_PRODUCT_ID}非秒杀商品，跳过")
                self.has_seckilled = True  # 标记为已执行，避免重复检查
                return

            # 步骤2：提交秒杀请求（用唯一user_id）
            seckill_data = {
                "user_id": self.user_id,  # 动态唯一user_id，而非固定26
                "product_id": TEST_PRODUCT_ID
            }
            seckill_response = self.client.post(
                url="/seckill/submit/",
                headers=headers,
                json=seckill_data,
                timeout=5
            )
            seckill_result = seckill_response.json()
            logger.info(f"用户{self.user_id}秒杀响应：{seckill_result.get('status')}，trade_no={seckill_result.get('trade_no', '无')}")

            # 步骤3：校验秒杀结果
            if seckill_result.get("status") == "success":
                check_url = f"/seckill/check/{seckill_result['trade_no']}/"
                check_response = self.client.get(check_url, headers=headers, timeout=3)
                check_result = check_response.json()
                if not check_result.get("stock_consistent", False):
                    logger.error(f"用户{self.user_id}超卖风险！trade_no={seckill_result['trade_no']}")
                else:
                    logger.info(f"用户{self.user_id}秒杀校验通过：{seckill_result['trade_no']}")

            # 核心改4：无论秒杀成功/失败，标记为已发请求（仅1次）
            self.has_seckilled = True

        except Exception as e:
            logger.error(f"用户{self.user_id}秒杀异常：{str(e)}")
            self.has_seckilled = True  # 即使异常，也标记为已执行
            pass