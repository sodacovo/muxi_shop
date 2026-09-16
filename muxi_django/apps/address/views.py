from django.http import JsonResponse
from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import CreateModelMixin
from address.models import UserAddress
from address.serializers import AddressSerializer
from utils import ResponseMessage
from utils.jwt_auth import JWTHeaderAuthentication, JWTQueryParamAuthentication


# 关键修改：继承 GenericViewSet（而非 ViewSet）
class AddressViewSet(GenericViewSet):
    queryset = UserAddress.objects  # GenericViewSet 要求必须定义 queryset
    serializer_class = AddressSerializer  # 必须定义序列化器类
    authentication_classes = [JWTHeaderAuthentication, JWTQueryParamAuthentication]

    # 1. 获取地址列表
    def list(self, request):
        if not request.user.get("status"):
            return JsonResponse(request.user, safe=False)

        email = request.user.get("data").get("username")
        addresses = self.queryset.filter(email=email)

        serializer = self.get_serializer(addresses, many=True)
        return ResponseMessage.AddressResponse.success(serializer.data)

    # 2. 保留原有的 create 方法（处理 POST /address/ 新增地址）
    def create(self, request):
        if not request.user.get("status"):
            return JsonResponse(request.user, safe=False)

        email = request.user.get("data").get("username")
        request_data = request.data.copy()

        # 处理默认地址逻辑（新增时设为默认，其他地址改为非默认）
        if request_data.get('default', False):
            self.queryset.filter(email=email).update(default=0)
            request_data['default'] = 1
        else:
            request_data['default'] = 0

        request_data['email'] = email  # 绑定当前用户
        serializer = self.serializer_class(data=request_data)

        if serializer.is_valid():
            serializer.save()
            return ResponseMessage.AddressResponse.success('地址创建成功')
        return ResponseMessage.AddressResponse.failed(serializer.errors)

    # 3. 保留原有的 edit/delete_address/set_default 方法（无需修改）
    def edit(self, request):
        if not request.user.get("status"):
            return JsonResponse(request.user, safe=False)

        email = request.user.get("data").get("username")
        address_id = request.data.get("id")
        if not address_id:
            return ResponseMessage.AddressResponse.failed("缺少地址ID")

        try:
            address = self.queryset.get(id=address_id, email=email)
        except UserAddress.DoesNotExist:
            return ResponseMessage.AddressResponse.failed("地址不存在或无权编辑")

        request_data = request.data.copy()
        if request_data.get('default', False):
            self.queryset.filter(email=email).update(default=0)
            request_data['default'] = 1
        else:
            request_data['default'] = 0

        serializer = self.serializer_class(address, data=request_data)
        if serializer.is_valid():
            serializer.save()
            return ResponseMessage.AddressResponse.success('地址编辑成功')
        return ResponseMessage.AddressResponse.failed(serializer.errors)

    def delete_address(self, request):
        if not request.user.get("status"):
            return JsonResponse(request.user, safe=False)

        email = request.user.get("data").get("username")
        address_id = request.data.get("id")
        if not address_id:
            return ResponseMessage.AddressResponse.failed("缺少地址ID")

        try:
            address = self.queryset.get(id=address_id, email=email)
        except UserAddress.DoesNotExist:
            return ResponseMessage.AddressResponse.failed("地址不存在或无权删除")

        address.delete()
        return ResponseMessage.AddressResponse.success('地址删除成功')

    def set_default(self, request):
        if not request.user.get("status"):
            return JsonResponse(request.user, safe=False)

        email = request.user.get("data").get("username")
        address_id = request.data.get("id")
        if not address_id:
            return ResponseMessage.AddressResponse.failed("缺少地址ID")

        try:
            address = self.queryset.get(id=address_id, email=email)
        except UserAddress.DoesNotExist:
            return ResponseMessage.AddressResponse.failed("地址不存在或无权操作")

        self.queryset.filter(email=email).update(default=0)
        address.default = 1
        address.save()
        return ResponseMessage.AddressResponse.success('默认地址设置成功')


# 2. 处理「获取所有地址列表」（保持不变，或合并到 ViewSet 中）
# class AddressListGenericAPIView(GenericAPIView, ListModelMixin):
#     queryset = UserAddress.objects
#     serializer_class = AddressSerializer
#     authentication_classes = [JWTQueryParamAuthentication, ]
#
#     def get(self, request):
#         if not request.user.get("status"):
#             return JsonResponse(request.user, safe=False)
#
#         # 过滤当前用户的地址
#         email = request.user.get("data").get("username")
#         self.queryset = self.queryset.filter(email=email)
#         return self.list(request)

"""
在 AddressListGenericAPIView 的 get 方法中添加认证结果判断（而非直接在 jwt_auth.py 中处理响应），核心好处是遵循 Django REST Framework（DRF）的认证流程设计，实现 “认证逻辑” 与 “业务响应逻辑” 的解耦，同时让代码更灵活、可维护。具体可以从以下 3 个维度理解：
1. 符合 DRF 认证组件的 “职责边界” 设计
DRF 的 BaseAuthentication（你自定义的 JWTQueryParamAuthentication 继承自它）的核心职责是 “验证身份”，而非 “返回业务响应”。它的 authenticate 方法只负责：

校验 Token 是否有效（如格式、过期时间）；
若有效：返回 (user, auth) 元组（user 存认证通过的用户信息，auth 存额外认证数据，如 Token）；
若无效：返回 None（交由后续权限组件处理）或直接抛出 AuthenticationFailed 异常。

你当前在 jwt_auth.py 中仅返回 (result_payload, token)（不主动抛异常 / 返回响应），再在视图 get 方法中判断 request.user.get("status")，正是贴合了这个职责边界：

JWTQueryParamAuthentication 只做 “Token 校验”，输出 “校验结果”（result_payload 包含 status/data/error）；
视图层根据 “校验结果” 决定返回什么响应（如 Token 无效则返回错误，有效则返回地址列表）。

如果反过来在 jwt_auth.py 中直接返回响应（比如用 JsonResponse），会打破 DRF 的流程链：认证组件本应只输出 “校验状态”，却直接接管了 “响应生成”，导致后续视图逻辑无法执行，也不符合 DRF 的组件化设计思想。
2. 让 “认证失败的响应” 更灵活，适配业务场景
不同的视图可能需要不同的 “认证失败响应格式”：

比如 AddressListGenericAPIView 需要返回 {"status": false, "error": "token已失效"}；
若后续有一个 “订单支付视图”，可能需要返回 {"code": 401, "msg": "身份过期，请重新登录", "data": {}}。

如果在 jwt_auth.py 中写死响应（比如固定返回 JsonResponse({"error": "token失效"})），所有使用该认证的视图都会被迫使用同一种响应格式，无法适配不同业务的需求。

而现在的写法，将 “响应生成” 放在视图层：

视图可以根据自身业务，自定义认证失败的响应内容（如字段名、错误描述、状态码）；
比如你当前代码中，if not request.user.get("status") 时返回 JsonResponse(request.user, safe=False)，直接复用了 get_payload 生成的 result_payload（包含 status/error），后续若需修改格式，只需在视图中调整，无需改动认证组件。
3. 便于后续扩展 “权限控制”
实际项目中，“认证通过” 不代表 “有权访问资源”（比如：用户 A 只能访问自己的地址，不能访问用户 B 的地址）。DRF 中，认证（Authentication）负责 “确认你是谁”，权限（Permission）负责 “确认你能做什么”。

你当前的写法为后续添加 “权限控制” 预留了空间：

认证组件先校验 Token 有效性（拿到 request.user 中的用户信息，如 user_id）；
视图层或权限组件可以基于 request.user["data"]["user_id"] 做进一步权限判断（比如：查询地址时，只返回当前用户的地址）；
若权限不通过，还能在视图层返回自定义的权限错误响应（与认证错误响应区分开）。

如果在 jwt_auth.py 中直接返回响应，会跳过后续的权限校验流程，无法实现 “认证 + 权限” 的联动。
"""