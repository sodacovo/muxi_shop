from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django_redis import get_redis_connection
import time
import logging

from order.models import Order, OrderGoods, EventLog, LocalTransactionRecord
from goods.models import Goods
from user.models import User
from order.tasks import process_seckill, send_seckill_event, consume_stock_event

logger = logging.getLogger(__name__)

class OrderService:
    @staticmethod
    def create_seckill_order(user_id, goods_id, qty=1):
        """
        创建秒杀订单（双模式自动切换，订单创建交给process_seckill核心任务）
        :param user_id: 用户ID
        :param goods_id: 秒杀商品ID
        :param qty: 购买数量（默认1件）
        :return: 订单结果字典
        """
        try:
            # 1. 基础校验：用户与商品合法性
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                logger.error(f"创建秒杀订单失败：用户ID={user_id}不存在")
                return {
                    "status": "fail",
                    "reason": f"用户ID={user_id}不存在",
                    "code": 8001
                }

            try:
                goods = Goods.objects.get(id=goods_id, is_seckill=True)
            except Goods.DoesNotExist:
                logger.error(f"创建秒杀订单失败：商品ID={goods_id}非秒杀商品或不存在")
                return {
                    "status": "fail",
                    "reason": f"商品ID={goods_id}非秒杀商品或不存在",
                    "code": 8001
                }

            # 2. 提前判重（拦截重复请求，避免触发核心任务）
            redis_conn = get_redis_connection("seckill")
            repeat_key = f"seckill:user:{user.email}:product:{goods_id}"
            if redis_conn.get(repeat_key):
                logger.warning(f"用户{user.email}重复秒杀商品{goods_id}，直接返回8001")
                return {
                    "status": "fail",
                    "reason": "不可重复下单",
                    "code": 8001,
                }

            # 3. 根据Celery Broker自动切换模式（核心修复）
            if "amqp://" in settings.CELERY_BROKER_URL:
                # ---------------------- RabbitMQ模式（核心修复） ----------------------
                # 第一步：触发process_seckill核心任务（库存扣减、订单创建、邮件发送）
                task = process_seckill.delay(user_id=user_id, product_id=goods_id)
                logger.info(f"🐇 RabbitMQ模式：触发核心秒杀任务 → task_id={task.id}，user_id={user_id}，goods_id={goods_id}")

                # 第二步：等待核心任务执行（同步获取结果，测试用；生产可改为异步）
                task_result = task.get(timeout=10)  # 超时10秒

                # 第三步：核心任务成功后，再触发事件推送（可选）
                if task_result["status"] == "success":
                    trade_no = task_result["trade_no"]
                    event_data = {
                        "trade_no": trade_no,
                        "user_id": user_id,
                        "user_email": user.email,
                        "goods_id": goods_id,
                        "qty": qty,
                        "order_amount": float(task_result["order_amount"]),
                        "create_time": timezone.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    # 触发事件推送（仅记录，不影响核心逻辑）
                    send_seckill_event.delay(event_data)
                    logger.info(f"🐇 RabbitMQ模式：核心任务执行成功 → trade_no={trade_no}，事件已推送")

                return {
                    "mode": "RabbitMQ",
                    "status": task_result["status"],
                    "trade_no": task_result.get("trade_no"),
                    "message": task_result.get("message"),
                    "code": task_result.get("code"),
                    "task_id": task.id
                }

            else:
                # ---------------------- Redis模式（保留原有逻辑） ----------------------
                task = process_seckill.delay(user_id, goods_id)
                logger.info(f"🔴 Redis模式：触发核心秒杀任务 → task_id={task.id}，user_id={user_id}，goods_id={goods_id}")
                
                # 等待任务结果
                task_result = task.get(timeout=10)

                return {
                    "mode": "Redis",
                    "status": task_result["status"],
                    "trade_no": task_result.get("trade_no"),
                    "message": task_result.get("message"),
                    "code": task_result.get("code"),
                    "task_id": task.id
                }

        except Exception as e:
            logger.error(
                f"秒杀订单创建异常：user_id={user_id}, goods_id={goods_id}，错误：{str(e)}",
                exc_info=True
            )
            return {
                "status": "fail",
                "reason": f"系统繁忙，订单创建失败：{str(e)[:30]}",
                "code": 8001
            }

    @staticmethod
    def get_order_by_trade_no(trade_no):
        """根据订单号查询订单详情（保留原有逻辑）"""
        try:
            order = Order.objects.get(trade_no=trade_no, is_delete=0)
            order_goods = OrderGoods.objects.filter(trade_no=trade_no).first()
            goods = Goods.objects.get(id=order_goods.sku_id) if (order_goods and order_goods.sku_id) else None
            user = User.objects.get(email=order.email) if order.email else None

            return {
                "trade_no": order.trade_no,
                "user_info": {
                    "user_id": user.id if user else None,
                    "user_email": order.email
                },
                "order_info": {
                    "order_amount": float(order.order_amount),
                    "pay_status": order.pay_status,
                    "create_time": order.create_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "address_id": order.address_id
                },
                "goods_info": {
                    "goods_id": goods.id if goods else None,
                    "goods_name": goods.name if goods else None,
                    "seckill_price": float(goods.seckill_price) if goods else None,
                    "buy_qty": order_goods.goods_num if order_goods else 0
                }
            }
        except Exception as e:
            logger.error(f"查询订单详情失败：trade_no={trade_no}，错误：{str(e)}", exc_info=True)
            return None