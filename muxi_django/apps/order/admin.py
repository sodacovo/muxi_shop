from django.contrib import admin
from .models import Order, OrderGoods

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('trade_no', 'email', 'order_amount', 'pay_status', 'create_time')
    list_filter = ('pay_status', 'create_time')
    search_fields = ('trade_no', 'email')
    # 新增：批量标记为已支付（演示微信支付用）
    actions = ['mark_as_paid']

    def mark_as_paid(self, request, queryset):
        # 只标记待支付的订单
        updated_count = queryset.filter(pay_status="0").update(pay_status="2")
        self.message_user(request, f"成功标记 {updated_count} 个订单为「已支付」")
    mark_as_paid.short_description = "标记选中订单为已支付（演示用）"

# 原有OrderGoodsAdmin（不动）
@admin.register(OrderGoods)
class OrderGoodsAdmin(admin.ModelAdmin):
    list_display = ('trade_no', 'sku_id', 'goods_num')
    search_fields = ('trade_no',)