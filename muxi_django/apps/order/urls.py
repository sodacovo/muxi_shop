

from django.urls import path, re_path
from .views import OrderGoodsGenericAPIView,OrderGenericAPIView,OrderDetailGenericAPIView

urlpatterns = [
    path("",OrderGenericAPIView.as_view()),
    path("goods/",OrderGoodsGenericAPIView.as_view()),
    path("update/",OrderDetailGenericAPIView.as_view()),
    re_path("goods/(?P<trade_no>.*)",OrderGoodsGenericAPIView.as_view()),
]



"""
1.路由捕获：把 trade_no 塞进 kwargs

当请求 GET /goods/T20250907001 时，
Django 的正则会把 T20250907001 捕获为关键字参数：

kwargs = {'trade_no': 'T20250907001'}
这个字典随后会被原封不动地传进视图实例的 self.kwargs
*********************************************
2.GenericAPIView 的两条关键属性

lookup_field = 'trade_no'  # 数据库里用于唯一定位记录的字段名
lookup_url_kwarg = None # 默认 None，此时 fallback 到 lookup_field

lookup_url_kwarg 显式指定时，视图就从 self.kwargs[lookup_url_kwarg] 取值；
为 None 时，就用 lookup_field 作为键。

因此上面代码等价于： lookup_url_kwarg = 'trade_no'

3.DRF 的 get_object

“用 URL 里捕获的 trade_no 作为关键字，
拼成 {lookup_field: 值} 去 queryset 里 get()，找不到就抛 404。”


URL /goods/T20250907001
   │
   ▼
re_path 捕获  ──►  self.kwargs = {'trade_no': 'T20250907001'}
   │
   ▼
get_object()  ──►  lookup_field='trade_no'
   │                       │
   │                       ▼
   │               filter_kwargs = {'trade_no': 'T20250907001'}
   │                       │
   │                       ▼
   └───── get_object_or_404(queryset, **filter_kwargs)
                           │
                           ▼
                      return obj    (或 404)
                      
  一句话记忆
lookup_field 告诉 DRF “用哪个数据库字段” 去匹配；
lookup_url_kwarg 告诉 DRF “到 URL 的哪个关键字参数” 里取值；
get_object() 帮你把这两件事拼成一次 get() 查询，顺便做权限/404 处理。                    
                      
"""