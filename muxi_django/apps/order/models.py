from django.db import models
from django.db.models import JSONField
import uuid
from django_prometheus.models import ExportModelOperationsMixin as ModelMixin

class Order(ModelMixin('order'), models.Model):
    email = models.CharField(max_length=255, blank=True, null=True)
    trade_no = models.CharField(max_length=155, blank=True, null=True)
    order_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    address_id = models.IntegerField(blank=True, null=True)
    pay_status = models.CharField(max_length=155, blank=True, null=True)
    pay_time = models.DateTimeField(blank=True, null=True)
    ali_trade_no = models.CharField(max_length=255, blank=True, null=True)
    is_delete = models.PositiveIntegerField(blank=True, null=True)
    create_time = models.DateTimeField(blank=True, null=True)
    update_time = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'order'


class OrderGoods(models.Model):
    trade_no = models.CharField(max_length=255, blank=True, null=True)
    sku_id = models.CharField(max_length=255, blank=True, null=True)
    goods_num = models.IntegerField(blank=True, null=True)
    create_time = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'order_goods'


# 事件表：记录已发送的事件（用于重试+幂等）
class EventLog(models.Model):
    event_id = models.CharField(max_length=64, unique=True, verbose_name="事件ID")  # 格式：trade_no_事件类型
    event_type = models.CharField(max_length=32, verbose_name="事件类型")  # OrderCreated/StockDeducted等
    event_data = JSONField(verbose_name="事件数据")  # 存事件完整JSON
    status = models.CharField(max_length=10, choices=[("pending", "待消费"), ("success", "已消费"), ("fail", "消费失败")], verbose_name="事件状态")
    retry_count = models.IntegerField(default=0, verbose_name="重试次数")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "event_log"  # 单独Meta，不重复
        verbose_name = "事件日志"
        verbose_name_plural = verbose_name


# 本地事务表：保留一个，删除重复定义
class LocalTransactionRecord(models.Model):
    """本地事务记录表：标记订单本地事务是否成功，防重复执行"""
    transaction_id = models.CharField(
        max_length=64, 
        unique=True, 
        verbose_name="事务ID（用订单号trade_no）"
    )
    status = models.CharField(
        max_length=10, 
        choices=[("pending", "处理中"), ("success", "成功"), ("fail", "失败")], 
        default="pending", 
        verbose_name="事务状态"
    )
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        db_table = "local_transaction_record"
        verbose_name = "本地事务记录"
        verbose_name_plural = verbose_name