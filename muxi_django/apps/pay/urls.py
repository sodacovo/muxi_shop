from django.urls import path
from .views import (
    ToAliPayPageAPIView,
    AlipayAPIView,
    wechat_pay_qrcode,  
    wechat_pay_query,   
    wechat_pay_notify,
    get_order_detail
)


urlpatterns = [
    # 支付宝路由
    path("alipay/", ToAliPayPageAPIView.as_view()),
    path("alipay/return/", AlipayAPIView.as_view()),
    
    # 微信路由（必须加入urlpatterns，不能漏）
    path('wechat/qrcode/', wechat_pay_qrcode, name='wechat_qrcode'),
    path('wechat/query/', wechat_pay_query, name='wechat_query'),
    path('wechat/notify/', wechat_pay_notify, name='wechat_notify'),
    path('order/detail/', get_order_detail, name='get_order_detail'),
]