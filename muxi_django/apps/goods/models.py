# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
import decimal
import json
from decimal import Decimal
import logging
from django.db import models
from django_redis import get_redis_connection
from django.conf import settings
from functools import lru_cache  # 新增这行，测试Redis三大坑用的
from django_prometheus.models import ExportModelOperationsMixin as ModelMixin, Counter
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)

# 新增：用 lru_cache 封装 Counter，确保只初始化一次（单例）测试Redis三大坑用的
@lru_cache(maxsize=None)
def get_goods_creation_counter():
    # 这里完全复制你原来的 Counter 定义，一字不改
    return Counter(
        'django_model_goods_creations_total',
        'Total number of Goods model insert operations'
    )

class Goods(ModelMixin('goods'), models.Model):
    id = models.BigAutoField(primary_key=True)
    type_id = models.IntegerField(blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    sku_id = models.CharField(max_length=255, blank=True, null=True)
    target_url = models.CharField(max_length=255, blank=True, null=True)
    jd_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    p_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    image = models.CharField(max_length=255, blank=True, null=True)
    shop_name = models.CharField(max_length=255, blank=True, null=True)
    shop_id = models.IntegerField(blank=True, null=True)
    spu_id = models.CharField(max_length=255, blank=True, null=True)
    mk_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    vender_id = models.IntegerField(blank=True, null=True)
    find = models.IntegerField(blank=True, null=True)
    create_time = models.DateTimeField(blank=True, null=True)
    seckill_stock = models.IntegerField(default=50)
    seckill_price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    seckill_start_time = models.DateTimeField(null=True)
    seckill_end_time = models.DateTimeField(null=True)
    is_seckill = models.BooleanField(default=False)


    def __str__(self):
        result = {}
        result['type_id'] = self.type_id
        result['name'] = self.name
        result['sku_id'] = self.sku_id
        result['target_url'] = self.target_url
        result['jd_price'] = self.jd_price
        result['p_price'] = self.p_price
        result['image'] = settings.IMAGE_URL + self.image if self.image else ""
        result['shop_name'] = self.shop_name
        result['shop_id'] = self.shop_id
        result['spu_id'] = self.spu_id
        result['mk_price'] = self.mk_price
        result['vender_id'] = self.vender_id
        result['find'] = self.find
        result['seckill_stock'] = self.seckill_stock
        result['seckill_price'] = self.seckill_price
        result['seckill_start_time'] = self.seckill_start_time.strftime("%Y-%m-%d %H:%M:%S") if self.seckill_start_time else None
        result['seckill_end_time'] = self.seckill_end_time.strftime("%Y-%m-%d %H:%M:%S") if self.seckill_end_time else None
        return json.dumps(result, cls=DecimalEncoder, ensure_ascii=False)
    # 定义商品新增计数器，指标名和 ModelMixin 生成的一致
    goods_creation_counter = Counter(
        'django_model_goods_creations_total',  # 指标名，固定不变
        'Total number of Goods model insert operations'  # 指标描述（可自定义）
    )
    # ------------------------------------------------------

    def save(self, *args, **kwargs):
        '''重写save方法，实现新增、编辑商品时自动同步库存到Redis'''
        # 保存前记录原始 id（None 表示新增）
        original_id = self.id
        super().save(*args, **kwargs)
        
        # 保存后判断：原始 id 为 None → 新增商品
        is_new = original_id is None  # 改用这个判断
        if is_new:
            self.goods_creation_counter.inc()  # 计数器+1
        # 只处理秒杀商品的库存同步
        if self.is_seckill:
            try:
                redis_conn = get_redis_connection("seckill")
                stock_key = f"seckill:stock:{self.id}"
                redis_conn.set(stock_key, self.seckill_stock)
                logger.info(
                    f"商品[{self.id}:{self.name}]库存同步到Redis成功"
                    f"数据库seckill_stock={self.seckill_stock},"
                    f"Redis键={stock_key}, 值={self.seckill_stock}"
                )
            except Exception as e:
                logger.error(
                    f"商品[{self.id}:{self.name}]库存同步到Redis失败：{str(e)}",
                    exc_info=True
                )
        
            
            
    class Meta:
        managed = True  # 改为True，允许Django同步数据库字段
        db_table = 'goods'

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return float(o)
        return super().default(o)

