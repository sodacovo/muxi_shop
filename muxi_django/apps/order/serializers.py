from rest_framework import serializers

from goods.models import Goods
from order.models import OrderGoods, Order
from django.conf import settings


class OrderGoodsSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderGoods
        fields = "__all__"


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = "__all__"


class OrderManyGoodsSerializer(serializers.Serializer):
    email = serializers.CharField()
    trade_no = serializers.CharField()
    order_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    address_id = serializers.IntegerField()
    pay_status = serializers.CharField()
    pay_time = serializers.DateTimeField()
    ali_trade_no = serializers.CharField()
    is_delete = serializers.IntegerField()
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S")

    order_info = serializers.SerializerMethodField()

    def get_order_info(self, obj):
        order_goods_list = OrderGoods.objects.filter(trade_no=obj.trade_no).all()
        ser = OrderGoodsSerializer(order_goods_list, many=True).data

        for i in ser:
            sku_id = i.get("sku_id")


            # 修复商品查询：移除status条件（Goods模型没有该字段）
            goods_data = Goods.objects.filter(id=sku_id, is_seckill=True).first()

            # 容错优化：即使非秒杀商品，也尝试查普通商品
            if not goods_data:
                goods_data = Goods.objects.filter(id=sku_id).first()

            # 修复：秒杀订单已支付，即使商品信息缺失也显示合理内容
            if not goods_data:
                # 从订单金额反推秒杀价，避免显示0元
                order_amount = obj.order_amount  # 订单总金额（秒杀价）
                i["name"] = "秒杀商品（已下单）"  # 替换“商品已下架”
                i["jd_price"] = float(order_amount)  # 显示订单中的秒杀价
                i["image"] = f"{settings.IMAGE_URL}default-seckill.png"  # 秒杀默认图
                i["shop_name"] = "秒杀专区"
                continue

            # 正常商品赋值
            i["jd_price"] = goods_data.seckill_price if goods_data.is_seckill else goods_data.jd_price
            i["image"] = f"{settings.IMAGE_URL}{goods_data.image}" if goods_data.image else f"{settings.IMAGE_URL}default-seckill.png"
            i["name"] = goods_data.name or "秒杀商品"
            i["shop_name"] = goods_data.shop_name or "秒杀专区"

            if "p_price" in i:
                del i["p_price"]

        return ser
