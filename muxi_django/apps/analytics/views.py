from django.shortcuts import render
# from django.contrib.auth.decorators import login_required  # 暂时注释，方便测试

from django.db.models import Q, Sum, Count, Avg, Value, CharField, Case, When, F  # 新增 Case、When、F
from django.db.models.functions import Concat  # Concat 需从 functions 导入
from django.db.models.functions import ExtractMonth, ExtractDay  # 保留你的原始导入
from django.http import JsonResponse
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
import pytz

# -------------------------- 恢复你原始的模型导入路径（关键修复！）--------------------------
from order.models import Order, OrderGoods
from goods.models import Goods

# -------------------------- 核心配置（完全保留你的原始配置）--------------------------
PAY_STATUS_MAP = {
    "0": "待确认",
    "1": "待付款",
    "2": "待收货",
    "3": "已完成",
    "4": "已取消"
}
VALID_PAY_STATUSES = ["0", "1", "2", "3"]
COMPLETED_PAY_STATUS = "3"
NOT_DELETED_CONDITION = {"is_delete__in": ["0", None]}

# -------------------------- 工具函数（完全保留你的原始逻辑）--------------------------
def parse_time_range(time_range):
    range_map = {"1d": 1, "7d": 7, "30d": 30}
    return range_map.get(time_range, 7)

def get_time_range(start_days):
    """修复时区问题：Django 3.2兼容版（返回无时区的北京时间）"""
    shanghai_tz = pytz.timezone('Asia/Shanghai')
    end_date = timezone.now().astimezone(shanghai_tz)
    start_date = end_date - timedelta(days=start_days)
    return start_date.replace(tzinfo=None), end_date.replace(tzinfo=None)

# -------------------------- 视图函数（完全保留你的原始逻辑）--------------------------
# @login_required
def analytics_dashboard(request):
    return render(request, "analytics/dashboard.html")

# -------------------------- 销售分析接口（仅修复 Case/When 导入，无其他改动）--------------------------
# @login_required
def sales_analysis_api(request):
    time_range = request.GET.get("time_range", "7d")
    start_days = parse_time_range(time_range)
    start_date, end_date = get_time_range(start_days)

    # 缓存已注释，避免旧数据干扰
    # cache_key = f"sales_analysis_{time_range}_{timezone.now().strftime('%Y%m%d%H')}"
    # cached_data = cache.get(cache_key)
    # if cached_data:
    #     return JsonResponse(cached_data)

    sales_data = Order.objects.filter(
        **NOT_DELETED_CONDITION,
        create_time__gte=start_date,
        create_time__lte=end_date,
        create_time__isnull=False,
        order_amount__isnull=False,
        pay_status__in=VALID_PAY_STATUSES
    ).annotate(
        # 核心修复：用Django原生方法拼接"月-日"（无兼容性问题）
        month=ExtractMonth('create_time'),  # 提取月份（数字）
        day=ExtractDay('create_time'),      # 提取日期（数字）
        # 拼接为"11-21"格式的字符串
        date=Concat(
            # 月份补0（比如1月→01）
            Case(
                When(month__lt=10, then=Concat(Value('0'), 'month')),
                default='month',
                output_field=CharField()
            ),
            Value('-'),  # 分隔符
            # 日期补0（比如5日→05）
            Case(
                When(day__lt=10, then=Concat(Value('0'), 'day')),
                default='day',
                output_field=CharField()
            ),
            output_field=CharField()
        )
    ).values("date").annotate(
        order_count=Count("id"),
        sales_amount=Sum("order_amount")
    ).order_by("date")

    dates = []
    order_counts = []
    sales_amounts = []
    for item in sales_data:
        if item["date"]:
            dates.append(item["date"])
            order_counts.append(item["order_count"])
            sales_amounts.append(round(float(item["sales_amount"]), 2) if item["sales_amount"] else 0)

    completed_orders = Order.objects.filter(
        **NOT_DELETED_CONDITION,
        create_time__gte=start_date,
        create_time__lte=end_date,
        create_time__isnull=False,
        order_amount__isnull=False,
        pay_status=COMPLETED_PAY_STATUS
    )
    total_sales = completed_orders.aggregate(total=Sum("order_amount"))["total"] or 0.00
    total_orders = completed_orders.count()
    avg_order_price = round(float(total_sales) / total_orders, 2) if total_orders > 0 else 0.00

    result = {
        "dates": dates,
        "order_counts": order_counts,
        "sales_amounts": sales_amounts,
        "avg_order_price": avg_order_price,
        "total_sales": round(float(total_sales), 2),
        "total_orders": total_orders
    }
    # cache.set(cache_key, result, 60*60)
    return JsonResponse(result)

# -------------------------- 订单状态分析接口（仅修复 Case/When 导入，无其他改动）--------------------------
# @login_required
def order_status_analysis_api(request):
    time_range = request.GET.get("time_range", "7d")
    start_days = parse_time_range(time_range)
    start_date, end_date = get_time_range(start_days)

    # 缓存已注释
    # cache_key = f"order_status_analysis_{time_range}_{timezone.now().strftime('%Y%m%d%H')}"
    # cached_data = cache.get(cache_key)
    # if cached_data:
    #     return JsonResponse(cached_data)

    status_distribution = Order.objects.filter(
        **NOT_DELETED_CONDITION,
        create_time__gte=start_date,
        create_time__lte=end_date,
        create_time__isnull=False,
        pay_status__in=PAY_STATUS_MAP.keys()
    ).values("pay_status").annotate(
        count=Count("id")
    ).order_by("pay_status")

    status_labels = [PAY_STATUS_MAP[item["pay_status"]] for item in status_distribution]
    status_counts = [item["count"] for item in status_distribution]

    status_trend = Order.objects.filter(
        **NOT_DELETED_CONDITION,
        create_time__gte=start_date,
        create_time__lte=end_date,
        create_time__isnull=False,
        pay_status__in=PAY_STATUS_MAP.keys()
    ).annotate(
        # 同样用Django原生方法拼接日期
        month=ExtractMonth('create_time'),
        day=ExtractDay('create_time'),
        date=Concat(
            Case(When(month__lt=10, then=Concat(Value('0'), 'month')), default='month', output_field=CharField()),
            Value('-'),
            Case(When(day__lt=10, then=Concat(Value('0'), 'day')), default='day', output_field=CharField()),
            output_field=CharField()
        )
    ).values("date", "pay_status").annotate(
        count=Count("id")
    ).order_by("date", "pay_status")

    trend_dates = []
    if status_trend:
        # 去重并排序日期
        trend_dates = sorted(list(set([item["date"] for item in status_trend if item["date"]])))

    status_series = []
    for pay_status, status_name in PAY_STATUS_MAP.items():
        status_data = []
        for date in trend_dates:
            # 匹配当前日期和支付状态的订单数
            item = next(
                (i for i in status_trend if i["date"] == date and i["pay_status"] == pay_status),
                None
            )
            status_data.append(item["count"] if item else 0)
        status_series.append({"name": status_name, "data": status_data})

    result = {
        "status_distribution": {"labels": status_labels, "counts": status_counts},
        "status_trend": {"dates": trend_dates, "series": status_series}
    }
    # cache.set(cache_key, result, 60*60)
    return JsonResponse(result)
    
# -------------------------- 秒杀订单转化分析接口（仅修复 Case/When 导入，无其他改动）--------------------------
# @login_required  # 测试完成后取消注释，限制管理员访问
def seckill_analysis_api(request):
    """秒杀订单支付转化分析：成功数、支付数、取消数、转化率、平均支付时长"""
    # 1. 时间范围筛选 
    time_range = request.GET.get("time_range", "7d")
    start_days = parse_time_range(time_range)
    start_date, end_date = get_time_range(start_days)

    # 2. 关联秒杀商品（修复：sku_id 无需转字符串，避免整数/字符串匹配失败）
    seckill_goods_ids = Goods.objects.filter(is_seckill=True).values_list("id", flat=True)  # 保留整数ID
    # 3. 关联秒杀订单：通过 OrderGoods 找到所有秒杀商品的订单号（包含已取消的订单）
    seckill_trade_nos = OrderGoods.objects.filter(
        sku_id__in=seckill_goods_ids,  # 直接用整数ID匹配，无需转字符串
        create_time__gte=start_date,
        create_time__lte=end_date,
        trade_no__isnull=False
    ).values_list("trade_no", flat=True).distinct()

    # 4. 查询秒杀订单（核心修复：去掉 NOT_DELETED_CONDITION，包含已取消的订单）
    seckill_orders = Order.objects.filter(
        # 🌟 关键修复：去掉 NOT_DELETED_CONDITION，允许查询 is_delete=1 的取消订单
        create_time__gte=start_date,
        create_time__lte=end_date,
        create_time__isnull=False,
        order_amount__isnull=False,
        trade_no__in=seckill_trade_nos
    ).distinct()

    # 5. 按状态分组统计（逻辑不变，现在能查到 is_delete=1 的取消订单）
    total_seckill = seckill_orders.count()
    paid_seckill = seckill_orders.filter(pay_status="3", pay_time__isnull=False).count()
    # 确认条件和 cancel_unpaid_orders 任务一致：pay_status="4" + is_delete=1
    cancelled_seckill = seckill_orders.filter(pay_status="4", is_delete=1).count()
    pending_seckill = seckill_orders.filter(pay_status__in=["0", "1"], is_delete__in=["0", None]).count()  # 待支付订单仍过滤已删除

    # 6. 转化率计算（逻辑不变）
    pay_conversion_rate = round((paid_seckill / total_seckill) * 100, 2) if total_seckill > 0 else 0.00

    # 7. 平均支付时长计算（逻辑不变）
    avg_pay_duration = 0.0
    if paid_seckill > 0:
        paid_orders = seckill_orders.filter(pay_status="3", pay_time__isnull=False).only("create_time", "pay_time")
        pay_durations = []
        for order in paid_orders:
            # 修复：处理时区问题（如果 create_time/pay_time 带时区）
            if order.create_time.tzinfo and order.pay_time.tzinfo:
                duration_sec = (order.pay_time - order.create_time).total_seconds()
            else:
                # 无时区时间直接计算
                duration_sec = (order.pay_time.replace(tzinfo=None) - order.create_time.replace(tzinfo=None)).total_seconds()
            pay_durations.append(duration_sec)
        avg_pay_duration = round(sum(pay_durations) / len(pay_durations) / 60, 1) if pay_durations else 0.0

    # 8. 趋势数据（修复：去掉 NOT_DELETED_CONDITION，包含取消订单）
    daily_trend = seckill_orders.annotate(
        month=ExtractMonth('create_time'),
        day=ExtractDay('create_time'),
        date=Concat(
            Case(When(month__lt=10, then=Concat(Value('0'), 'month')), default='month', output_field=CharField()),
            Value('-'),
            Case(When(day__lt=10, then=Concat(Value('0'), 'day')), default='day', output_field=CharField()),
            output_field=CharField()
        )
    ).values("date").annotate(
        daily_total=Count("id"),
        daily_paid=Count("id", filter=Q(pay_status="3", pay_time__isnull=False)),
        daily_cancelled=Count("id", filter=Q(pay_status="4", is_delete=1))  # 明确匹配取消条件
    ).order_by("date")

    trend_dates = [item["date"] for item in daily_trend if item["date"]]
    daily_totals = [item["daily_total"] for item in daily_trend]
    daily_paids = [item["daily_paid"] for item in daily_trend]
    daily_cancelleds = [item["daily_cancelled"] for item in daily_trend]
    daily_conversion_rates = [
        round((paid / total) * 100, 2) if total > 0 else 0.00
        for total, paid in zip(daily_totals, daily_paids)
    ]

    # 9. 返回结果（逻辑不变）
    result = {
        "total_seckill": total_seckill,
        "paid_seckill": paid_seckill,
        "cancelled_seckill": cancelled_seckill,  # 现在能正确统计取消数
        "pending_seckill": pending_seckill,
        "pay_conversion_rate": pay_conversion_rate,
        "avg_pay_duration": avg_pay_duration,
        "trend_dates": trend_dates,
        "daily_totals": daily_totals,
        "daily_paids": daily_paids,
        "daily_cancelleds": daily_cancelleds,
        "daily_conversion_rates": daily_conversion_rates
    }
    return JsonResponse(result)