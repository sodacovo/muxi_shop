from django.urls import path
from . import views

urlpatterns = [
    path("dashboard/", views.analytics_dashboard, name="analytics_dashboard"),
    path("api/sales/", views.sales_analysis_api, name="sales_analysis_api"),
    path("api/order-status/", views.order_status_analysis_api, name="order_status_analysis_api"),
    path("api/seckill/", views.seckill_analysis_api, name="seckill_analysis_api"),
]