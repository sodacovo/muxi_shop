from django.urls import path
from . import views

urlpatterns = [
    path('submit/', views.SeckillSubmitView.as_view()),
    path('result/', views.SeckillResultView.as_view()),
    path('stock/', views.SeckillStockView.as_view()),
]