import logging
import re
import json  # 新增：导入json模块用于手动构造响应
from django.http import JsonResponse  # 新增：导入JsonResponse
from rest_framework.views import APIView

from user.serializers import VerifyCodeSerializer
# 注释掉UserResponse，改用手动返回
# from utils.ResponseMessage import UserResponse
from utils.email import send_email_verify_code
from utils.sms import SMS
from utils.verify import generate_code, save_verify_code


def is_valid_email(email):
    """验证邮箱格式是否正确"""
    if not email:
        return False
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(pattern, email) is not None


class VerifyCodeView(APIView):
    def post(self, request):
        serializer = VerifyCodeSerializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"序列化失败：{serializer.errors}")
            # 原：return UserResponse.failed(...) → 改为返回1002（失败）
            return JsonResponse({"status": 1002, "data": f"输入错误：{serializer.errors}"}, safe=False)

        email = serializer.validated_data.get('email')
        phone = serializer.validated_data.get('phone')
        code = generate_code(length=4)

        try:
            if email:
                if not is_valid_email(email):
                    logger.error(f"邮箱格式错误：{email}")
                    # 原：return UserResponse.failed(...) → 改为1002（失败）
                    return JsonResponse({"status": 1002, "data": "邮箱格式错误，请检查后重试"}, safe=False)

                send_success = send_email_verify_code(email, code)
                logger.info(f"邮件发送结果：send_success={send_success}，邮箱={email}，验证码={code}")

                if send_success:
                    try:
                        save_verify_code(key=f"email:{email}", code=code)
                        logger.info(f"验证码保存成功：key=email:{email}，code={code}")
                        # 原：return UserResponse.success(...) → 改为1001（成功）
                        return JsonResponse({"status": 1001, "data": "邮箱验证码已发送，请注意查收"}, safe=False)
                    except Exception as save_err:
                        logger.error(f"验证码保存失败：{str(save_err)}，key=email:{email}")
                        # 保存失败 → 1002（失败）
                        return JsonResponse({"status": 1002, "data": "验证码发送成功，但保存失败，请稍后再试"}, safe=False)
                else:
                    logger.error(f"邮件发送失败：邮箱={email}")
                    # 发送失败 → 1002（失败）
                    return JsonResponse({"status": 1002, "data": "邮箱验证码发送失败，请稍后重试"}, safe=False)

            elif phone:
                send_success = SMS.send_sms(phone=phone, code=code)
                logger.info(f"短信发送结果：send_success={send_success}，手机号={phone}")
                if send_success:
                    try:
                        save_verify_code(key=f"sms:{phone}", code=code)
                        logger.info(f"短信验证码保存成功：key=sms:{phone}")
                        # 短信成功 → 1001（成功）
                        return JsonResponse({"status": 1001, "data": "短信验证码已发送，请注意查收"}, safe=False)
                    except Exception as save_err:
                        logger.error(f"短信验证码保存失败：{str(save_err)}")
                        return JsonResponse({"status": 1002, "data": "短信发送成功，但保存失败，请稍后再试"}, safe=False)
                else:
                    return JsonResponse({"status": 1002, "data": "短信验证码发送失败，请稍后重试"}, safe=False)

        except Exception as e:
            logger.error(f"全局异常：{str(e)}", exc_info=True)
            # 系统异常 → 1003（其他）
            return JsonResponse({"status": 1003, "data": "系统异常，请稍后再试"}, safe=False)
