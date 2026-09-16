import datetime

import jwt
from rest_framework.authentication import BaseAuthentication

from django.conf import settings


def create_token(payload, timeout=30*24*60):  # 30天有效期
    # payload 必须包含 "username"（与视图中 user_data.get("username") 对应）
    # 示例：payload = {"username": "4@qq.com", ...}
    payload['exp'] = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=timeout)
    return jwt.encode(
        payload,
        key=settings.SECRET_KEY,
        algorithm='HS256',
        headers={'alg': 'HS256', 'typ': 'JWT'}
    )

def get_payload(token):
    result = {"status": False, "data": None, "error": None}  # 初始化结果字典
    try:
        # 解析 Token
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        result["status"] = True  # 解析成功
        result["data"] = payload  # 存储解析后的 payload（包含 user_id 等）
    except jwt.exceptions.DecodeError:
        result['error'] = 'token认证失败'
    except jwt.exceptions.ExpiredSignatureError:
        result['error'] = 'token已失效'
    except jwt.exceptions.InvalidTokenError:
        result['error'] = '无效的token'
    # 关键修复：确保无论如何都返回结果字典（之前遗漏了这行！）
    return result  # 必须返回，否则调用时会得到 None

# 用户在url中进行token的参数配置
class JWTQueryParamAuthentication(BaseAuthentication):
    def authenticate(self, request):
        # 从url中拿到token
        token = request.GET.get("token")
        result_payload = get_payload(token)
        return (result_payload, token)


class JWTHeaderAuthentication(BaseAuthentication):
    def authenticate(self, request):
        if request.method == "OPTIONS":
            return None
        # print(request.META)
        # 从url中拿到token
        # token = request.META.get("HTTP_TOKEN") # postman中获取
        # 从正确的头中获取（对应前端的 Authorization）
        auth = request.META.get("HTTP_AUTHORIZATION", "")
        print("收到的认证头:", auth)

        # 检查 Token 格式（必须以 "Token " 开头）
        if not auth.startswith("Token "):
            print("Token 格式错误（未以 'Token ' 开头）")
            return None  # 格式错误，视为未认证

        # 提取 Token（去掉 "Token " 前缀）
        token = auth[6:]
        print("提取的 Token:", token)

        # 解析 Token（修复后 get_payload 会返回字典）
        result = get_payload(token)
        print("Token 解析结果:", result)  # 现在会显示完整的 result 字典

        # 若解析失败（status=False），返回 None 让视图处理
        if not result["status"]:
            return (result, token)  # 仍返回结果，让视图判断错误信息

        # 解析成功，返回 (result, token)
        return (result, token)
