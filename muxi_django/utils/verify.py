import random
from django_redis import get_redis_connection
from django.conf import settings


def generate_code(length=4):
    '''生成随机验证码（1-4位数字）'''
    length = max(1, min(4, length))
    return ''.join(random.sample('0123456789', length))


def save_verify_code(key, code):
    '''存储验证码到Redis（sms数据库，300秒过期）'''
    try:
        redis_conn = get_redis_connection('sms')
        expire_time = getattr(settings, 'REDIS_TIMEOUT', 300)
        redis_conn.setex(
            name=key,
            time=expire_time,
            value=code
        )
        print(f"=== 验证码存储成功 ===")
        print(f"键名：{key}，存储值：{code}（类型：{type(code)}）")
        print(f"过期时间：{expire_time}秒，当前TTL：{redis_conn.ttl(key)}秒")
        return True
    except Exception as e:
        print(f"=== 验证码存储失败 ===")
        print(f"错误原因：{str(e)}")
        return False


def check_verify_code(key, code):
    '''检验验证码并删除（兼容bytes和str类型）'''
    redis_conn = get_redis_connection('sms')
    stored_code = redis_conn.get(key)  # 可能是bytes或str类型

    print(f"=== 验证码验证日志 ===")
    print(f"验证键名：{key}")
    print(f"存储的验证码：{stored_code}（类型：{type(stored_code)}）")
    print(f"用户输入的验证码：{code}（类型：{type(code)}）")
    print(f"验证码是否存在：{bool(stored_code)}")

    if not stored_code:
        print(f"错误原因：验证码不存在（已过期）")
        return False

    # 核心修复：兼容bytes和str类型
    if isinstance(stored_code, bytes):
        # 如果是bytes类型，解码为str
        stored_code_str = stored_code.decode('utf-8')
    else:
        # 如果已经是str类型，直接使用
        stored_code_str = stored_code

    # 比较字符串
    if stored_code_str != code:
        print(f"错误原因：验证码不匹配（存储：{stored_code_str}，输入：{code}）")
        return False

    # 验证成功，删除验证码
    # redis_conn.delete(key)
    print(f"验证成功：已删除验证码")
    return True
