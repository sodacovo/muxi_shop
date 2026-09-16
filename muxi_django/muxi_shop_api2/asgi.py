import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

# 1. 正确导入：WebSocket 文件在 order 应用，所以导入 order 的 routing
import apps.order.routing  

# 2. 正确指定服务器配置文件（settings_dev.py，之前的 settings 是默认，服务器用 dev 配置）
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'muxi_shop_api2.settings_dev')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            # 正确指向：order 应用的 WebSocket 路由列表
            apps.order.routing.websocket_urlpatterns  
        )
    ),
})