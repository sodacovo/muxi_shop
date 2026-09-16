from django.utils import timezone
from rest_framework import serializers
from goods.models import Goods
from django.conf import settings


class GoodsSerializer(serializers.ModelSerializer):
    # 1. 显式声明自定义字段的类型（关键！）
    # - image：用SerializerMethodField，对应get_image方法
    # - is_seckill_valid：用SerializerMethodField，对应get_is_seckill_valid方法
    # - create_time：用DateTimeField，自定义时间格式
    image = serializers.SerializerMethodField()
    is_seckill_valid = serializers.SerializerMethodField()  # 新增：声明自定义字段类型
    create_time = serializers.DateTimeField("%Y-%m-%d %H:%M:%S")

    # 2. 自定义字段的逻辑实现
    def get_image(self, obj):
        # 拼接完整图片URL（从settings获取基础URL）
        return settings.IMAGE_URL + obj.image

    def get_is_seckill_valid(self, obj):
        # 判断商品是否在秒杀有效期内
        if not obj.is_seckill:  # 先判断是否是秒杀商品
            return False
        now = timezone.now()
        # 再判断当前时间是否在 [开始时间, 结束时间] 之间
        return obj.seckill_start_time <= now <= obj.seckill_end_time

    class Meta:
        model = Goods  # 关联的模型
        fields = [
            # 基础商品字段（前端展示用）
            'id', 'name', 'image', 'jd_price',  # jd_price 作为“原价”展示
            'create_time',  # 补充：把声明的create_time加入fields
            # 秒杀相关字段（前端判断是否显示“秒杀”标签用）
            'is_seckill', 'seckill_price', 'seckill_start_time', 'seckill_end_time',
            'is_seckill_valid'  # 补充：把自定义的“秒杀有效性”字段加入fields
        ]