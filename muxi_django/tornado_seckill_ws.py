import tornado.ioloop
import tornado.web
import tornado.websocket
import redis
import json
import logging
import os
import re
from datetime import datetime, timedelta

# 配置 Django 环境
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "muxi_shop_api2.settings.settings_dev")
import django
django.setup()

from django.conf import settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('tornado.ws')

# 初始化 Redis 连接
redis_config = settings.TORNADO_WS_CONFIG["redis"]
redis_conn = redis.Redis(
    host=redis_config["host"],
    port=redis_config["port"],
    db=redis_config["db"],
    decode_responses=redis_config["decode_responses"],
    socket_timeout=5
)
SECKILL_RESULT_CHANNEL = settings.TORNADO_WS_CONFIG["redis_channels"]["seckill_result"]

# 新增：秒杀结果缓存（key=task_id，value=结果数据，过期时间5分钟）
result_cache = {}
CACHE_EXPIRE = 300  # 5分钟

# 管理 WebSocket 连接
connection_map = {}

# Redis 订阅回调：新增缓存逻辑
def on_redis_message(message):
    if message["type"] == "message":
        try:
            data = json.loads(message["data"])
            task_id = data.get("task_id")
            logger.info(f"[Tornado Redis] 收到消息 → task_id={task_id}，data={data}")
            if task_id:
                # 1. 缓存结果（5分钟过期）
                result_cache[task_id] = {
                    "data": data,
                    "expire_at": datetime.now() + timedelta(seconds=CACHE_EXPIRE)
                }
                # 2. 推送在线连接
                if task_id in connection_map:
                    connection_map[task_id].write_message(json.dumps(data))
                    logger.info(f"[Tornado WS] 推送成功 → task_id={task_id}，status={data.get('status')}")
                else:
                    logger.warning(f"[Tornado WS] 未找到连接 → task_id={task_id}，已缓存结果")
            else:
                logger.warning(f"[Tornado Redis] 消息无 task_id → data={data}")
        except Exception as e:
            logger.error(f"[Tornado Redis] 消息处理失败 → 错误={str(e)}，消息={message.get('data')}")

# WebSocket 处理类：新增缓存检查
class SeckillWebSocketHandler(tornado.websocket.WebSocketHandler):
    def check_origin(self, origin):
        logger.info(f"[Tornado WS] 检查跨域 → origin={origin}")
        return True

    def open(self, *args):
        """连接建立时：提取task_id + 检查缓存 + 补发历史结果"""
        # 提取 task_id
        task_id = ""
        if args:
            task_id = args[-1].strip('/')
        if not task_id:
            path = self.request.path
            match = re.search(r'/ws/seckill/([^/]+)', path)
            if match:
                task_id = match.group(1).strip('/')
        
        self.task_id = task_id
        if task_id:
            # 1. 记录连接
            connection_map[task_id] = self
            logger.info(f"[Tornado WS] 连接建立 → task_id={task_id}，URL={self.request.path}，当前连接数={len(connection_map)}")
            
            # 2. 发送连接成功消息
            connect_msg = {
                "code": 8000,
                "status": "connected",
                "message": "Tornado WebSocket 连接成功",
                "task_id": task_id
            }
            self.write_message(json.dumps(connect_msg))
            
            # 3. 检查缓存：若有历史秒杀结果，立即补发
            if task_id in result_cache:
                cache_item = result_cache[task_id]
                # 检查缓存是否过期
                if datetime.now() < cache_item["expire_at"]:
                    self.write_message(json.dumps(cache_item["data"]))
                    logger.info(f"[Tornado WS] 补发缓存结果 → task_id={task_id}，data={cache_item['data']}")
                    # 补发后删除缓存（避免重复推送）
                    del result_cache[task_id]
                else:
                    del result_cache[task_id]
        else:
            logger.error(f"[Tornado WS] 连接失败 → 未提取到 task_id，URL={self.request.path}")
            self.close(code=400, reason="task_id 缺失")

    def on_message(self, message):
        try:
            data = json.loads(message)
            logger.info(f"[Tornado WS] 收到前端消息 → task_id={self.task_id}，message={data}")
            if data.get("type") == "heartbeat":
                self.write_message(json.dumps({"type": "pong", "timestamp": data.get("timestamp")}))
        except Exception as e:
            logger.error(f"[Tornado WS] 处理前端消息失败 → task_id={self.task_id}，错误={str(e)}")

    def on_close(self):
        """延迟移除连接（避免短时间内重连丢失）- 修复 lambda + del 语法错误"""
        if hasattr(self, 'task_id') and self.task_id in connection_map:
            # 定义独立的移除函数（替代lambda，解决del语法问题）
            def remove_connection(tid):
                current_count = len(connection_map)
                if tid in connection_map:
                    del connection_map[tid]
                    logger.info(f"[Tornado WS] 连接关闭（延迟移除）→ task_id={tid}，当前连接数={current_count - 1}")
                else:
                    logger.info(f"[Tornado WS] 连接已提前移除 → task_id={tid}，当前连接数={current_count}")
            
            # 延迟10秒执行移除操作
            tornado.ioloop.IOLoop.current().call_later(
                10, 
                remove_connection,  # 传入移除函数
                self.task_id        # 传入task_id参数
            )

def start_tornado():
    app = tornado.web.Application([
        (r"/ws/seckill/.*", SeckillWebSocketHandler),
    ])
    port = settings.TORNADO_WS_CONFIG.get("port", 8666)
    app.listen(port, address='0.0.0.0')
    logger.info(f"[Tornado] 服务启动成功：http://0.0.0.0:{port}")

    # 启动 Redis 订阅
    pubsub = redis_conn.pubsub()
    pubsub.subscribe(**{SECKILL_RESULT_CHANNEL: on_redis_message})
    pubsub.run_in_thread(sleep_time=0.01, daemon=True)
    logger.info(f"[Tornado Redis] 开始订阅频道：{SECKILL_RESULT_CHANNEL}（线程模式）")

    # 定时清理过期缓存
    def clean_expired_cache():
        global result_cache
        now = datetime.now()
        expired_keys = [k for k, v in result_cache.items() if now > v["expire_at"]]
        for k in expired_keys:
            del result_cache[k]
        logger.info(f"[Tornado Cache] 清理过期缓存 → 清理数量={len(expired_keys)}，剩余缓存={len(result_cache)}")
    
    # 每分钟清理一次缓存
    tornado.ioloop.PeriodicCallback(clean_expired_cache, 60 * 1000).start()

    tornado.ioloop.IOLoop.current().start()

if __name__ == "__main__":
    start_tornado()