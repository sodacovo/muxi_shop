"""菜单：
成功了就是1001
失败了就是1002
其他不确定1003
"""
import json

from django.http import HttpResponse, JsonResponse

#  菜单的响应
class MenuResponse():
    @staticmethod
    def success(data):
        result = {"status": 1000, "data": data}
        return HttpResponse(json.dumps(result), content_type="application/json")


    @staticmethod
    def failed(data):
        result = {"status": 1001, "data": data}
        return HttpResponse(json.dumps(result), content_type="application/json")

    @staticmethod
    def other(data):
        result = {"status": 1002, "data": data}
        return HttpResponse(json.dumps(result), content_type="application/json")


# 商品的响应
class GoodsResponse():
    @staticmethod
    def success(data):
        result = {"status": 2000, "data": data}
        return HttpResponse(json.dumps(result), content_type="application/json")


    @staticmethod
    def failed(data):
        result = {"status": 2001, "data": data}
        return HttpResponse(json.dumps(result), content_type="application/json")

    @staticmethod
    def other(data):
        result = {"status": 2002, "data": data}
        return HttpResponse(json.dumps(result), content_type="application/json")


# 购物车的响应
class CartResponse():
    @staticmethod
    def success(data):
        result = {"status": 3000, "data": data}
        return JsonResponse(result, safe=False)


    @staticmethod
    def failed(data):
        result = {"status": 3001, "data": data}
        return JsonResponse(result, safe=False)

    @staticmethod
    def other(data):
        result = {"status": 3002, "data": data}
        return JsonResponse(result, safe=False)


class UserResponse():
    @staticmethod
    def success(data):
        result = {"status": 4000, "data": data}
        return JsonResponse(result, safe=False)

    @staticmethod
    def failed(data):
        result = {"status": 4001, "data": data}
        return JsonResponse(result, safe=False)

    @staticmethod
    def other(data):
        result = {"status": 4002, "data": data}
        return JsonResponse(result, safe=False)

# 评论的响应
class CommentResponse():
    @staticmethod
    def success(data):
        result = {"status": 5000, "data": data}
        return JsonResponse(result, safe=False)

    @staticmethod
    def failed(data):
        result = {"status": 5001, "data": data}
        return JsonResponse(result, safe=False)

    @staticmethod
    def other(data):
        result = {"status": 5002, "data": data}
        return JsonResponse(result, safe=False)

# 订单的响应
class OrderResponse():
    @staticmethod
    def success(data):
        result = {"status": 6000, "data": data}
        return JsonResponse(result, safe=False)

    @staticmethod
    def failed(data):
        result = {"status": 6001, "data": data}
        return JsonResponse(result, safe=False)

    @staticmethod
    def other(data):
        result = {"status": 6002, "data": data}
        return JsonResponse(result, safe=False)

# 地址的响应
class AddressResponse():

    @staticmethod
    def success(data):
        result = {"status": 7000, "data":data}
        return JsonResponse(result,safe=False)

    @staticmethod
    def failed(data):
        result = {"status": 7001, "data": data}
        return JsonResponse(result, safe=False)

    @staticmethod
    def other(data):
        result = {"status": 7002, "data": data}
        return JsonResponse(result, safe=False)

# 秒杀的响应（新增！状态码用8000系列，避免和其他模块冲突）
class SeckillResponse():
    @staticmethod
    def success(data):
        """成功：status=8000"""
        result = {"status": 8000, "data": data}
        return JsonResponse(result, safe=False)  # 用JsonResponse，和OrderResponse等一致

    @staticmethod
    def failed(data):
        """失败：status=8001（如Redis连接失败、数据库错误）"""
        result = {"status": 8001, "data": data}
        return JsonResponse(result, safe=False)

    @staticmethod
    def other(data):
        """其他情况：status=8002（如同步0个商品，不算失败但需提示）"""
        result = {"status": 8002, "data": data}
        return JsonResponse(result, safe=False)