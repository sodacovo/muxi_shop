
from django.urls import path
from .views import GoodsCategoryAPIView, GoodsDetailAPIView, GoodsFindAPIView, GoodSearchAPIView, \
    GoodsSearchDataCountAPIView, InitSeckillStockAPIView, RecommendView, GoodsBehaviorAPIView, test_cache_penetration, test_cache_breakdown

urlpatterns = [
    path("find/", GoodsFindAPIView.as_view()),
    path("category/<int:category_id>/<int:page>/", GoodsCategoryAPIView.as_view()),
    path("search/<str:keyword>/<int:page>/<int:order_by>/", GoodSearchAPIView.as_view()),
    path("get_keyword_data_count/<str:keyword>/", GoodsSearchDataCountAPIView.as_view()),
    path("init-seckill-stock/", InitSeckillStockAPIView.as_view()),
    # 1. 固定路由：推荐接口放前面
    path('recommend/', RecommendView.as_view()),
    # 2. 动态路由：商品详情放后面
    path("<str:sku_id>/", GoodsDetailAPIView.as_view()),
    path('behavior/<int:sku_id>/', GoodsBehaviorAPIView.as_view()),
    path("test/penetration/<int:goods_id>/", test_cache_penetration),
    path("test/breakdown/", test_cache_breakdown, name="test_breakdown"),
]