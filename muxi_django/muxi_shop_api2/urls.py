"""
URL configuration for muxi_shop_api2 project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from apps import goods, cart
from menu.views import GoodsMainMenu, GoodsSubMenu
from django_prometheus.exports import ExportToDjangoView
from apps.goods.views import custom_metrics, simplejson_metrics
# 测试错误视图
def sentry_debug(request):
    # 故意触发除零错误
    division_by_zero = 1 / 0
    return HttpResponse("This line won't run")

# 👇 新增这个函数，触发除零错误
def trigger_sentry_error(request):
    1 / 0  # 核心：触发异常，让Sentry捕获
    return HttpResponse("OK")

urlpatterns = [
    path("admin/", admin.site.urls),
    path('metrics/', ExportToDjangoView), 
    path('custom-metrics/', custom_metrics, name='custom-metrics'),
    path('simplejson/', simplejson_metrics, name='simplejson'),
    path('simplejson/annotations', simplejson_metrics, name='simplejson-annotations'),
    path("main_menu/", GoodsMainMenu.as_view(), name="main_menu"),
    path("sub_menu/", GoodsSubMenu.as_view(), name="sub_menu"),
    path("goods/", include("goods.urls")),
    path("cart/", include("cart.urls")),
    path("user/", include("user.urls")),
    path("order/", include("order.urls")),
    path("address/", include("address.urls")),
    path("comment/", include("comment.urls")),
    path("pay/", include("pay.urls")),
    path('seckill/', include('seckill.urls')),
    path('analytics/', include('analytics.urls')),
    path('sentry-debug/', sentry_debug),
    # path('sentry-debug/', trigger_sentry_error),
    
]
