from rest_framework import serializers

from cart.models import ShoppingCart
from goods.models import Goods
from goods.serializers import GoodsSerializer


class CartSerializer(serializers.ModelSerializer):
    sku_id = serializers.CharField(required=True)
    email = serializers.CharField(required=True)

    class Meta:
        model = ShoppingCart
        fields = "__all__"


class CartDetailSerializer(serializers.Serializer):
    sku_id = serializers.CharField(required=True)
    email = serializers.CharField(required=True)
    nums = serializers.IntegerField()
    is_delete = serializers.IntegerField()
    goods = serializers.SerializerMethodField()

    def get_goods(self, obj):
        try:
            # 🌟 显式将 sku_id 转为整数（避免字符串/数字不匹配）
            goods_id = int(obj.sku_id)
            # 🌟 打印日志，查看实际查询的 ID 和结果（调试用）
            print(f"查询商品 ID：{goods_id}")
            goods_obj = Goods.objects.filter(id=goods_id).first()

            if goods_obj:
                print(f"查到商品：{goods_obj.name}，价格：{goods_obj.p_price}")
                return GoodsSerializer(goods_obj).data
            else:
                print(f"未查到 ID 为 {goods_id} 的商品")
                return {"name": "商品已下架", "p_price": 0, "image": ""}
        except ValueError:
            # 处理 sku_id 无法转为整数的情况（比如存储了非数字字符串）
            print(f"无效的商品 ID：{obj.sku_id}（不是数字）")
            return {"name": "商品已下架", "p_price": 0, "image": ""}

        # 正常序列化商品数据
        ser = GoodsSerializer(goods_obj).data
        return ser