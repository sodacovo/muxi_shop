from kombu import Exchange, Queue
from .base import *
import logging
from utils.logging import LineCountRotatingFileHandler
import sys
import os
# import sentry_sdk
# from sentry_sdk.integrations.django import DjangoIntegration
from datetime import timedelta
# 强制设置默认编码为UTF-8
if sys.version_info.major == 2:
    reload(sys)
    sys.setdefaultencoding('utf-8')
os.environ['LC_ALL'] = 'en_US.UTF-8'
os.environ['LANG'] = 'en_US.UTF-8'
os.environ['PYTHONIOENCODING'] = 'utf-8'
# 1. 开发环境专属：DEBUG开启+宽松域名
DEBUG = True
ALLOWED_HOSTS = ["*"]

# 2. 开发密钥
SECRET_KEY = "django-insecure-l!fnpi@_wq53xk62d@cjpo5t_e)n!uqj$_u9r&tv6x8$fzsd01"

# 3. 开发数据库

DATABASES = {
    "default": {
        # 关键修改：用 django-prometheus 包装后的 MySQL 引擎
        "ENGINE": "django_prometheus.db.backends.mysql",  
        "NAME": "muxi_shop",                   # 开发数据库名
        "USER": "admin1",                      # 开发数据库用户名
        "PASSWORD": "123",                     # 开发数据库密码
        "HOST": "127.0.0.1",                   # 数据库IP（虚拟机IP）
        "PORT": "3306",                        # 数据库端口
        "OPTIONS": {
            "charset": "utf8mb4",              # 避免中文乱码
            "use_unicode": True,
        },
        "CONN_MAX_AGE": 60,  # 数据库连接复用（优化性能）
    }
}

# 4. 开发Redis：指定各库的地址
CACHES["default"]["LOCATION"] = "redis://127.0.0.1:6379/0"    # 默认库
CACHES["sms"]["LOCATION"] = "redis://127.0.0.1:6379/1"        # 短信库
CACHES["carts"]["LOCATION"] = "redis://127.0.0.1:6379/2"      # 购物车库
CACHES["seckill"]["LOCATION"] = "redis://127.0.0.1:6379/3"    # 秒杀库

# 这个是测试Redis三坑
CACHES["test_redis"] = {
    "BACKEND": "django_redis.cache.RedisCache",
    "LOCATION": "redis://127.0.0.1:6379/5",  
    "OPTIONS": {
        "CLIENT_CLASS": "django_redis.client.DefaultClient",
        "PARSER_CLASS": "redis.connection._HiredisParser",  # 
    }
}


# 5. Celery配置：根据需要注释/取消注释以下配置
# --------------------双模式切换入口----------------------
# 模式1：Redis 模式
# CELERY_BROKER_URL = settings.CACHES["seckill"]["LOCATION"]
# CELERY_RESULT_BACKEND = CELERY_BROKER_URL

# 模式2：RabbitMQ 模式（注释Redis模式，启用以下两行）
CELERY_BROKER_URL = 'amqp://admin:123456@localhost:5672//'
CELERY_RESULT_BACKEND = 'rpc://'

# ---------------------- 通用配置----------------------
CELERY_TIMEZONE = "Asia/Shanghai"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERYD_MAX_TASKS_PER_CHILD = 10  # 防止内存泄漏
CELERYD_CONCURRENCY = 4  # 并发数

# ---------------------- 定时任务----------------------
CELERY_BEAT_SCHEDULE = {
    'cancel-unpaid-seckill-orders': {
        'task': 'order.tasks.cancel_unpaid_orders',
        'schedule': timedelta(minutes=30),
    },
    'update-celery-queue-metrics': {
        'task': 'order.tasks.update_celery_queue_metrics',
        'schedule': timedelta(seconds=7200),
    },
    'check-stock-consistency': {
        'task': 'order.tasks.check_stock_consistency',
        'schedule': timedelta(minutes=7200),
    },
    'refresh-analytics-cache': {
        'task': 'order.tasks.refresh_analytics_cache',
        'schedule': timedelta(hours=1),
    },
}

# ---------------------- 模式隔离配置（强化可靠性）----------------------
# 1. RabbitMQ 模式专属配置（手动 ACK+生产者确认+持久化+死信队列）
if "amqp://" in CELERY_BROKER_URL:
    # 手动ACK（确保任务处理完成后再确认）
    CELERY_TASK_ACKS_LATE = True
    CELERY_TASK_RETRY = True
    CELERY_TASK_RETRY_POLICY = {
        "max_retries": 3,
        "interval_start": 2,
        "interval_step": 5,
        "interval_max": 15,
    }
    CELERYD_MAX_TASKS_PER_CHILD = 100  # RabbitMQ 模式优化内存

    # 消息/队列/交换机 持久化（避免RabbitMQ崩溃丢失消息）
    CELERY_TASK_PERSISTENT = True
    CELERY_QUEUE_PERSISTENT = True
    CELERY_EXCHANGE_PERSISTENT = True

    # 生产者发布确认（确保消息成功发送到RabbitMQ）
    CELERY_BROKER_TRANSPORT_OPTIONS = {
        'confirm_publish': True,
        'max_retries': 3,
        'interval_start': 0,
        'interval_step': 1,
        'interval_max': 5,
    }

    # 定义业务队列+死信队列
    SECKILL_QUEUE = Queue(
        name='seckill_event_queue',
        exchange=Exchange('seckill_event_exchange', type='direct', durable=True),
        routing_key='seckill.event',
        durable=True,
        arguments={
            'x-dead-letter-exchange': 'seckill_dead_exchange',
            'x-dead-letter-routing-key': 'seckill.dead',
            'x-message-ttl': 60000,  # 消息60秒未消费进入死信队列
        }
    )

    SECKILL_DEAD_QUEUE = Queue(
        name='seckill_dead_queue',
        exchange=Exchange('seckill_dead_exchange', type='direct', durable=True),
        routing_key='seckill.dead',
        durable=True
    )

    # 注册队列
    CELERY_TASK_QUEUES = (SECKILL_QUEUE, SECKILL_DEAD_QUEUE)

    # 任务路由（指定任务到对应队列）
    CELERY_TASK_ROUTES = {
        'order.tasks.send_seckill_event': {'queue': 'seckill_event_queue', 'routing_key': 'seckill.event'},
        'order.tasks.consume_stock_event': {'queue': 'seckill_event_queue', 'routing_key': 'seckill.event'},
        'order.tasks.send_compensate_event': {'queue': 'seckill_event_queue', 'routing_key': 'seckill.event'},
        'order.tasks.consume_dead_seckill_event': {'queue': 'seckill_dead_queue', 'routing_key': 'seckill.dead'},
    }

# 2. Redis 模式专属配置（默认自动 ACK，无需额外配置）
elif "redis://" in CELERY_BROKER_URL:
    CELERY_TASK_ACKS_LATE = False  # Redis 不支持手动 ACK，禁用
    CELERY_TASK_RETRY = True
    CELERY_TASK_RETRY_POLICY = {
        "max_retries": 2,
        "interval_start": 3,
        "interval_step": 2,
        "interval_max": 10,
    }

# ===================== WebSocket 服务模式开关（一键切换） =====================
# True = 启用 Tornado 高并发 WebSocket 服务（秒杀高并发场景）
# False = 使用原有 Django Channels WebSocket 服务（兼容原有逻辑）
USE_TORNADO_WS = True  # 注释/取消注释即可切换

# Tornado WS 配置（开发环境：本地Redis，端口8666）
TORNADO_WS_CONFIG = {
    "port": 8666,  # 指定8666端口，避免冲突
    "redis": {
        "host": "127.0.0.1",  # 开发环境Redis地址（本地）
        "port": 6379,
        "db": 3,  # 秒杀专用库（匹配CACHES["seckill"]["LOCATION"]的3号库）
        "decode_responses": True
    },
    "redis_channels": {
        "seckill_result": "seckill_result",  # 秒杀结果推送频道
        "seckill_stock": "seckill_stock"     # 库存更新推送频道
    }
}


# 6. 开发静态文件：本地访问路径
STATIC_URL = "/static/"  # 静态文件访问前缀
STATIC_ROOT = os.path.join(BASE_DIR, "collected_static")  # 静态文件收集目录
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),  # 根目录下的static文件夹
]

MEDIA_URL = "/media/"  # 媒体文件访问前缀
MEDIA_ROOT = os.path.join(BASE_DIR, "media")  # 媒体文件实际存放目录

# 图片/头像访问URL（替换为域名，避免IP访问失效）
IMAGE_URL = "http://www.nwq1309.shop/static/product_images/"
USER_AVATAR_URL = "http://www.nwq1309.shop/media/user_avatars/"
USER_BACKGROUND_URL = "http://www.nwq1309.shop/media/user_backgrounds/"

# 7. 第三方服务配置
## 邮件（QQ测试邮箱）
EMAIL_HOST = 'smtp.qq.com'
EMAIL_PORT = 465
EMAIL_HOST_USER = '2350496649@qq.com'
EMAIL_HOST_PASSWORD = 'zrzudgnpwbnsecaa'
DEFAULT_FROM_EMAIL = '2350496649@qq.com'
ERROR_EMAIL_RECIPIENTS = ['2350496649@qq.com'] # 接受错误邮件

## 支付宝（沙箱）
APPID = "9021000155668647"
ALI_PUB_KEY_PATH = os.path.join(BASE_DIR, "apps/pay/keys/alipay_key.txt")
PRIVATE_KEY_PATH = os.path.join(BASE_DIR, "apps/pay/keys/private_key.txt")
APP_NOTIFY_URL = "http://www.nwq1309.shop/pay/alipay/return/"
RETURN_URL = "http://www.nwq1309.shop/pay/alipay/return/"
ALIPAY_DEBUG = True


# 微信支付模拟配置
WECHAT_PAY_CONFIG = {
    "mch_id": "1900009881",
    "api_key": "abcdef1234567890abcdef1234567890",
    "notify_url": "http://www.nwq1309.shop/pay/wechat/notify/",
}


## 新浪微博
WEIBO_APP_KEY = "780919870"
WEIBO_APP_SECRET = "298c445669e83b882df28909d3520e1a"
WEIBO_REDIRECT_URI = "http://www.nwq1309.shop/weibo/callback"


# Sentry 异常监控配置
# sentry_sdk.init(
#     dsn="http://a68b2918bd424dbe9661c211f28fd678@8.138.126.24:9000/2",  正确保留
#     integrations=[DjangoIntegration()], 
#     traces_sample_rate=1.0,  
#     send_default_pii=True,  
#     environment="development",
#     debug=True,
# )

# ---------------------- 日志配置 ----------------------
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        # 统一格式：时间 + 级别 + 任务类型 + 订单号 + 消息（核心优化）
        'standard': {
            'format': '%(asctime)s [%(levelname)s] [%(task_type)s] [%(trade_no)s] %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
    },
    'filters': {
        # 启用上下文过滤器（添加trade_no和task_type）
        'context_filter': {
            '()': 'utils.logging.ContextFilter',
        }
    },
    'handlers': {
        # uwsgi日志（保留原有路径和分割逻辑）
        'uwsgi_handler': {
            'class': 'utils.logging.LineCountRotatingFileHandler',
            'filename': 'logs/uwsgi.log',
            'max_lines': 5000,
            'backup_count': 3,
            'encoding': 'utf-8',
            'formatter': 'standard',  # 使用统一格式
            'filters': ['context_filter'],  # 应用上下文过滤器
        },
        # Celery Beat日志
        'celery_beat_handler': {
            'class': 'utils.logging.LineCountRotatingFileHandler',
            'filename': 'logs/celery_beat.log',
            'max_lines': 5000,
            'backup_count': 3,
            'encoding': 'utf-8',
            'formatter': 'standard',
            'filters': ['context_filter'],
        },
        # Celery Worker日志（核心任务日志）
        'celery_worker_handler': {
            'class': 'utils.logging.LineCountRotatingFileHandler',
            'filename': 'logs/celery_worker.log',
            'max_lines': 5000,
            'backup_count': 3,
            'encoding': 'utf-8',
            'formatter': 'standard',
            'filters': ['context_filter'],
        },
        # 控制台输出（开发调试用）
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
            'filters': ['context_filter'],
        }
    },
    'loggers': {
        'django': {
            'handlers': ['uwsgi_handler', 'console'],  # 开发时添加console
            'level': 'INFO',
            'propagate': False,
        },
        'uwsgi_logger': {
            'handlers': ['uwsgi_handler'],
            'level': 'INFO',
            'propagate': False,
        },
        'celery.beat': {
            'handlers': ['celery_beat_handler', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'celery.worker': {
            'handlers': ['celery_worker_handler', 'console'],  # Worker日志用专用handler
            'level': 'INFO',
            'propagate': False,
        },
        'app': {
            'handlers': ['uwsgi_handler', 'console'],
            'level': "INFO",
            'propagate': False
        },
    },
}

# 确保logs目录存在
logs_dir = os.path.join(BASE_DIR, 'logs')
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir, mode=0o755)
    
    

