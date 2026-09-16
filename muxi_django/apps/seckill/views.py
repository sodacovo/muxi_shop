from django_redis import get_redis_connection
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from celery.result import AsyncResult
# 🌟 只导入CeleryError（兼容所有版本，涵盖TaskNotFound场景）
from celery.exceptions import CeleryError

# 导入项目内依赖
from goods.models import Goods
from user.models import User
from order.tasks import process_seckill  # 保留Redis模式任务（OrderService内部会调用）
from order.services import OrderService  # 新增：导入OrderService
from utils.ResponseMessage import SeckillResponse
from utils.jwt_auth import JWTHeaderAuthentication
from django.utils.decorators import method_decorator
from utils.rate_limit import seckill_rate_limit


class SeckillSubmitView(APIView):
    """提交秒杀请求接口"""
    authentication_classes = [JWTHeaderAuthentication]
    permission_classes = [AllowAny]
    @method_decorator(seckill_rate_limit(limit=3,period=10))
    def post(self, request):
        try:
            # -------------------------- 1. JWT认证处理 --------------------------
            auth_result = request.user
            if not auth_result.get("status"):
                return SeckillResponse.failed({
                    "msg": f"认证失败：{auth_result.get('error', '未知错误')}",
                    "code": 8107
                })
            payload = auth_result.get("data", {})
            user_id = payload.get("user_id")
            if not user_id or not isinstance(user_id, int):
                return SeckillResponse.failed({
                    "msg": "Token中缺少合法的user_id",
                    "code": 8108
                })

            # -------------------------- 2. 参数校验 --------------------------
            product_id = request.data.get("product_id")
            if not product_id or not str(product_id).isdigit():
                return SeckillResponse.failed({
                    "msg": "参数错误：商品ID必须是有效数字",
                    "code": 8101
                })
            product_id = int(product_id)

            # -------------------------- 3. 业务逻辑校验（部分移到OrderService，这里保留基础校验） --------------------------
            if not User.objects.filter(id=user_id).exists():
                return SeckillResponse.failed({
                    "msg": "用户不存在",
                    "code": 8102
                })
            try:
                goods = Goods.objects.get(id=product_id, is_seckill=True)
                now = timezone.now()
                if now < goods.seckill_start_time:
                    return SeckillResponse.failed({
                        "msg": f"秒杀未开始（开始时间：{goods.seckill_start_time.strftime('%Y-%m-%d %H:%M:%S')}）",
                        "code": 8103
                    })
                if now > goods.seckill_end_time:
                    return SeckillResponse.failed({
                        "msg": "秒杀已结束",
                        "code": 8104
                    })
            except Goods.DoesNotExist:
                return SeckillResponse.failed({
                    "msg": "非秒杀商品或商品不存在",
                    "code": 8105
                })

            # -------------------------- 4. 关键修改：调用OrderService，触发模式判断 --------------------------
            # 替换原来直接调用process_seckill.delay()的逻辑
            order_result = OrderService.create_seckill_order(
                user_id=user_id,
                goods_id=product_id,
                qty=1  # 秒杀默认1件
            )

            # ✅ 核心新增：优先处理 8001（重复下单），直接返回失败响应
            if order_result["code"] == 8001:
                return SeckillResponse.failed({
                    "msg": order_result["reason"],  # 透传"不可重复下单"提示
                    "code": 8001  # 前端识别该code，立即弹窗
                })

            # 根据OrderService的返回结果处理响应（原有逻辑保留）
            if order_result["status"] == "success":
                return SeckillResponse.success({
                    "task_id": order_result["task_id"],  # RabbitMQ模式不需要返回task_id（事件异步处理）
                    "mode": order_result["mode"],  # 新增：返回当前模式，方便前端调试
                    "msg": order_result["message"],
                    "trade_no": order_result["trade_no"],  # 返回订单号，便于查询
                    "expire_seconds": 60,
                    "code": order_result["code"]
                })
            else:
                return SeckillResponse.failed({
                    "msg": order_result["reason"],
                    "code": order_result["code"]
                })

        except Exception as e:
            return SeckillResponse.failed({
                "msg": f"提交秒杀失败：{str(e)[:30]}",
                "code": 8106
            })


class SeckillResultView(APIView):
    """查询秒杀结果接口"""
    # 以下代码不变（保持原样）
    authentication_classes = [JWTHeaderAuthentication]
    permission_classes = [AllowAny]
    @method_decorator(seckill_rate_limit(limit=2,period=5))
    def get(self, request):
        try:
            # 1. 认证校验
            auth_result = request.user
            if not auth_result.get("status"):
                return SeckillResponse.failed({
                    "msg": f"认证失败：{auth_result.get('error', '未知错误')}",
                    "code": 8207
                })

            # 2. 参数校验
            task_id = request.query_params.get("task_id")
            if not task_id or not isinstance(task_id, str):
                return SeckillResponse.failed({
                    "msg": "参数错误：缺少有效的task_id",
                    "code": 8201
                })
            from order.models import Order  # 导入订单模型（确保路径正确）
            try:
                # 加事务：确保读取最新订单状态，避免并发问题
                from django.db import transaction
                with transaction.atomic():
                    # 根据 task_id 查询订单（假设订单表有 task_id 字段关联）
                    order = Order.objects.select_for_update().get(task_id=task_id)
                
                # 订单存在，直接返回成功（秒杀已完成）
                return SeckillResponse.success({
                    "status": "success",
                    "trade_no": order.trade_no,
                    "order_amount": float(order.total_amount),  # 按订单表字段调整
                    "msg": "秒杀成功，可前往支付",
                    "code": 8201
                })
            except Order.DoesNotExist:
                # 订单未找到，再查 Celery 任务状态（降级逻辑）
                pass

            # 3. 查询任务状态
            task_result = AsyncResult(task_id)

            # 4. 处理不同状态
            if task_result.state == "PENDING":
                return SeckillResponse.other({
                    "status": "pending",
                    "msg": "秒杀处理中，请稍后...",
                    "code": 8200
                })
            elif task_result.state == "SUCCESS":
                task_data = task_result.result
                if task_data.get("status") == "success":
                    return SeckillResponse.success({
                        "status": "success",
                        "trade_no": task_data.get("trade_no"),
                        "order_amount": task_data.get("order_amount", 0),
                        "msg": task_data.get("message", "秒杀成功，可前往支付"),
                        "code": 8201
                    })
                else:
                    return SeckillResponse.failed({
                        "msg": task_data.get("reason", "秒杀失败"),
                        "code": task_data.get("code", 8202)
                    })
            elif task_result.state in ["FAILURE", "REVOKED"]:
                error_msg = str(task_result.result)[:50] if task_result.result else "未知系统异常"
                return SeckillResponse.failed({
                    "msg": f"秒杀失败：系统异常（{error_msg}）",
                    "code": 8203
                })
            else:
                return SeckillResponse.failed({
                    "msg": f"秒杀状态异常（状态：{task_result.state}）",
                    "code": 8204
                })

        except Exception as e:
            return SeckillResponse.failed({
                "msg": f"查询秒杀结果失败：{str(e)[:30]}",
                "code": 8205
            })


class SeckillStockView(APIView):
    """实时刷新库存接口"""
    # 以下代码不变（保持原样）
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        try:
            product_ids_str = request.query_params.get("product_ids")
            if not product_ids_str:
                return SeckillResponse.failed({
                    "msg": "参数错误：缺少product_ids（格式：product_ids=1,2,3）",
                    "code": 8301
                })

            product_id_list = []
            for pid in product_ids_str.split(","):
                pid = pid.strip()
                if pid.isdigit():
                    product_id_list.append(int(pid))
            if not product_id_list:
                return SeckillResponse.failed({
                    "msg": "参数错误：product_ids格式无效（需为数字列表，如1,2,3）",
                    "code": 8302
                })

            redis_conn = get_redis_connection("seckill")
            stock_result = []
            for product_id in product_id_list:
                stock_key = f"seckill:stock:{product_id}"
                current_stock = redis_conn.get(stock_key)
                current_stock = int(current_stock) if current_stock else 0

                try:
                    goods = Goods.objects.get(id=product_id, is_seckill=True)
                    now = timezone.now()
                    stock_result.append({
                        "product_id": product_id,
                        "product_name": goods.name,
                        "seckill_price": float(goods.seckill_price),
                        "current_stock": current_stock,
                        "is_valid": now >= goods.seckill_start_time and now <= goods.seckill_end_time,
                        "start_time": goods.seckill_start_time.strftime("%Y-%m-%d %H:%M:%S"),
                        "end_time": goods.seckill_end_time.strftime("%Y-%m-%d %H:%M:%S")
                    })
                except Goods.DoesNotExist:
                    stock_result.append({
                        "product_id": product_id,
                        "product_name": "未知商品",
                        "seckill_price": 0.0,
                        "current_stock": 0,
                        "is_valid": False,
                        "start_time": "",
                        "end_time": ""
                    })

            return SeckillResponse.success({
                "stock_list": stock_result,
                "total_count": len(stock_result),
                "update_time": timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
                "code": 8300
            })

        except Exception as e:
            return SeckillResponse.failed({
                "msg": f"刷新库存失败：{str(e)[:30]}",
                "code": 8303
            })