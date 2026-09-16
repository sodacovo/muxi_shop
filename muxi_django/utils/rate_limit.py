import time
from functools import wraps
from django.http import JsonResponse
from django_redis import get_redis_connection

def seckill_rate_limit(limit=3, period=10):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # 🌟 关键修复：适配request.user是字典的情况（JWT认证返回的字典）
            if hasattr(request, 'user') and isinstance(request.user, dict):
                # 从字典中获取认证状态和user_id（对应你的JWT返回格式）
                auth_status = request.user.get('status', False)
                user_data = request.user.get('data', {})
                user_id = user_data.get('user_id')
                # 已认证且有user_id：用user_id作为限流key
                if auth_status and user_id:
                    key = f"seckill:rate_limit:user:{user_id}"
                else:
                    # 未认证：用IP作为key
                    ip = request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get('REMOTE_ADDR')
                    key = f"seckill:rate_limit:ip:{ip}"
            else:
                # 兼容其他情况（如普通用户模型实例）
                if hasattr(request, 'user') and request.user.is_authenticated:
                    key = f"seckill:rate_limit:user:{request.user.id}"
                else:
                    ip = request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get('REMOTE_ADDR')
                    key = f"seckill:rate_limit:ip:{ip}"

            # 后续Redis逻辑不变
            redis_conn = get_redis_connection('seckill')
            current = redis_conn.incr(key)
            if current == 1:
                redis_conn.expire(key, period)

            if current > limit:
                return JsonResponse({
                    'status': 'fail',
                    'code': 429,
                    'message': f'请求过于频繁，请{period}秒后再试'
                })

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator