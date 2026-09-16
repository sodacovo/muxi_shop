from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from rest_framework.views import APIView
# 新增：导入AnonymousUser，用于判断未登录用户
from django.contrib.auth.models import AnonymousUser

from cart.models import ShoppingCart
from cart.serializers import CartSerializer, CartDetailSerializer
from utils import ResponseMessage


# Create your views here.
class CartAPIView(APIView):
    #  我们的购物车应该时登录之后才能访问的
    #  @todo  后续补充登录权限验证

    def post(self,request):
        # 🔥 第一步：兼容未登录用户（核心修复）
        if isinstance(request.user, AnonymousUser):
            return ResponseMessage.CartResponse.failed("请先登录后操作购物车")
        
        # 登录用户：判断是否是字典 + status是否有效
        if not isinstance(request.user, dict) or not request.user.get("status"):
            return ResponseMessage.CartResponse.failed("用户登录状态异常，请重新登录")

        request_data = request.data
        print("=== 前端传递的原始参数 ===")
        print(request_data)
        
        print(request.user)
        email = request.user.get("data", {}).get("username")
        # 兜底：确保email存在
        if not email:
            return ResponseMessage.CartResponse.failed("用户信息异常，请重新登录")
            
        request_data["email"]=email
        print("=== 补充 email 后的参数 ===")
        print(request_data)
        print("=== 参数类型 ===")
        print(f"sku_id 类型：{type(request_data.get('sku_id'))}")
        print(f"nums 类型：{type(request_data.get('nums'))}")
        print(f"email 类型：{type(request_data.get('email'))}")
        sku_id = request_data.get("sku_id")
        nums = request_data.get("nums")
        is_delete = request_data.get("is_delete")
        
        # 校验必要参数
        if not sku_id or nums is None:
            return ResponseMessage.CartResponse.failed("sku_id和数量不能为空")
            
        # 判断一下数据是否存在，如果存在就更新，如果不存在那就插入
        data_exists = ShoppingCart.objects.filter(
                                    email=email,
                                    is_delete=0,
                                    sku_id=sku_id
                                )

        print(data_exists.exists())
        # 存在就更新
        if data_exists.exists():
            exists_cart_data = data_exists.get(
                                        email=email,
                                        is_delete=0,
                                        sku_id=sku_id
                                    )
            if is_delete == 0:
                new_nums = nums + exists_cart_data.nums
                request_data["nums"] = new_nums
            elif is_delete == 1:
                request_data["nums"] = exists_cart_data.nums
            # 反序列化
            cart_ser = CartSerializer(data=request_data)
            cart_ser.is_valid(raise_exception=True)
            # 更新
            ShoppingCart.objects.filter(
                                    email=email,
                                    is_delete=0,
                                    sku_id=sku_id
                                ).update(**cart_ser.data)
            if is_delete == 0:
                return ResponseMessage.CartResponse.success("更新成功")
            elif is_delete == 1:
                return ResponseMessage.CartResponse.success("删除成功")
        else:
            #  这里是数据插入逻辑
            print("****",request_data)
            cart_ser = CartSerializer(data=request_data)
            cart_ser.is_valid(raise_exception=True)
            print("=======",cart_ser)
            ShoppingCart.objects.create(**cart_ser.data)
            return ResponseMessage.CartResponse.success("插入成功")

    def get(self, request):
        # 🔥 修复：兼容未登录用户
        if isinstance(request.user, AnonymousUser):
            return ResponseMessage.CartResponse.failed("请先登录后查看购物车")
        
        if not isinstance(request.user, dict) or not request.user.get("status"):
            return ResponseMessage.CartResponse.failed("用户登录状态异常，请重新登录")
            
        email = request.GET.get("email")
        # 兜底：如果GET参数没有email，从user字典取
        if not email:
            email = request.user.get("data", {}).get("username")
            if not email:
                return ResponseMessage.CartResponse.failed("用户信息异常，请重新登录")
                
        cart_result = ShoppingCart.objects.filter(email=email,is_delete=0)
        cart_ser = CartSerializer(instance=cart_result,many=True)
        return ResponseMessage.CartResponse.success(cart_ser.data)

# 使用序列化器，达到多表关联查询的目的
class CartDetailAPIView(APIView):
    def post(self,request):
        # 🔥 修复：兼容未登录用户
        if isinstance(request.user, AnonymousUser):
            return ResponseMessage.CartResponse.failed("请先登录后查看购物车详情")
        
        if not isinstance(request.user, dict) or not request.user.get("status"):
            return ResponseMessage.CartResponse.failed("用户登录状态异常，请重新登录")
            
        email = request.user.get("data", {}).get("username")
        if not email:
            return ResponseMessage.CartResponse.failed("用户信息异常，请重新登录")
            
        filters = {
            "email":email,
            "is_delete":0
        }
        shopping_cart = ShoppingCart.objects.filter(**filters).all()
        db_data = CartDetailSerializer(shopping_cart,many=True)
        return ResponseMessage.CartResponse.success(db_data.data)

class UpdateCartNumAPIView(APIView):
    def post(self,request):
        # 🔥 修复：兼容未登录用户
        if isinstance(request.user, AnonymousUser):
            return ResponseMessage.CartResponse.failed("请先登录后修改购物车数量")
        
        if not isinstance(request.user, dict) or not request.user.get("status"):
            return ResponseMessage.CartResponse.failed("用户登录状态异常，请重新登录")
            
        print(request.user)
        email = request.user.get("data", {}).get("username")
        if not email:
            return ResponseMessage.CartResponse.failed("用户信息异常，请重新登录")
            
        request_data = request.data
        # 校验必要参数
        if not request_data.get("sku_id") or request_data.get("nums") is None:
            return ResponseMessage.CartResponse.failed("sku_id和数量不能为空")
            
        ShoppingCart.objects.filter(
            email=email,
            sku_id=request_data["sku_id"],
            is_delete=0
        ).update(nums=request_data["nums"])
        return ResponseMessage.CartResponse.success("ok")

# 获取购物车商品数量的接口
class CartCountAPIView(APIView):
    def post(self, request):
        # 🔥 修复：兼容未登录用户
        if isinstance(request.user, AnonymousUser):
            return ResponseMessage.CartResponse.failed("请先登录后查看购物车数量")
        
        if not isinstance(request.user, dict) or not request.user.get("status"):
            return ResponseMessage.CartResponse.failed("用户登录状态异常，请重新登录")
            
        print(request.user)
        from django.db.models import Sum
        email = request.user.get("data", {}).get("username")
        if not email:
            return ResponseMessage.CartResponse.failed("用户信息异常，请重新登录")
            
        user_cart_count = ShoppingCart.objects.filter(
                            email=email,
                            is_delete=0
                        ).aggregate(Sum("nums"))
        print(user_cart_count)
        return ResponseMessage.CartResponse.success(user_cart_count)

class DeleteCartGoodsAPIView(APIView):
    def post(self,request):
        # 🔥 修复：兼容未登录用户
        if isinstance(request.user, AnonymousUser):
            return ResponseMessage.CartResponse.failed("请先登录后删除购物车商品")
        
        if not isinstance(request.user, dict) or not request.user.get("status"):
            return ResponseMessage.CartResponse.failed("用户登录状态异常，请重新登录")
            
        print(request.user)
        email = request.user.get("data", {}).get("username")
        if not email:
            return ResponseMessage.CartResponse.failed("用户信息异常，请重新登录")
            
        request_data = request.data
        # 校验必要参数
        if not request_data:
            return ResponseMessage.CartResponse.failed("请选择要删除的商品")
            
        ShoppingCart.objects.filter(
            email=email,
            sku_id__in=request_data,
            is_delete=0
        ).update(is_delete=1)
        return ResponseMessage.CartResponse.success("ok")