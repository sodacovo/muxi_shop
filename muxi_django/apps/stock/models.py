from django.db import models

# 库存事务表：记录扣减/补偿轨迹，用于Saga补偿
class StockTx(models.Model):
    TX_STATUS = (('deducted', '已扣减'), ('compensated', '已补偿'), ('failed', '失败'))
    order_trade_no = models.CharField(max_length=64, verbose_name="关联订单编号")
    goods_id = models.IntegerField(verbose_name="商品ID（关联Goods.id）") 
    qty = models.IntegerField(verbose_name="扣减/补偿数量")
    tx_status = models.CharField(
        max_length=16,
        choices=TX_STATUS,
        default='deducted',
        verbose_name="事务状态"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        db_table = 'stock_tx'
        verbose_name = "库存事务记录"