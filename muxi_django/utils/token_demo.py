import datetime

import jwt

from muxi_shop_api2.settings import SECRET_KEY
# 自定义一个盐
# SALT = "ASGEAAHNINOmC@13565"

# 直接使用django中的key当作盐
# SECRET_KEY

def create_token():
    headers = {
        'alg': 'HS256',
        'typ': 'JWT',
    }
    payload = {
        'user_id': 1,
        'username': 'test',
        'exp': datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=1)
    }
    # 注意：headers参数在最新版本jwt中已不推荐使用，建议合并到payload或省略
    result = jwt.encode(payload, key=SECRET_KEY, algorithm='HS256', headers=headers)
    return result


def get_payload(token):
    try:
        # 去除token中的空白字符（包括换行、空格等）
        clean_token = token.strip()
        return jwt.decode(clean_token, key=SECRET_KEY, algorithms=['HS256'], options={"verify_exp": True})
    except jwt.ExpiredSignatureError:
        return {"error": "Token已过期"}
    except jwt.InvalidTokenError as e:
        return {"error": f"无效的Token: {str(e)}"}


if __name__ == '__main__':
    # 生成新token并测试
    token = create_token()
    print("生成的Token:", token)

    # 测试解码（使用刚生成的token）
    payload = get_payload(token)
    print("解码结果:", payload)

    # 如果你确实需要使用固定token测试，确保它是单行且没有额外字符
    fixed_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJ1c2VybmFtZSI6InRlc3QiLCJleHAiOjE3NTcyNDE1MDJ9.r14xfLdrUWfeZ1bRqWCMHJmsLj9G7hrqFCzhiYPntNw"
    payload = get_payload(fixed_token)
    print("固定Token解码结果:", payload)