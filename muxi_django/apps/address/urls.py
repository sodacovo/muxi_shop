from django.urls import path
from rest_framework.routers import SimpleRouter
from .views import AddressViewSet  # 仅需导入 AddressViewSet（已包含列表功能）

# 1. 注册 ViewSet 路由，绑定根路径 /address/
router = SimpleRouter()
# 路径设为 ""，匹配 /address/，自动映射 ViewSet 的方法：
# - GET /address/ → list 方法（获取列表）
# - POST /address/ → create 方法（新增地址）
router.register(r'', AddressViewSet, basename='address')

urlpatterns = [
    # 2. 绑定编辑/删除/设默认的路由（对应 ViewSet 的自定义方法）
    path("edit/", AddressViewSet.as_view({"post": "edit"}), name="address-edit"),
    path("delete/", AddressViewSet.as_view({"post": "delete_address"}), name="address-delete"),
    path("setDefault/", AddressViewSet.as_view({"post": "set_default"}), name="address-set-default"),
]

# 3. 合并 ViewSet 自动生成的路由
urlpatterns += router.urls