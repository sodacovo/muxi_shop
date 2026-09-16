from django.urls import path, re_path
from .views import CommentCountAPIView, CommentAPIView, CommentGenericAPIView, test_settings

urlpatterns = [
    path('test-settings/', test_settings),
    path('count/', CommentCountAPIView.as_view()),   # 匹配 /comment/count/
    path('detail/', CommentAPIView.as_view()),       # 匹配 /comment/detail/
    path('', CommentGenericAPIView.as_view({
        'get': 'my_list',
        'post': 'create'
    })),
    re_path(r'^(?P<pk>.+)/$', CommentGenericAPIView.as_view({
        'get': 'single',
        'put': 'edit',
        'delete': 'my_delete'
    })),
]