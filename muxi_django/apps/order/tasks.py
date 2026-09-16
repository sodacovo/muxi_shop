import smtplib
import ssl
from email.mime.text import MIMEText
import time
import re
import logging
from utils.logging import TaskContext
from datetime import timedelta
from django.core.mail import send_mail
from django.db import transaction, connection, close_old_connections
from django.utils import timezone
from django_redis import get_redis_connection
from celery import shared_task, current_task, current_app
import json
import redis
from asgiref.sync import sync_to_async
# 导入项目模型和配置
from goods.models import Goods
from order.models import Order, OrderGoods, EventLog
from user.models import User
from django.conf import settings
from utils.email import send_seckill_success_email
from pay.alipay import AliPay
from prometheus_client import Gauge, CollectorRegistry
from django.db.utils import IntegrityError
from utils.redis_lock import acquire_redis_lock, release_redis_lock, lock_renewal
# 导入RabbitMQ队列配置所需模块
from kombu import Exchange, Queue

# 初始化日志
logger = logging.getLogger(__name__)

# 尝试导入SeckillResponse
try:
    from utils.ResponseMessage import SeckillResponse
except ImportError:
    logger.warning("未导入SeckillResponse，若需使用请检查路径")

# Prometheus监控指标
metrics_registry = CollectorRegistry()
celery_queue_length_gauge = Gauge(
    'celery_queue_length',
    'Current length of Celery task queues',
    ['queue_name'],
    registry=metrics_registry
)


# ------------------------------ 工具函数 ------------------------------
def get_seckill_redis():
    """获取秒杀专用Redis连接"""
    return get_redis_connection('seckill')


def generate_trade_no():
    """生成唯一订单号"""
    return str(int(time.time() * 1000))


def is_valid_email(email):
    """验证邮箱格式"""
    if not email:
        return False
    email_pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(email_pattern, email) is not None


# ------------------------------ Redis模式核心任务 ------------------------------
@shared_task(bind=True, max_retries=2)
def send_seckill_email_async(self, to_email, goods_name, trade_no, price, pay_url):
    task_id = self.request.id
    logger = logging.getLogger('celery.worker')
    logger.info(f"【邮件任务启动】task_id={task_id}，trade_no={trade_no}，收件人={to_email}，商品名={goods_name}")
    try:
        result = send_seckill_success_email(
            to_email=to_email,
            goods_name=goods_name,
            trade_no=trade_no,
            price=price,
            pay_url=pay_url
        )
        if result:
            logger.info(f"【邮件任务】成功 → task_id={task_id}，trade_no={trade_no}，收件人={to_email}")
        else:
            logger.error(f"【邮件任务】失败 → task_id={task_id}，trade_no={trade_no}，收件人={to_email}（发送返回False）")
        return result
    except Exception as e:
        current_retry = self.request.retries + 1
        remaining_retry = self.max_retries - self.request.retries
        logger.error(
            f"【邮件任务】异常 → task_id={task_id}，trade_no={trade_no}，收件人={to_email}，错误={str(e)[:50]}，第{current_retry}次重试，剩余{remaining_retry}次",
            exc_info=True
        )
        self.retry(exc=e, countdown=3)

@shared_task(bind=True, max_retries=2)
def process_seckill(self, user_id, product_id):
    """核心秒杀任务（整合Redis分布式锁防死锁+RabbitMQ事件触发）"""
    # 🌟 统一日志器（必须放在最前面）
    logger = logging.getLogger('celery.worker')
    task_id = self.request.id or getattr(current_task, 'request', {}).get('id')
    logger.info(f"【秒杀任务启动】task_id={task_id}，user_id={user_id}，product_id={product_id}，模式={'RabbitMQ' if 'amqp' in settings.CELERY_BROKER_URL else 'Redis'}")

    # 内部方法：WebSocket推送结果（定义在调用前）
    def push_seckill_result(result):
        try:
            if not task_id:
                logger.error("[WebSocket推送] task_id为空，无法推送")
                return
            
            # 🌟 核心：根据配置开关选择推送方式
            if settings.USE_TORNADO_WS:
                # Tornado 模式：发布消息到 Redis 频道（开发环境Redis配置）
                redis_config = settings.TORNADO_WS_CONFIG["redis"]
                redis_conn = redis.Redis(
                    host=redis_config["host"],
                    port=redis_config["port"],
                    db=redis_config["db"],
                    decode_responses=redis_config["decode_responses"]
                )
                redis_channel = settings.TORNADO_WS_CONFIG["redis_channels"]["seckill_result"]
                # 补充 task_id 到消息中（Tornado 按 task_id 推送）
                result["task_id"] = task_id
                redis_conn.publish(redis_channel, json.dumps(result))
                logger.info(f"[Redis发布] 秒杀结果已发布到频道 {redis_channel} → task_id={task_id}，result_status={result.get('status')}")
            else:
                # Django Channels 模式：原有逻辑保留
                group_name = f'seckill_{task_id}'
                logger.info(f"[WebSocket推送] 准备推送 → group={group_name}，result_status={result.get('status')}，trade_no={result.get('trade_no', '无')}")
                
                from channels.layers import get_channel_layer
                from asgiref.sync import async_to_sync
                channel_layer = get_channel_layer()
                time.sleep(0.1)
                
                if not channel_layer:
                    logger.error("[WebSocket推送] 获取channel_layer失败")
                    return
                
                async_to_sync(channel_layer.group_send)(
                    group_name,
                    {'type': 'seckill_result', 'result': result}
                )
                logger.info(f"[WebSocket推送] 推送成功 → group={group_name}")
        except Exception as e:
            logger.error(f"[推送失败] task_id={task_id}，错误={str(e)}", exc_info=True)

    # 初始化变量
    redis_conn = get_seckill_redis()
    stock_key = f"seckill:stock:{product_id}"
    repeat_key = None
    user_email = None
    processed_key = f"seckill:task:processed:{task_id}"

    # 1. 幂等性校验日志（补充）
    if redis_conn.get(processed_key):
        logger.warning(f"【秒杀幂等校验】任务已处理，跳过重复执行 → task_id={task_id}，user_id={user_id}")
        # 🌟 补充：推送重复执行结果给前端
        push_seckill_result({'status': 'fail', 'reason': '任务已处理，请勿重复提交', 'code': 8001})
        return {'status': 'fail', 'reason': '任务已处理', 'code': 8001}
    
    # 新增：锁相关变量
    lock_key = f"seckill:lock:goods:{product_id}"
    lock_acquired = False
    renewal_thread = None  # 锁续约线程

    try:
        # 2. 校验用户（补充日志）
        try:
            user = User.objects.get(id=user_id)
            user_email = user.email
            if not is_valid_email(user_email):
                logger.warning(f"【用户校验】邮箱格式无效 → user_id={user_id}，email={user_email}")
                push_seckill_result({'status': 'fail', 'reason': '邮箱格式无效', 'code': 8001})
                return {'status': 'fail', 'reason': '邮箱格式无效', 'code': 8001}
            logger.info(f"【用户校验】通过 → user_id={user_id}，email={user_email}")
        except User.DoesNotExist:
            logger.error(f"【用户校验】失败 → user_id={user_id} 不存在")
            push_seckill_result({'status': 'fail', 'reason': '用户不存在', 'code': 8001})
            return {'status': 'fail', 'reason': '用户不存在', 'code': 8001}

        # 3. 校验商品（补充日志）
        try:
            goods = Goods.objects.get(id=product_id, is_seckill=True)
            logger.info(f"【商品校验】通过 → product_id={product_id}，商品名={goods.name}，秒杀库存={goods.seckill_stock}，开始时间={goods.seckill_start_time}，结束时间={goods.seckill_end_time}")
        except Goods.DoesNotExist:
            logger.error(f"【商品校验】失败 → product_id={product_id} 非秒杀商品或不存在")
            push_seckill_result({'status': 'fail', 'reason': '非秒杀商品或不存在', 'code': 8001})
            return {'status': 'fail', 'reason': '非秒杀商品或不存在', 'code': 8001}

        # 4. 校验秒杀时间（补充日志）
        now = timezone.now()
        if now < goods.seckill_start_time:
            start_time_str = goods.seckill_start_time.strftime("%Y-%m-%d %H:%M:%S")
            logger.warning(f"【时间校验】失败 → 秒杀未开始，当前时间={now.strftime('%Y-%m-%d %H:%M:%S')}，开始时间={start_time_str}，product_id={product_id}")
            push_seckill_result({'status': 'fail', 'reason': f'秒杀未开始({start_time_str})', 'code': 8002})
            return {'status': 'fail', 'reason': f'秒杀未开始({start_time_str})', 'code': 8002}
        if now > goods.seckill_end_time:
            end_time_str = goods.seckill_end_time.strftime("%Y-%m-%d %H:%M:%S")
            logger.warning(f"【时间校验】失败 → 秒杀已结束，当前时间={now.strftime('%Y-%m-%d %H:%M:%S')}，结束时间={end_time_str}，product_id={product_id}")
            push_seckill_result({'status': 'fail', 'reason': '秒杀已结束', 'code': 8002})
            return {'status': 'fail', 'reason': '秒杀已结束', 'code': 8002}
        logger.info(f"【时间校验】通过 → 当前时间={now.strftime('%Y-%m-%d %H:%M:%S')}，秒杀有效期内")

        # 5. 防重复秒杀（补充日志）
        repeat_key = f"seckill:user:{user_email}:product:{product_id}"
        if redis_conn.get(repeat_key):
            logger.warning(f"【重复校验】失败 → 用户{user_email}已秒杀过商品{product_id}")
            push_seckill_result({'status': 'fail', 'reason': '不可重复下单', 'code': 8001})
            return {'status': 'fail', 'reason': '不可重复下单', 'code': 8001}
        logger.info(f"【重复校验】通过 → 用户{user_email}未秒杀过商品{product_id}")
        
        # 🌟 Redis分布式锁：原子获取锁（带自动过期，防死锁基础）
        lock_acquired = acquire_redis_lock(redis_conn, lock_key, task_id, expire=10)
        if not lock_acquired:
            logger.warning(f"【锁竞争】失败 → task_id={task_id}，product_id={product_id}，当前抢购人数过多")
            push_seckill_result({'status': 'fail', 'reason': '当前抢购人数过多，请稍后再试', 'code': 8001})
            return {'status': 'fail', 'reason': '当前抢购人数过多，请稍后再试', 'code': 8001}
        logger.info(f"【锁竞争】成功 → task_id={task_id}，product_id={product_id}，获取分布式锁")

        # 🌟 Redis分布式锁：启动后台续约（进阶防死锁，避免任务耗时超锁过期时间）
        renewal_thread = lock_renewal(redis_conn, lock_key, task_id, expire=10, interval=3)
        logger.info(f"【锁续约】启动 → task_id={task_id}，product_id={product_id}，续约间隔3秒，过期时间10秒")

        # 6. 扣减Redis库存（补充日志）
        current_stock = redis_conn.decr(stock_key)
        logger.info(f"【库存扣减】Redis库存扣减后 → product_id={product_id}，当前库存={current_stock}")
        if current_stock < 0:
            redis_conn.incr(stock_key)  # 回滚
            logger.error(f"【库存扣减】失败 → 商品已抢完，product_id={product_id}，回滚后库存={current_stock + 1}")
            push_seckill_result({'status': 'fail', 'reason': '商品已抢完', 'code': 8001})
            return {'status': 'fail', 'reason': '商品已抢完', 'code': 8001}

        # 7. 同步数据库库存（补充日志）
        update_db_stock.delay(product_id, current_stock)
        logger.info(f"【库存同步】已提交数据库同步任务 → product_id={product_id}，目标库存={current_stock}")

        # 8. 创建订单（补充详细日志）
        with transaction.atomic():
            trade_no = generate_trade_no()
            order = Order.objects.create(
                email=user_email,
                trade_no=trade_no,
                order_amount=goods.seckill_price,
                address_id=None,
                pay_status="0",
                create_time=now,
                update_time=now,
                is_delete=0
            )
            OrderGoods.objects.create(
                trade_no=trade_no,
                sku_id=goods.id,
                goods_num=1
            )
            redis_conn.setex(repeat_key, 86400, 1)  # 标记已秒杀
            redis_conn.setex(processed_key, 3600, 1)  # 标记任务已处理
            logger.info(f"【订单创建】成功 → trade_no={trade_no}，user_email={user_email}，商品名={goods.name}，订单金额={goods.seckill_price}，支付状态=待支付")

        # 9. 发送邮件（补充日志）
        pay_url = f"https://www.nwq1309.shop/Order/Pay?tradeNo={trade_no}&orderAmount={float(goods.seckill_price)}&payType=alipay"
        email_task = send_seckill_email_async.delay(
            to_email='2350496649@qq.com',
            goods_name=goods.name,
            trade_no=trade_no,
            price=goods.seckill_price,
            pay_url=pay_url
        )
        logger.info(f"【邮件任务】已提交 → trade_no={trade_no}，收件人=2350496649@qq.com，邮件任务ID={email_task.id}")

        # 🌟 RabbitMQ模式：订单创建成功后，触发事件发送（兼容Redis模式）
        if "amqp://" in settings.CELERY_BROKER_URL:
            event_data = {
                "trade_no": trade_no,
                "goods_id": product_id,
                "user_email": user_email,
                "order_amount": float(goods.seckill_price),
                "create_time": now.strftime("%Y-%m-%d %H:%M:%S")
            }
            rabbitmq_task = send_seckill_event.delay(event_data)
            logger.info(f"【RabbitMQ事件】已提交 → trade_no={trade_no}，事件任务ID={rabbitmq_task.id}")

        # 10. 成功结果（补充日志）
        success_result = {
            'status': 'success',
            'trade_no': trade_no,
            'order_amount': float(goods.seckill_price),
            'message': '秒杀成功！请在15分钟内支付',
            'code': 8000
        }
        push_seckill_result(success_result)
        logger.info(f"【秒杀任务】完成 → task_id={task_id}，trade_no={trade_no}，状态=成功，模式={'RabbitMQ' if 'amqp' in settings.CELERY_BROKER_URL else 'Redis'}")
        return success_result

    except Exception as task_err:
        # 异常处理（修正推送参数错误+补充日志）
        close_old_connections()
        err_msg = str(task_err)[:50]  # 截取前50字避免日志过长
        
        # 回滚库存（补充日志）
        if stock_key and redis_conn:
            redis_conn.incr(stock_key)
            logger.error(f"【异常回滚】库存回滚 → product_id={product_id}，错误={err_msg}")
        
        # 清除重复标记（补充日志）
        if repeat_key and redis_conn:
            redis_conn.delete(repeat_key)
            logger.error(f"【异常清理】重复标记清除 → user_email={user_email or '未知'}，product_id={product_id}")
        
        # 清除任务已处理标记（补充日志）
        if processed_key and redis_conn:
            redis_conn.delete(processed_key)
            logger.error(f"【异常清理】任务处理标记清除 → task_id={task_id}")
        
        # 记录异常日志（强化）
        logger.error(
            f"【秒杀任务】异常 → task_id={task_id}，user_id={user_id}，product_id={product_id}，错误={err_msg}",
            exc_info=True  # 保留堆栈信息
        )
        
        # 推送失败结果（修正：之前传了2个参数，函数只接收1个）
        fail_result = {
            'status': 'fail',
            'reason': f'系统繁忙，请稍后再试（{err_msg}）',
            'code': 8001
        }
        push_seckill_result(fail_result)
        
        # 重试日志（补充）
        current_retry = self.request.retries + 1
        logger.warning(f"【秒杀任务】重试 → task_id={task_id}，第{current_retry}次重试，倒计时3秒")
        self.retry(exc=task_err, countdown=3)
        
        return fail_result
    # 🌟 Redis分布式锁：finally块强制释放锁（防死锁核心，无论正常/异常都释放）
    finally:
        # 停止锁续约线程（若已启动）
        if renewal_thread and renewal_thread.is_alive():
            logger.info(f"【锁续约】停止 → task_id={task_id}，product_id={product_id}")
        # 仅当获取锁成功时，才释放锁（避免误删其他任务的锁）
        if lock_acquired and redis_conn:
            release_success = release_redis_lock(redis_conn, lock_key, task_id)
            if release_success:
                logger.info(f"【锁释放】成功 → task_id={task_id}，product_id={product_id}")
            else:
                logger.warning(f"【锁释放】失败 → task_id={task_id}，product_id={product_id}，锁已过期或非当前任务持有（正常场景）")


@shared_task
def cancel_unpaid_orders():
    logger = logging.getLogger('celery.worker')
    task_id = current_task.request.id
    logger.info(f"【取消超时订单任务启动】task_id={task_id}，当前时间={timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    close_old_connections()
    redis_conn = get_seckill_redis()
    now = timezone.now()
    fifteen_min_ago = now - timedelta(minutes=15)
    cancel_count = 0

    # 1. 筛选超时订单（补充日志）
    seckill_prices = [float(g.seckill_price) for g in Goods.objects.filter(is_seckill=True)]
    logger.info(f"【取消超时订单】筛选条件 → 支付状态=待支付，未删除，创建时间<{fifteen_min_ago.strftime('%Y-%m-%d %H:%M:%S')}，秒杀价格列表={seckill_prices}")
    
    unpaid_orders = Order.objects.filter(
        pay_status="0",
        is_delete=0,
        create_time__lt=fifteen_min_ago,
        order_amount__in=seckill_prices
    )
    logger.info(f"【取消超时订单】待取消订单总数={unpaid_orders.count()}")

    # 批量获取OrderGoods（补充日志）
    trade_no_list = unpaid_orders.values_list('trade_no', flat=True)
    goods_map = {og.trade_no: og for og in OrderGoods.objects.filter(trade_no__in=trade_no_list)}
    logger.info(f"【取消超时订单】关联商品数={len(goods_map)}（匹配订单数={len(trade_no_list)}）")
    
    for order in unpaid_orders:
        with transaction.atomic():
            # 补充单个订单取消日志
            logger.info(f"【取消超时订单】处理中 → trade_no={order.trade_no}，user_email={order.email}，创建时间={order.create_time.strftime('%Y-%m-%d %H:%M:%S')}，订单金额={order.order_amount}")
            
            order.pay_status = "4"
            order.is_delete = 1
            order.update_time = now
            order.save()
            cancel_count += 1

            order_goods = goods_map.get(order.trade_no)
            if not order_goods:
                logger.warning(f"【取消超时订单】无商品关联 → trade_no={order.trade_no}，跳过库存回滚")
                continue

            goods_id = order_goods.sku_id
            redis_stock_key = f"seckill:stock:{goods_id}"
            redis_old_stock = int(redis_conn.get(redis_stock_key) or 0)
            redis_new_stock = redis_conn.incr(redis_stock_key)
            repeat_key = f"seckill:user:{order.email}:product:{goods_id}"
            redis_conn.delete(repeat_key)

            try:
                goods = Goods.objects.get(id=goods_id, is_seckill=True)
                goods.seckill_stock = redis_new_stock
                goods.save()
                logger.info(f"【取消超时订单】成功 → trade_no={order.trade_no}，商品ID={goods_id}，Redis库存={redis_old_stock}→{redis_new_stock}，数据库库存同步完成")
            except Goods.DoesNotExist:
                logger.error(f"【取消超时订单】库存回滚失败 → trade_no={order.trade_no}，商品ID={goods_id} 不存在")

    logger.info(f"【取消超时订单任务】完成 → task_id={task_id}，共取消{cancel_count}个超时订单")
    return f"已取消{cancel_count}个超时订单"

@shared_task
def update_db_stock(product_id, seckill_stock):
    logger = logging.getLogger('celery.worker')
    task_id = current_task.request.id
    logger.info(f"【库存同步任务启动】task_id={task_id}，product_id={product_id}，目标库存={seckill_stock}")
    close_old_connections()
    try:
        # 修正：sync_to_async 用于异步函数，同步任务直接调用（无需包装）
        goods = Goods.objects.get(id=product_id, is_seckill=True)
        old_stock = goods.seckill_stock
        goods.seckill_stock = seckill_stock
        goods.save()
        
        logger.info(f"【库存同步任务】成功 → product_id={product_id}，商品名={goods.name}，原库存={old_stock}→新库存={seckill_stock}")
    except Goods.DoesNotExist:
        logger.error(f"【库存同步任务】失败 → product_id={product_id} 不存在或非秒杀商品")
    except Exception as db_err:
        logger.error(
            f"【库存同步任务】异常 → task_id={task_id}，product_id={product_id}，错误={str(db_err)[:50]}",
            exc_info=True
        )


@shared_task
def check_stock_consistency():
    logger = logging.getLogger('celery.worker')
    task_id = current_task.request.id
    logger.info(f"【库存一致性校验任务启动】task_id={task_id}，当前时间={timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    close_old_connections()
    redis_conn = get_seckill_redis()
    active_goods = Goods.objects.filter(
        is_seckill=True,
        seckill_end_time__gt=timezone.now()
    )
    fix_count = 0

    logger.info(f"【库存一致性校验】待校验秒杀商品数={len(active_goods)}（秒杀未结束）")
    for goods in active_goods:
        redis_key = f"seckill:stock:{goods.id}"
        redis_stock = int(redis_conn.get(redis_key) or 0)
        db_stock = goods.seckill_stock

        # 补充单个商品校验日志
        logger.info(f"【库存一致性校验】商品={goods.name}（ID={goods.id}）→ Redis库存={redis_stock}，数据库库存={db_stock}")
        if redis_stock != db_stock:
            goods.seckill_stock = redis_stock
            goods.save()
            fix_count += 1
            logger.warning(f"【库存一致性校验】修复差异 → 商品ID={goods.id}，Redis库存={redis_stock}→数据库库存={redis_stock}（原数据库库存={db_stock}）")

    # 补充无差异日志
    if fix_count == 0:
        logger.info(f"【库存一致性校验任务】完成 → task_id={task_id}，检查{len(active_goods)}个商品，无库存差异")
    else:
        logger.info(f"【库存一致性校验任务】完成 → task_id={task_id}，检查{len(active_goods)}个商品，修复{fix_count}个差异")
    return f"检查{len(active_goods)}个商品，修复{fix_count}个差异"


@shared_task
def sync_db_to_redis(product_id):
    """同步数据库库存到Redis"""
    try:
        goods = Goods.objects.get(id=product_id, is_seckill=True)
        db_stock = goods.seckill_stock
        redis_conn = get_seckill_redis()
        redis_key = f"seckill:stock:{product_id}"
        redis_conn.set(redis_key, db_stock)
        redis_stock = int(redis_conn.get(redis_key) or 0)

        logger.info(f"商品{product_id}库存同步：DB={db_stock}→Redis={redis_stock}")
        return {
            "status": "success",
            "msg": f"商品【{goods.name}】库存同步成功",
            "data": {"product_id": product_id, "db_stock": db_stock, "redis_stock": redis_stock}
        }
    except Goods.DoesNotExist:
        logger.error(f"商品{product_id}不存在或非秒杀商品")
        return {"status": "fail", "msg": "商品不存在或非秒杀商品", "data": {}}
    except Exception as e:
        logger.error(f"同步异常：{str(e)}", exc_info=True)
        return {"status": "fail", "msg": f"同步异常：{str(e)[:30]}", "data": {}}


@shared_task
def update_celery_queue_metrics():
    """更新Celery队列长度到Prometheus"""
    close_old_connections()
    try:
        celery_inspect = current_app.control.inspect()
        queue_info = celery_inspect.active_queues()

        if not queue_info:
            logger.warning("未获取到Celery队列信息")
            return "未获取到队列信息"

        for worker, queues in queue_info.items():
            for queue in queues:
                queue_name = queue.get('name', 'unknown')
                queue_count = queue.get('count', 0)
                celery_queue_length_gauge.labels(queue_name=queue_name).set(queue_count)
                logger.info(f"队列{queue_name}长度：{queue_count}")

        return "队列指标更新成功"
    except Exception as e:
        logger.error(f"队列指标更新失败：{str(e)}", exc_info=True)
        return f"更新失败：{str(e)}"


# ---------------------- RabbitMQ模式任务（完善消息可靠性） ----------------------
@shared_task(bind=True, max_retries=3, acks_late=True)
def send_seckill_event(self, event_data):
    """发送订单事件到RabbitMQ队列（完善生产者确认，确保消息不丢失）"""
    task_id = self.request.id
    logger = logging.getLogger('celery.worker')
    logger.info(f"【RabbitMQ事件发送任务启动】task_id={task_id}，event_data={json.dumps(event_data)[:100]}（截取前100字）")
    
    if "amqp://" not in settings.CELERY_BROKER_URL:
        logger.warning(f"【RabbitMQ事件发送】非RabbitMQ模式，跳过 → task_id={task_id}")
        return "❌ 非RabbitMQ模式，跳过"

    trade_no = event_data.get("trade_no", "unknown")
    event_id = f"{trade_no}_OrderCreated"

    with TaskContext(trade_no=trade_no, task_type="seckill_event"):
        try:
            # 原有事件入库逻辑（无需修改）
            event, created = EventLog.objects.get_or_create(
                event_id=event_id,
                defaults={
                    "event_type": 'SeckillOrderCreated',
                    "event_data": event_data,
                    "status": 'sent',
                    "retry_count": 0
                }
            )
            
            if not created:
                if event.status != 'sent':
                    event.status = 'sent'
                    event.save()
                    logger.info(f"【RabbitMQ事件发送】事件已存在，更新状态 → event_id={event_id}")
                else:
                    logger.info(f"【RabbitMQ事件发送】事件已存在，无需重复发送 → event_id={event_id}")
                return f"✅ 事件{event_id}已存在"

            # 生产者确认：捕获发布异常（Celery已开启confirm_publish，补充业务日志）
            try:
                # 触发库存消费任务（消息发送到RabbitMQ）
                consume_task = consume_stock_event.delay(event_data)
                logger.info(f"【RabbitMQ事件发送】成功 → event_id={event_id}，trade_no={trade_no}，库存消费任务ID={consume_task.id}")
                # 更新事件状态为“成功”
                event.status = 'success'
                event.save()
                return f"✅ 事件{event_id}处理完成"
            except Exception as publish_err:
                # 消息发布失败，更新事件状态并重试
                event.status = 'failed'
                event.retry_count += 1
                event.save()
                logger.error(f"【RabbitMQ事件发送】发布失败 → event_id={event_id}，错误={str(publish_err)[:50]}")
                raise self.retry(exc=publish_err, countdown=5)

        except IntegrityError as e:
            if "Duplicate entry" in str(e) and event_id in str(e):
                logger.info(f"【RabbitMQ事件发送】事件重复，视为成功 → event_id={event_id}")
                return f"✅ 事件{event_id}已发送"
            else:
                logger.error(f"【RabbitMQ事件发送】异常（非重复）→ task_id={task_id}，event_id={event_id}，错误={str(e)}", exc_info=True)
                raise self.retry(exc=e, countdown=5)
        
        except Exception as e:
            # 记录事件失败状态
            event = EventLog.objects.get_or_create(event_id=event_id)[0]
            event.status = 'failed'
            event.retry_count += 1
            event.save()
            logger.error(f"【RabbitMQ事件发送】异常 → task_id={task_id}，event_id={event_id}，错误={str(e)}", exc_info=True)
            raise self.retry(exc=e, countdown=5)


@shared_task(bind=True, acks_late=True, retry_kwargs={"max_retries": 3, "countdown": 5})
def send_compensate_event(self, event_data):
    task_id = self.request.id
    logger = logging.getLogger('celery.worker')
    logger.info(f"【库存补偿任务启动】task_id={task_id}，event_data={json.dumps(event_data)[:100]}（截取前100字）")
    
    trade_no = event_data.get("trade_no", "unknown")
    goods_id = event_data.get("goods_id")
    qty = event_data.get("qty", 1)
    event_id = f"{trade_no}_CompensateStock"

    with TaskContext(trade_no=trade_no, task_type="compensate_event"):
        try:
            with transaction.atomic():
                event, created = EventLog.objects.get_or_create(
                    event_id=event_id,
                    defaults={"event_type": "CompensateStock", "event_data": event_data, "status": "pending", "retry_count": 0}
                )
                if event.status == "success":
                    logger.info(f"【库存补偿任务】已执行成功，跳过 → event_id={event_id}，trade_no={trade_no}，goods_id={goods_id}")
                    return f"✅ 补偿事件{event_id}已执行"

                # 库存回滚（补充前后库存日志）
                redis_conn = get_seckill_redis()
                stock_key = f"seckill:stock:{goods_id}"
                before_stock = int(redis_conn.get(stock_key) or 0)
                redis_conn.incrby(stock_key, qty)
                after_stock = int(redis_conn.get(stock_key) or 0)
                logger.info(f"【库存补偿任务】库存回滚 → goods_id={goods_id}，回滚数量={qty}，回滚前={before_stock}→回滚后={after_stock}")

                # 更新状态（补充日志）
                event.status = "success"
                event.save()
                logger.info(f"【库存补偿任务】成功 → event_id={event_id}，trade_no={trade_no}，goods_id={goods_id}")
                return f"✅ 补偿事件{event_id}执行成功"

        except Exception as e:
            event = EventLog.objects.get_or_create(event_id=event_id)[0]
            event.retry_count += 1
            event.status = "pending"
            event.save()

            if event.retry_count >= self.max_retries:
                event.status = "fail"
                event.save()
                logger.error(f"【库存补偿任务】失败 → 重试3次耗尽，event_id={event_id}，trade_no={trade_no}，goods_id={goods_id}", exc_info=True)
                return f"❌ 补偿事件{event_id}重试失败"

            logger.warning(f"【库存补偿任务】重试 → 第{event.retry_count}次，event_id={event_id}，错误={str(e)[:50]}")
            raise self.retry(exc=e, countdown=5)


@shared_task(bind=True, acks_late=True, max_retries=3, retry_kwargs={"countdown": 20})
def consume_stock_event(self, event_data):
    """消费库存事件（完善消费者手动ACK+死信兜底）"""
    task_id = self.request.id
    logger = logging.getLogger('celery.worker')
    logger.info(f"【库存消费任务启动】task_id={task_id}，event_data={json.dumps(event_data)[:100]}（截取前100字）")
    
    trade_no = event_data.get("trade_no", "unknown")
    goods_id = event_data.get("goods_id")
    compensate_event_id = f"{trade_no}_CompensateStock"

    # 幂等检查（原有代码，无需修改）
    if EventLog.objects.filter(event_id=compensate_event_id, status="success").exists():
        logger.info(f"【库存消费任务】已补偿，跳过 → trade_no={trade_no}，goods_id={goods_id}，补偿事件ID={compensate_event_id}")
        return f"✅ 订单{trade_no}已补偿，无需处理"

    with TaskContext(trade_no=trade_no, task_type="stock_consume"):
        try:
            # 数据库连接检查
            if connection.connection is None or (hasattr(connection.connection, 'ping') and not connection.connection.ping()):
                connection.close()
                connection.connect()
                logger.info(f"【库存消费任务】数据库连接重置 → task_id={task_id}，trade_no={trade_no}")

            # 业务逻辑执行（成功日志）
            logger.info(f"【库存消费任务】成功 → task_id={task_id}，trade_no={trade_no}，goods_id={goods_id}")
            return f"✅ 库存消费成功：trade_no={trade_no}"

        except Exception as e:
            current_try = self.request.retries + 1
            remaining = self.max_retries - self.request.retries

            logger.error(
                f"【库存消费任务】失败 → 第{current_try}次，剩余{remaining}次，task_id={task_id}，trade_no={trade_no}，错误={str(e)[:50]}",
                exc_info=True
            )

            # 重试耗尽时：归档事件，消息自动进入死信队列
            if current_try >= self.max_retries:
                # 1. 归档失败事件（便于人工排查）
                fail_event_id = f"{trade_no}_StockConsumeFail_{task_id}"
                EventLog.objects.get_or_create(
                    event_id=fail_event_id,
                    defaults={
                        "event_type": 'StockConsumeFailed',
                        "event_data": event_data,
                        "status": 'dead',
                        "retry_count": current_try,
                        "error_msg": str(e)[:100]
                    }
                )
                # 2. 触发补偿任务
                compensate_task = send_compensate_event.delay({
                    "trade_no": trade_no,
                    "goods_id": goods_id,
                    "qty": event_data.get("qty", 1),
                    "reason": str(e)[:30]
                })
                logger.info(f"【库存消费任务】重试耗尽，触发补偿+进入死信队列 → trade_no={trade_no}，补偿任务ID={compensate_task.id}")
                # 抛出异常，让Celery不发送ACK，消息进入死信队列
                raise Exception(f"重试{current_try}次失败，进入死信队列：{str(e)[:50]}")

            # 未耗尽重试次数，继续重试
            if current_try < self.max_retries:
                raise self.retry(exc=e, countdown=20)
            else:
                logger.error(f"【库存消费任务】终止 → 重试3次失败，trade_no={trade_no}")
                return f"❌ 库存消费失败：trade_no={trade_no}"

@shared_task(bind=True, acks_late=True)
def consume_dead_seckill_event(self, event_data):
    """消费秒杀死信队列消息（兜底处理，避免消息丢失）"""
    task_id = self.request.id
    logger = logging.getLogger('celery.worker')
    logger.error(f"【死信队列消费】接收失败消息 → task_id={task_id}，event_data={json.dumps(event_data)[:200]}")

    # 1. 归档死信消息（持久化到数据库）
    trade_no = event_data.get("trade_no", "unknown_dead")
    dead_event_id = f"{trade_no}_DeadEvent_{task_id}"
    EventLog.objects.create(
        event_id=dead_event_id,
        event_type='SeckillDeadEvent',
        event_data=event_data,
        status='dead',
        error_msg="消息进入死信队列，消费失败",
        retry_count=3
    )

    # 2. 自动兜底：重新触发库存补偿
    goods_id = event_data.get("goods_id")
    if trade_no != "unknown_dead" and goods_id:
        send_compensate_event.delay({
            "trade_no": trade_no,
            "goods_id": goods_id,
            "qty": 1,
            "reason": "死信队列兜底处理"
        })
        logger.info(f"【死信队列消费】已触发自动兜底 → trade_no={trade_no}，goods_id={goods_id}")

    logger.info(f"【死信队列消费】完成归档 → task_id={task_id}，dead_event_id={dead_event_id}")
    return f"✅ 死信消息{dead_event_id}归档+兜底完成"
                
@shared_task
def refresh_analytics_cache():
    """刷新分析缓存（补充缺失的任务）"""
    logger = logging.getLogger('celery.worker')
    task_id = current_task.request.id
    logger.info(f"【刷新分析缓存任务启动】task_id={task_id}，执行空实现（可补充业务逻辑）")
    return "分析缓存刷新完成（空实现）"
