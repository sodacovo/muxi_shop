from .base import *

# 1. 测试环境：DEBUG开启+测试域名
DEBUG = True
ALLOWED_HOSTS = ["test.muxishop.com", "127.0.0.1"]

# 2. 测试密钥（简单密钥，无需保密）
SECRET_KEY = "test-secret-key-1234567890"

# 3. 测试数据库（专用测试库，避免污染开发数据）
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "test_muxi_shop",  # 测试库名（单独创建！）
        "USER": "test_admin",      # 测试数据库用户
        "PASSWORD": "test_123",   # 测试密码
        "HOST": "192.168.80.144",
        "PORT": "3306",
        "OPTIONS": {"charset": "utf8mb4"},
    }
}

# 4. 测试Redis：用单独的10-13号库（避免污染开发/生产）
CACHES["default"]["LOCATION"] = "redis://192.168.80.144:6379/10"
CACHES["sms"]["LOCATION"] = "redis://192.168.80.144:6379/11"
CACHES["carts"]["LOCATION"] = "redis://192.168.80.144:6379/12"
CACHES["seckill"]["LOCATION"] = "redis://192.168.80.144:6379/13"

# 5. 测试Celery配置（降低并发，减少资源占用）
CELERY_BROKER_URL = CACHES["seckill"]["LOCATION"]
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERYD_CONCURRENCY = 2  # 测试环境低并发

# 6. 测试静态文件：本地访问
STATIC_URL = "static/"
IMAGE_URL = "http://test.muxishop.com/static/product_images/"

# 7. 测试优化：关闭CSRF（方便接口测试工具调用）
MIDDLEWARE.remove("django.middleware.csrf.CsrfViewMiddleware")

# 8. 测试第三方服务（用测试账号）
ALIPAY_DEBUG = True  # 测试用支付宝沙箱
WEIBO_REDIRECT_URI = "http://test.muxishop.com/weibo/callback"