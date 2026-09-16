from .base import *
import os  # 用于读取环境变量（敏感信息不硬编码）

# 1. 生产环境：DEBUG关闭+严格域名
DEBUG = False
ALLOWED_HOSTS = ["www.muxishop.com", "muxishop.com"]  # 你的线上域名（替换！）

# 2. 生产密钥：从环境变量读取（避免硬编码）
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")  # 线上部署时设置环境变量

# 3. 生产数据库：敏感信息从环境变量读取
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("DB_NAME", "muxi_shop_prod"),  # 生产数据库名
        "USER": os.getenv("DB_USER", "prod_admin"),      # 生产数据库用户
        "PASSWORD": os.getenv("DB_PWD"),                 # 生产密码（环境变量）
        "HOST": os.getenv("DB_HOST", "192.168.80.100"),  # 生产数据库IP（替换！）
        "PORT": os.getenv("DB_PORT", "3306"),
        "OPTIONS": {
            "charset": "utf8mb4",
            "connect_timeout": 10,  # 超时保护
        },
        "CONN_MAX_AGE": 300,  # 长连接（优化生产性能）
    }
}

# 4. 生产Redis：带密码（防未授权访问）
REDIS_PWD = os.getenv("REDIS_PWD")  # Redis密码（环境变量）
CACHES["default"]["LOCATION"] = f"redis://:{REDIS_PWD}@192.168.80.100:6379/0"
CACHES["sms"]["LOCATION"] = f"redis://:{REDIS_PWD}@192.168.80.100:6379/1"
CACHES["carts"]["LOCATION"] = f"redis://:{REDIS_PWD}@192.168.80.100:6379/2"
CACHES["seckill"]["LOCATION"] = f"redis://:{REDIS_PWD}@192.168.80.100:6379/3"

# 5. 生产Celery配置
CELERY_BROKER_URL = CACHES["seckill"]["LOCATION"]
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_TASK_ACKS_LATE = True  # 生产环境必须开启（防任务丢失）
CELERYD_CONCURRENCY = 8  # 生产环境并发数（根据CPU核心数调整）

# 6. 生产静态文件：用CDN（替换成你的CDN地址！）
STATIC_URL = "https://cdn.muxishop.com/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "static_prod")  # 收集静态文件的目录
IMAGE_URL = "https://cdn.muxishop.com/static/product_images/"
USER_AVATAR_URL = "https://cdn.muxishop.com/static/user_avatars/"

# 7. 生产安全配置（必须开启！）
SECURE_SSL_REDIRECT = True  # 强制HTTPS
SESSION_COOKIE_SECURE = True  # Session仅HTTPS传输
CSRF_COOKIE_SECURE = True    # CSRF仅HTTPS传输
SECURE_BROWSER_XSS_FILTER = True  # 防XSS攻击

# 8. 生产第三方服务（正式环境配置，替换！）
## 邮件（企业邮箱）
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.muxishop.com")
EMAIL_HOST_USER = os.getenv("EMAIL_USER", "service@muxishop.com")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_PWD")
EMAIL_PORT = 465
EMAIL_USE_SSL = True
DEFAULT_FROM_EMAIL = "木犀商城 <service@muxishop.com>"

## 支付宝（正式环境）
APPID = os.getenv("ALIPAY_APPID", "2021000000000000")  # 正式APPID
ALI_PUB_KEY_PATH = os.path.join(BASE_DIR, "apps/pay/keys/alipay_prod_key.txt")
PRIVATE_KEY_PATH = os.path.join(BASE_DIR, "apps/pay/keys/private_prod_key.txt")
APP_NOTIFY_URL = "https://www.muxishop.com/pay/alipay/notify"
RETURN_URL = "https://www.muxishop.com/pay/alipay/return"
ALIPAY_DEBUG = False  # 关闭沙箱

## 新浪微博（正式回调）
WEIBO_REDIRECT_URI = "https://www.muxishop.com/weibo/callback"