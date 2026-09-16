from .base import *
from .settings_dev import *

# ============================================
# 本地开发专用配置：连接远程服务器
# ============================================

DEBUG = True
ALLOWED_HOSTS = ["*"]

SECRET_KEY = "django-insecure-l!fnpi@_wq53xk62d@cjpo5t_e)n!uqj$_u9r&tv6x8$fzsd01"

# ==================== 数据库 ====================
DATABASES = {
    "default": {
        "ENGINE": "django_prometheus.db.backends.mysql",
        "NAME": "muxi_shop",
        "USER": "admin1",
        "PASSWORD": "123",
        "HOST": "8.138.126.24",
        "PORT": "3306",
        "OPTIONS": {
            "charset": "utf8mb4",
            "use_unicode": True,
        },
        "CONN_MAX_AGE": 60,
    }
}

# ==================== Redis ====================
CACHES["default"]["LOCATION"] = "redis://8.138.126.24:6379/0"
CACHES["sms"]["LOCATION"] = "redis://8.138.126.24:6379/1"
CACHES["carts"]["LOCATION"] = "redis://8.138.126.24:6379/2"
CACHES["seckill"]["LOCATION"] = "redis://8.138.126.24:6379/3"

CACHES["test_redis"] = {
    "BACKEND": "django_redis.cache.RedisCache",
    "LOCATION": "redis://8.138.126.24:6379/5",
    "OPTIONS": {
        "CLIENT_CLASS": "django_redis.client.DefaultClient",
    }
}

# ==================== Channel Layer ====================
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": ["redis://8.138.126.24:6379/3"],
            "capacity": 1500,
            "expiry": 300,
        },
    },
}

# ==================== Celery ====================
CELERY_BROKER_URL = 'amqp://admin:123456@8.138.126.24:5672//'
CELERY_RESULT_BACKEND = 'rpc://'
CELERY_TIMEZONE = "Asia/Shanghai"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERYD_MAX_TASKS_PER_CHILD = 10
CELERYD_CONCURRENCY = 4

# ==================== Tornado WebSocket ====================
USE_TORNADO_WS = True
TORNADO_WS_CONFIG = {
    "port": 8666,
    "redis": {
        "host": "8.138.126.24",
        "port": 6379,
        "db": 3,
        "decode_responses": True
    },
    "redis_channels": {
        "seckill_result": "seckill_result",
        "seckill_stock": "seckill_stock"
    }
}

# ==================== 静态文件 ====================
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "collected_static")
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

IMAGE_URL = "http://www.nwq1309.shop/static/product_images/"
USER_AVATAR_URL = "http://www.nwq1309.shop/media/user_avatars/"
USER_BACKGROUND_URL = "http://www.nwq1309.shop/media/user_backgrounds/"

# ==================== 日志（本地） ====================
import logging
LOGGING['handlers']['console'] = {
    'class': 'logging.StreamHandler',
    'formatter': 'standard',
}
