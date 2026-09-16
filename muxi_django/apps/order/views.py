from datetime import datetime
from address.models import UserAddress
from django.http import JsonResponse
from rest_framework.generics import GenericAPIView
from django.utils import timezone
from cart.models import ShoppingCart
from order.models import OrderGoods, Order
from order.serializers import OrderGoodsSerializer, OrderSerializer, OrderManyGoodsSerializer
from utils import ResponseMessage
from django.db import transaction

class OrderGoodsGenericAPIView(GenericAPIView):
    queryset = OrderGoods.objects
    serializer_class = OrderGoodsSerializer
    lookup_field = "trade_no"

    def post(self, request):
        print(request.data)
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save()
        return JsonResponse("ok", safe=False)

    def get(self, request, trade_no):
        trade_no = trade_no.strip('/')  
        if not request.user.get("status"):
            return JsonResponse(request.user, safe=False)
        email = request.user.get("data").get("username")
        db_result = Order.objects.filter(
            email=email, is_delete=0, trade_no=trade_no
        ).first()
        if not db_result:
            return ResponseMessage.OrderResponse.failed("订单不存在或已删除")

        order_ser = OrderManyGoodsSerializer(instance=db_result)
        order_data = order_ser.data

        # 修复地址查询：移除is_delete条件
        if db_result.address_id:
            address = UserAddress.objects.filter(id=db_result.address_id).first()
        else:
            address = UserAddress.objects.filter(email=email, default=1).first()

        order_data["address"] = {
            "signer_name": address.signer_name if address else "",
            "telphone": address.telphone if address else "",
            "district": address.district if address else "",
            "signer_address": address.signer_address if address else ""
        } if address else {}

        return ResponseMessage.OrderResponse.success(order_data)


class OrderGenericAPIView(GenericAPIView):
    queryset = Order.objects
    serializer_class = OrderSerializer

    def post(self, request):
        # print("\n" + "="*50)
        # print("=== 前端提交的订单数据 ===")
        # print(f"request.data 内容：{request.data}")
        # print(f"是否包含'trade'字段：{'trade' in request.data}")
        # print(f"是否包含'goods'字段：{'goods' in request.data}")
        # print("="*50)

        # 2. 验证用户身份
        if not request.user.get("status"):
            # print(f"\n=== 用户认证失败 ===")
            # print(f"失败原因：{request.user}")
            return JsonResponse(request.user, safe=False)

        # 3. 获取用户信息和生成订单号
        email = request.user.get("data").get("username")
        import time
        trade_no = str(int(time.time() * 1000))  # 字符串类型订单号
        
        # print("\n" + "="*50)
        # print(f"=== 订单基础信息 ===")
        # print(f"生成的trade_no：{trade_no}")
        # print(f"trade_no类型：{type(trade_no)}")  # 确保是字符串
        # print(f"当前下单用户email：{email}")
        # print("="*50)

        # 4. 提取订单数据和商品数据
        request_data = request.data
        trade_data = request_data.get("trade", {})
        goods_data = request_data.get("goods", [])

        # 5. 验证订单数据和商品数据不为空
        # print("\n" + "="*50)
        # print(f"=== 订单数据有效性检查 ===")
        # print(f"trade_data（订单信息）：{trade_data}")
        # print(f"goods_data（商品列表）：{goods_data}")
        # print(f"trade_data是否为空：{bool(trade_data)}")
        # print(f"goods_data是否为空：{bool(goods_data)}")
        # print("="*50)

        if not trade_data or not goods_data:
            print(f"\n=== 订单创建被拦截：数据不完整 ===")
            return ResponseMessage.OrderResponse.failed("订单数据或商品数据缺失")

        # 6. 补充订单必要字段
        current_time = timezone.now()
        trade_data.update({
            "trade_no": trade_no,
            "email": email,
            "pay_status": "0",  # 待支付状态
            "is_delete": 0,     # 未删除
            "create_time": current_time,
            "update_time": current_time
        })

        # 7. 打印待保存的订单数据
        print("\n" + "="*50)
        print(f"=== 待保存的订单完整数据 ===")
        print(trade_data)
        print("="*50)

        # 8. 序列化器验证与订单保存（新增事务管理）
        serializer = self.get_serializer(data=trade_data)
        try:
            # 新增：开启数据库事务，确保订单和订单项要么一起成功，要么一起失败
            with transaction.atomic():
                # 验证订单数据
                serializer.is_valid(raise_exception=True)
                # print("\n=== 序列化器验证通过 ===")
                
                # 保存订单到数据库
                serializer.save()
                print(f"=== 订单保存成功！ID：{serializer.instance.id} ===")
                print(f"数据库中trade_no：{serializer.instance.trade_no}")

                # 9. 保存订单项（仅在订单保存成功后执行）
                print("\n" + "="*50)
                print(f"=== 开始保存订单项（共{len(goods_data)}个） ===")
                for idx, data in enumerate(goods_data, 1):
                    goods_order_data = {
                        "trade_no": trade_no,
                        "sku_id": data.get("sku_id"),
                        "goods_num": data.get("nums") or data.get("goods_nums", 1),
                        "create_time": current_time
                    }
                    print(f"订单项{idx}数据：{goods_order_data}")
                    print(f"  sku_id是否存在：{bool(goods_order_data['sku_id'])}")
                    print(f"  goods_num是否有效：{goods_order_data['goods_num'] > 0}")

                    if not goods_order_data["sku_id"]:
                        print(f"订单项{idx}：跳过（无sku_id）")
                        continue
                    
                    try:
                        # 保存订单项到数据库
                        OrderGoods.objects.create(** goods_order_data)
                        print(f"  订单项{idx}：保存成功（sku_id={goods_order_data['sku_id']}）")

                        # 修复：仅当订单项保存成功后，才清空购物车（移到try块内部）
                        ShoppingCart.objects.filter(
                            sku_id=goods_order_data["sku_id"],
                            email=email,
                            is_delete=0
                        ).update(is_delete=1)
                        print(f"  订单项{idx}：对应的购物车商品已清空")

                    except Exception as e:
                        print(f"  订单项{idx}：保存失败！错误：{str(e)}")
                        # 订单项保存失败，触发事务回滚（订单也会被撤销）
                        raise  # 向上抛异常，让外层事务捕获并回滚

                print(f"=== 所有订单项保存完成 ===")
                print("="*50)

            # 10. 订单创建成功：返回成功响应（事务内无异常才会执行到这里）
            return ResponseMessage.OrderResponse.success(serializer.data)

        except Exception as e:
            # 11. 捕获异常：订单/订单项保存失败（事务已自动回滚）
            print("\n" + "="*50)
            print(f"=== 订单创建失败（事务已回滚） ===")
            print(f"错误原因：{str(e)}")  # 关键：打印具体错误
            print("="*50)
            return ResponseMessage.OrderResponse.failed(f"创建订单失败：{str(e)}")

    def get(self, request):
        # （get方法逻辑不变，省略）
        if not request.user.get("status"):
            return JsonResponse(request.user, safe=False)

        email = request.user.get("data").get("username")
        print(f"\n=== 查询订单的用户email：{email} ===")
        pay_status = request.GET.get("pay_status", "-1")

        if pay_status == "-1":
            db_result = Order.objects.filter(
                email=email, is_delete=0
            ).all().order_by("-create_time")
        else:
            db_result = Order.objects.filter(
                email=email, is_delete=0, pay_status=pay_status
            ).all().order_by("-create_time")

        order_list = []
        for order in db_result:
            order_data = OrderManyGoodsSerializer(order).data

            if order.address_id:
                address = UserAddress.objects.filter(id=order.address_id).first()
            else:
                address = UserAddress.objects.filter(email=email, default=1).first()

            order_data["address"] = {
                "signer_name": address.signer_name if address else "未填写",
                "telphone": address.telphone if address else "",
                "district": address.district if address else "",
                "signer_address": address.signer_address if address else ""
            } if address else {
                "signer_name": "未填写",
                "telphone": "",
                "district": "",
                "signer_address": ""
            }

            order_list.append(order_data)

        return ResponseMessage.OrderResponse.success(order_list)


class OrderDetailGenericAPIView(GenericAPIView):
    queryset = Order.objects
    serializer_class = OrderSerializer

    def post(self, request):
        # print(f"\n=== 订单更新接口被调用 ===")
        # print(f"请求数据：{request.data}")
        # print(f"调用IP：{request.META.get('REMOTE_ADDR')}")
        # print(f"用户：{request.user.get('data', {}).get('username', '未知')}")
        if not request.user.get("status"):
            return JsonResponse(request.user, safe=False)
        # 这里是加了修改
        trade_no = request.data.get("trade_no", "").strip('/')
        update_data = request.data
        update_data["update_time"] = timezone.now()
        allowed_fields = ["address_id", "pay_status", "is_delete", "ali_trade_no", "pay_time"]
        update_data = {k: v for k, v in update_data.items() if k in allowed_fields}

        if not trade_no or not update_data:
            return ResponseMessage.OrderResponse.failed("订单号或更新数据缺失")

        self.get_queryset().filter(trade_no=trade_no).update(**update_data)
        return ResponseMessage.OrderResponse.success("订单更新成功")
