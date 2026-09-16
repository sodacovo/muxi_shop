import base64
import hashlib
import io
import logging
import os
import time
import uuid
import jwt
import requests
import re
from django.contrib.auth.hashers import make_password
from django.http import JsonResponse
from django_redis import get_redis_connection
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from user.models import User, WeiboProfile
from user.serializers import UserSerializer, VerifyCodeSerializer, RegisterSerializer, PasswordResetSerializer, \
    PasswordResetVerifySerializer
from muxi_shop_api2 import settings
from utils import ResponseMessage
from utils.ResponseMessage import UserResponse
from utils.jwt_auth import create_token
from utils.sms import SMS
from utils.verify import generate_code, save_verify_code, check_verify_code
from utils.email import send_email_verify_code
from datetime import datetime, timedelta
import qrcode
from rest_framework.decorators import authentication_classes, permission_classes
from django.conf import settings
from django.utils.decorators import method_decorator
from utils.rate_limit import seckill_rate_limit
from django.contrib.auth.hashers import check_password, make_password
# Create your views here.
class UserApiView(APIView):
    # 注册功能的实现
    # def post(self,request):
    #     request.data["password"] = get_md5(request.data.get("password"))
    #     # 反序列化呀，把json变成一个对象  [这是关键的一句话]
    #     user_data_serializer = UserSerializer(data=request.data)
    #     user_data_serializer.is_valid(raise_exception=True)
    #     user_data = User.objects.create(**user_data_serializer.data)
    #
    #     # 序列化一下，把json返回给前端对象
    #     user_ser = UserSerializer(instance=user_data)
    #     return JsonResponse(user_ser.data)
    def post(self,request):
        # 反序列化呀，把json变成一个对象  [这是关键的一句话]
        user_data_serializer = UserSerializer(data=request.data)
        user_data_serializer.is_valid(raise_exception=True)
        user_data = user_data_serializer.save()

        # 序列化一下，把json返回给前端对象
        user_ser = UserSerializer(instance=user_data)
        # return JsonResponse(user_ser.data)
        return ResponseMessage.UserResponse.success(user_ser.data)

    def get(self, request):
        email = request.GET.get("email")
        try:
            user_data = User.objects.get(email=email)
            user_ser = UserSerializer(user_data)
            return ResponseMessage.UserResponse.success(user_ser.data)
        except Exception as e:
            print(e)
            return ResponseMessage.UserResponse.failed("用户信息获取失败")

        # 新增：PUT方法——更新当前登录用户的信息（复用根路由）

    def put(self, request):
        try:
            # 1. 从认证结果提取用户邮箱
            auth_result = request.user
            if not auth_result.get("status"):
                error_msg = auth_result.get("error", "Token认证失败")
                return ResponseMessage.UserResponse.failed(error_msg)  # Token无效→4001

            payload_data = auth_result.get("data", {})
            user_email = payload_data.get("username")
            if not user_email:
                return ResponseMessage.UserResponse.failed("Token中无有效用户邮箱")  # 无邮箱→4001

            # 2. 查询用户实例（捕获用户不存在异常）
            try:
                current_user = User.objects.get(email=user_email)
            except User.DoesNotExist:
                return ResponseMessage.UserResponse.failed("当前用户不存在")  # 用户不存在→4001

            # 3. 处理生日格式（确保与serializer匹配）
            update_data = request.data.copy()  # 避免修改原数据
            if "birthday" in update_data and update_data["birthday"]:
                # 前端传YYYY-MM-DD，后端需YYYY-MM-DD HH:MM:SS（适配serializer的DateTimeField）
                if len(str(update_data["birthday"]).split(" ")) == 1:
                    update_data["birthday"] = f"{update_data['birthday']} 00:00:00"

            # 4. 序列化器验证（打印错误详情，定位验证失败原因）
            serializer = UserSerializer(
                instance=current_user,
                data=update_data,
                partial=True  # 支持部分字段更新
            )
            # 关键：如果验证失败，打印具体错误（方便排查）
            if not serializer.is_valid():
                print(f"序列化器验证失败：{serializer.errors}")  # 打印错误，比如字段格式问题
                return ResponseMessage.UserResponse.failed(f"参数错误：{serializer.errors}")  # 验证失败→4001

            # 5. 验证通过，保存更新（成功路径）
            serializer.save()
            updated_ser = UserSerializer(current_user)
            # 关键：成功时返回UserResponse.success（status=4000）
            return ResponseMessage.UserResponse.success(updated_ser.data)

        except Exception as e:
            # 捕获其他未知错误，打印详情
            print(f"更新用户信息未知错误：{str(e)}")
            return ResponseMessage.UserResponse.failed(f"更新失败：{str(e)}")  # 未知错误→4001

class LoginView(APIView):
    """登录视图（使用 APIView 直接处理，无需 serializer_class）"""
    authentication_classes = []  # 不需要认证
    permission_classes = [AllowAny]  # 允许任何人访问

    @method_decorator(seckill_rate_limit(limit=5, period=60))
    def post(self, request):
        request_data = request.data
        email = request_data.get('username')  # 前端传的是邮箱

        # 1. 捕获 User.DoesNotExist 异常
        try:
            user_data = User.objects.get(email=email)
        except User.DoesNotExist:
            return ResponseMessage.UserResponse.other("用户名或者是密码错误")

        # 🌟 新增：校验用户的 email 字段非空（避免 Token 中 username 为空）
        if not user_data.email:
            return ResponseMessage.UserResponse.other("用户邮箱未设置，无法登录")

        # 2. 获取数据库中的密码（已加密）
        db_user_password = user_data.password
        user_password = request_data.get('password')
        md5_user_password = user_password  # 前端已做 MD5 加密

        # 3. 对比密码
        if md5_user_password != db_user_password:
            return ResponseMessage.UserResponse.other("用户名或者是密码错误")
        else:
            # 生成包含 email 和 user_id 的 Token
            token_info = {
                "username": user_data.email,  # 直接用 user_data.email，更安全（避免前端传错）
                "user_id": user_data.id
            }
            token_data = create_token(token_info)
            return ResponseMessage.UserResponse.success({
                "token": token_data,
                "name": user_data.name
            })

class VerifyCodeView(APIView):
    """发送验证码（适配现有verify.py，修复参数错误）"""

    def post(self, request):
        print(f'【VerifyCodeView】收到请求体：{request.data}')
        serializer = VerifyCodeSerializer(data=request.data)
        if not serializer.is_valid():
            return UserResponse.failed(f"输入错误：{serializer.errors}")

        email = serializer.validated_data.get('email')
        phone = serializer.validated_data.get('phone')
        # 使用verify.py中的generate_code生成4位验证码
        code = generate_code(length=4)  # 已限制为1-4位，符合要求
        print(f'【VerifyCodeView】提取后 - email={email}, phone={phone}')
        try:
            if email:
                # 发送邮箱验证码
                send_success = send_email_verify_code(email, code)
                if send_success:
                    # 调用verify.py中的save_verify_code（只传key和code）
                    save_verify_code(
                        key=f"email:{email}",  # 键名：与验证时一致
                        code=code  # 验证码：无需传过期时间（已在函数内处理）
                    )
                    return UserResponse.success("邮箱验证码已发送，请注意查收")
                else:
                    print(f'【VerifyCodeView】提取后 - email={email}, phone={phone}')
                    return UserResponse.failed("邮箱验证码发送失败，请稍后重试")

            elif phone:
                # 发送手机验证码（使用修复后的SMS类）
                send_success = SMS.send_sms(phone=phone, code=code)
                if send_success:
                    # 调用verify.py中的save_verify_code
                    save_verify_code(
                        key=f"sms:{phone}",  # 键名：与验证时一致
                        code=code
                    )
                    return UserResponse.success("短信验证码已发送，请注意查收")
                else:
                    print(f'【VerifyCodeView】提取后 - email={email}, phone={phone}')
                    return UserResponse.failed("短信验证码发送失败，请稍后重试")

        except Exception as e:
            logging.error(f"验证码发送异常：{str(e)}")
            return UserResponse.failed("系统异常，请稍后再试")


class RegisterView(APIView):
    """注册视图（使用新的序列化器）"""

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        # 返回用户信息（排除密码）
        return ResponseMessage.UserResponse.success({
            "email": user.email,
            "name": user.name,
            "create_time": user.create_time
        })

@authentication_classes([])
@permission_classes([AllowAny])
class WeiboQrCodeView(APIView):
    """生成微博登录二维码"""

    def get(self, request):
        try:
            # 1. 生成唯一ticket（用于标识当前二维码）
            ticket = f"weibo_ticket_{uuid.uuid4().hex[:8]}"  # 随机唯一字符串

            # 2. 生成二维码内容（微博授权地址，需替换为你的实际授权地址）
            # 格式：https://api.weibo.com/oauth2/authorize?client_id=你的APP_KEY&redirect_uri=你的回调地址&state=ticket
            weibo_auth_url = (
                f"https://api.weibo.com/oauth2/authorize"
                f"?client_id={settings.WEIBO_APP_KEY}"  # 从配置读，避免硬编码
                f"&redirect_uri={settings.WEIBO_REDIRECT_URI}"  # 统一用配置里的地址
                f"&state={ticket}"
            )

            # 3. 生成二维码图片并转为base64
            qr = qrcode.make(weibo_auth_url)  # 生成二维码图片
            buffer = io.BytesIO()
            qr.save(buffer, format="PNG")  # 保存到内存
            qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")  # 转为base64字符串
            qrcode_url = f"data:image/png;base64,{qr_base64}"  # 完整的base64图片URL

            # 4. 将ticket存入Redis（有效期5分钟）
            redis_conn = get_redis_connection("default")
            redis_conn.setex(
                name=f"weibo_ticket:{ticket}",
                time=300,  # 5分钟有效期
                value="pending"  # 标记为待扫码状态
            )

            # 5. 返回成功响应（包含qrcode_url）
            return UserResponse.success({
                "qrcode_url": qrcode_url,  # 关键：正确返回qrcode_url
                "ticket": ticket,
                "expire_seconds": 300,
                "msg": "二维码生成成功"
            })

        except Exception as e:
            # 捕获所有异常，返回错误信息
            return UserResponse.failed(f"二维码生成失败：{str(e)}")

class WeiboQrCheckView(APIView):
    """轮询验证二维码登录状态"""
    def get(self, request):
        ticket = request.query_params.get("ticket")
        if not ticket:
            # 缺少参数：返回失败（status:4001）
            return UserResponse.failed("缺少ticket参数")

        redis_conn = get_redis_connection("default")
        try:
            # 检查ticket是否过期
            if not redis_conn.exists(f"weibo_ticket:{ticket}"):
                return UserResponse.other({
                    "status": "expired",
                    "msg": "二维码已过期，请刷新重试"
                })

            # 检查是否已扫码授权
            auth_code = redis_conn.get(f"weibo_ticket:{ticket}_code")
            if auth_code:
                # 已授权：返回success+code（status:4000）
                return UserResponse.success({
                    "status": "success",
                    "authorization_code": auth_code.decode("utf-8"),  # 转字符串，避免bytes类型
                    "msg": "登录成功"
                })
            else:
                # 未授权：返回pending（status:4000，因为轮询请求本身成功）
                return UserResponse.success({
                    "status": "pending",
                    "msg": "请用微博APP扫码并确认登录"
                })
        except Exception as e:
            # 异常返回失败（status:4001）
            return UserResponse.failed(f"轮询失败：{str(e)}")




class WeiboCallbackView(APIView):
    """微博授权回调处理"""
    def post(self, request):
        code = request.data.get("code")
        ticket = request.data.get("ticket")
        if not code or not ticket:
            return UserResponse.failed("缺少code或ticket参数")

        # 兑换微博access_token
        token_url = "https://api.weibo.com/oauth2/access_token"
        token_data = {
            "client_id": settings.WEIBO_APP_KEY,
            "client_secret": settings.WEIBO_APP_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.WEIBO_REDIRECT_URI
        }

        response = requests.post(token_url, data=token_data)
        if response.status_code != 200:
            return UserResponse.failed("兑换access_token失败")

        token_result = response.json()
        access_token = token_result.get("access_token")
        wuid = token_result.get("uid")
        if not access_token or not wuid:
            return UserResponse.failed("获取微博用户信息失败")

        # 检查ticket有效性
        redis_conn = get_redis_connection("default")
        if not redis_conn.exists(f"weibo_ticket:{ticket}"):
            return UserResponse.failed("二维码已过期，请重新扫码")

        # 绑定/创建用户
        try:
            weibo_profile = WeiboProfile.objects.get(wuid=wuid)
            user = weibo_profile.user_profile
            weibo_profile.access_token = access_token
            weibo_profile.save()
        except WeiboProfile.DoesNotExist:
            user = User.objects.create(
                name=f"微博用户_{wuid[:6]}",
                password=make_password(None),
                create_time=datetime.now(),
                is_active=True
            )
            WeiboProfile.objects.create(
                access_token=access_token,
                wuid=wuid,
                user_profile=user,
                create_time=datetime.now()
            )

        # 存储code到Redis
        redis_conn.setex(
            name=f"weibo_ticket:{ticket}_code",
            time=60,
            value=code
        )

        # 生成JWT token（返回给前端）
        token = jwt.encode(
            payload={
                "user_id": user.id,
                "exp": datetime.now() + timedelta(days=7)
            },
            key=settings.SECRET_KEY,
            algorithm="HS256"
        )

        # 🔴 统一格式返回成功（status:4000）
        return UserResponse.success({
            "token": token,
            "user_id": user.id,
            "name": user.name,
            "msg": "微博登录成功"
        })


class CurrentUserInfoView(APIView):
    # 不需要加 IsAuthenticated 权限类！因为我们手动校验登录状态
    def get(self, request):
        try:
            # 1. 从认证结果中获取 Token 解析信息（request.user 是 JWTHeaderAuthentication 返回的 result_payload）
            # 回顾你的认证类：返回的是 (result_payload, token)，所以 request.user = result_payload
            auth_result = request.user  # auth_result 是 get_payload 返回的字典：{"status": True/False, "data": {...}, "error": "..."}
            # print("认证结果:", auth_result)  # 可打印查看，格式如：{"status":True, "data":{"username":"2350496649@qq.com", "exp":...}, "error":None}

            # 2. 手动校验登录状态（替代 IsAuthenticated 权限类）
            if not auth_result.get("status"):
                # Token解析失败（如过期、无效），返回错误
                error_msg = auth_result.get("error", "Token认证失败")
                return ResponseMessage.UserResponse.failed(error_msg)

            # 3. 从解析结果中提取用户标识（username 就是你的登录邮箱）
            payload_data = auth_result.get("data", {})
            user_email = payload_data.get("username")  # 你的 Token 里存的是 "username"（邮箱）
            if not user_email:
                return ResponseMessage.UserResponse.failed("Token中无有效用户邮箱")

            # 4. 根据邮箱查询 Django User实例（关键：转成User实例，后续序列化用）
            user_instance = User.objects.get(email=user_email)  # 靠邮箱查用户

            # 5. 序列化User实例，返回给前端（包含name、avatar、background等所有字段）
            serializer = UserSerializer(user_instance)
            return ResponseMessage.UserResponse.success(serializer.data)

        except User.DoesNotExist:
            # 邮箱对应的用户不存在（极端情况，比如用户被删除但Token还在）
            return ResponseMessage.UserResponse.failed("当前用户不存在")
        except Exception as e:
            # 其他未知错误（如数据库异常）
            # print(f"获取当前用户信息错误：{str(e)}")
            return ResponseMessage.UserResponse.failed("获取用户信息失败，请重试")

# 生成唯一文件名（避免重复）
def get_unique_filename(user_id, upload_file):  # 注意：参数从file_ext改为upload_file
    # 1. 计算文件内容的MD5哈希（相同图片的哈希值完全相同）
    file_hash = hashlib.md5()
    # 分块读取文件内容（避免大文件占用过多内存）
    for chunk in upload_file.chunks():
        file_hash.update(chunk)
    # 哈希值转16进制字符串（32位，确保唯一性）
    hash_str = file_hash.hexdigest()

    # 2. 提取文件原始后缀（如".jpg"，保持原格式）
    file_ext = os.path.splitext(upload_file.name)[-1].lower()

    # 3. 生成最终文件名：用户ID_哈希值.后缀（如"user_8_a1b2c3d4.jpg"）
    return f"user_{user_id}_{hash_str}{file_ext}"


# 1. 头像上传完整视图类
class AvatarUploadView(APIView):
    def post(self, request):
        try:
            # -------------------------- 1. 手动校验登录状态 + 获取当前用户实例 --------------------------
            # request.user 是 JWTHeaderAuthentication 返回的字典：{"status": True, "data": {"username": "xxx@qq.com"}, "error": None}
            auth_result = request.user
            # 校验Token是否有效（status=True表示Token解析成功）
            if not auth_result.get("status"):
                error_msg = auth_result.get("error", "Token认证失败")
                return ResponseMessage.UserResponse.failed(error_msg)
            # 从Token解析结果中提取用户邮箱（username对应登录时的邮箱）
            payload_data = auth_result.get("data", {})
            user_email = payload_data.get("username")
            if not user_email:
                return ResponseMessage.UserResponse.failed("Token中无有效用户邮箱")
            # 根据邮箱查询Django User实例（避免request.user是字典的问题）
            try:
                current_user = User.objects.get(email=user_email)
            except User.DoesNotExist:
                return ResponseMessage.UserResponse.failed("当前用户不存在")

            # -------------------------- 2. 上传文件基础校验 --------------------------
            # 获取前端传递的文件（ElUpload默认参数名为"file"）
            upload_file = request.FILES.get("file")
            if not upload_file:
                return ResponseMessage.UserResponse.failed("请选择要上传的头像文件")

            # -------------------------- 3. 文件格式校验（仅允许JPG/PNG） --------------------------
            allowed_extensions = [".jpg", ".jpeg", ".png"]
            # 提取文件后缀（如"test.jpg" → ".jpg"）
            file_ext = os.path.splitext(upload_file.name)[-1].lower()
            if file_ext not in allowed_extensions:
                return ResponseMessage.UserResponse.failed("仅支持JPG/PNG格式的头像文件")

            # -------------------------- 4. 文件大小校验（≤2MB） --------------------------
            max_size = 2 * 1024 * 1024  # 2MB（字节）
            if upload_file.size > max_size:
                return ResponseMessage.UserResponse.failed(f"头像文件大小不能超过{max_size // 1024 // 1024}MB")

            # -------------------------- 5. 配置文件保存路径 --------------------------
            # 基础路径：项目static目录下的user_avatars文件夹（如"static/user_avatars/"）
            save_dir = os.path.join(settings.MEDIA_ROOT, "user_avatars")
            # 确保目录存在（不存在则自动创建，避免IO错误）
            os.makedirs(save_dir, exist_ok=True)

            # -------------------------- 6. 生成唯一文件名（避免重复覆盖） --------------------------
            # 示例：get_unique_filename(用户ID, 文件后缀) → "user_8_1758873353.jpg"
            filename = get_unique_filename(user_id=current_user.id, upload_file=upload_file)
            # 完整保存路径（目录+文件名）
            save_path = os.path.join(save_dir, filename)

            # -------------------------- 7. 分块保存文件（避免大文件内存溢出） --------------------------
            with open(save_path, "wb") as f:
                # 分块读取上传文件并写入本地
                for chunk in upload_file.chunks():
                    f.write(chunk)

            # -------------------------- 8. 生成完整图片URL（前端可直接访问） --------------------------
            # 拼接：settings配置的头像URL前缀 + 唯一文件名 → "http://localhost:8000/static/user_avatars/user_8_1758873353.jpg"
            avatar_url = f"{settings.USER_AVATAR_URL}{filename}"

            # -------------------------- 9. 更新用户数据库中的avatar字段 --------------------------
            current_user.avatar = avatar_url
            current_user.save()  # 保存到数据库

            # -------------------------- 10. 返回成功响应（带完整图片URL） --------------------------
            return ResponseMessage.UserResponse.success({
                "avatar_url": avatar_url,  # 前端用于预览的完整URL
                "msg": "头像上传成功"
            })

        # -------------------------- 异常捕获（精准处理不同错误场景） --------------------------
        except User.DoesNotExist:
            # 极端情况：Token中的邮箱对应的用户已被删除
            return ResponseMessage.UserResponse.failed("上传失败：当前用户不存在")
        except PermissionError:
            # 权限错误（如服务器目录无写入权限）
            return ResponseMessage.UserResponse.failed("上传失败：服务器保存目录无写入权限")
        except Exception as e:
            # 其他未知错误（打印详情方便排查）
            # print(f"头像上传未知错误：{str(e)}")
            return ResponseMessage.UserResponse.failed(f"头像上传失败：{str(e)}")


# 2. 背景装饰上传完整视图类
class BackgroundUploadView(APIView):
    def post(self, request):
        try:
            # -------------------------- 1. 手动校验登录状态 + 获取当前用户实例（与头像逻辑一致） --------------------------
            auth_result = request.user
            if not auth_result.get("status"):
                error_msg = auth_result.get("error", "Token认证失败")
                return ResponseMessage.UserResponse.failed(error_msg)

            payload_data = auth_result.get("data", {})
            user_email = payload_data.get("username")
            if not user_email:
                return ResponseMessage.UserResponse.failed("Token中无有效用户邮箱")

            try:
                current_user = User.objects.get(email=user_email)
            except User.DoesNotExist:
                return ResponseMessage.UserResponse.failed("当前用户不存在")

            # -------------------------- 2. 上传文件基础校验 --------------------------
            upload_file = request.FILES.get("file")
            if not upload_file:
                return ResponseMessage.UserResponse.failed("请选择要上传的背景文件")

            # -------------------------- 3. 文件格式校验（仅允许JPG/PNG） --------------------------
            allowed_extensions = [".jpg", ".jpeg", ".png"]
            file_ext = os.path.splitext(upload_file.name)[-1].lower()
            if file_ext not in allowed_extensions:
                return ResponseMessage.UserResponse.failed("仅支持JPG/PNG格式的背景文件")

            # -------------------------- 4. 文件大小校验（≤5MB，比头像宽松） --------------------------
            max_size = 5 * 1024 * 1024  # 5MB（字节）
            if upload_file.size > max_size:
                return ResponseMessage.UserResponse.failed(f"背景文件大小不能超过{max_size // 1024 // 1024}MB")

            # -------------------------- 5. 配置文件保存路径 --------------------------
            # 基础路径：项目static目录下的user_backgrounds文件夹（如"static/user_backgrounds/"）
            save_dir = os.path.join(settings.MEDIA_ROOT, "user_backgrounds")
            os.makedirs(save_dir, exist_ok=True)  # 确保目录存在

            # -------------------------- 6. 生成唯一文件名 --------------------------
            filename = get_unique_filename(user_id=current_user.id, upload_file=upload_file)
            save_path = os.path.join(save_dir, filename)

            # -------------------------- 7. 分块保存文件 --------------------------
            with open(save_path, "wb") as f:
                for chunk in upload_file.chunks():
                    f.write(chunk)

            # -------------------------- 8. 生成完整图片URL --------------------------
            # 拼接：settings配置的背景URL前缀 + 唯一文件名 → "http://localhost:8000/static/user_backgrounds/user_8_1758873376.jpg"
            background_url = f"{settings.USER_BACKGROUND_URL}{filename}"

            # -------------------------- 9. 更新用户数据库中的background字段 --------------------------
            current_user.background = background_url
            current_user.save()

            # -------------------------- 10. 返回成功响应 --------------------------
            return ResponseMessage.UserResponse.success({
                "background_url": background_url,  # 前端用于预览的完整URL
                "msg": "背景装饰上传成功"
            })

        # -------------------------- 异常捕获 --------------------------
        except User.DoesNotExist:
            return ResponseMessage.UserResponse.failed("上传失败：当前用户不存在")
        except PermissionError:
            return ResponseMessage.UserResponse.failed("上传失败：服务器保存目录无写入权限")
        except Exception as e:
            # print(f"背景上传未知错误：{str(e)}")
            return ResponseMessage.UserResponse.failed(f"背景上传失败：{str(e)}")


from rest_framework.response import Response  # 必须导入Response类


@authentication_classes([])  # 免认证
@permission_classes([AllowAny])
class PasswordResetVerifyView(APIView):
    def post(self, request):
        # 1. 验证请求参数
        serializer = PasswordResetVerifySerializer(data=request.data)
        if not serializer.is_valid():
            # print(f"序列化器错误：{serializer.errors}")
            # 直接返回 UserResponse.failed（已包含 JsonResponse，无需包裹）
            return UserResponse.failed(data=f"参数错误：{serializer.errors}")

        # 2. 提取参数（去空格，避免隐性错误）
        email = serializer.validated_data.get('email', '').strip()
        phone = serializer.validated_data.get('phone', '').strip()
        verify_code = str(serializer.validated_data.get('verify_code')).strip()

        try:
            # 3. 确定 Redis 键名（与发送时一致）
            if email:
                key = f"email:{email}"
                # 查用户（确保邮箱存在）
                user = User.objects.get(email=email)
            else:
                key = f"sms:{phone}"
                user = User.objects.get(mobile=phone.strip())

            # 4. 验证验证码（调用 verify.py 中的函数）
            if not check_verify_code(key, verify_code):
                # 直接返回失败响应
                return UserResponse.failed(data="验证码错误或已过期")

            # 5. 生成重置令牌（存储到 sms 数据库，600秒过期）
            reset_token = f"reset_{uuid.uuid4().hex[:16]}"
            redis_conn = get_redis_connection('sms')  # 用 sms 数据库（索引1）
            redis_conn.setex(
                name=f"reset_token:{reset_token}",
                time=600,
                value=str(user.id)
            )
            # print(f"=== 验证成功 ===")
            # print(f"用户：{user.email if email else user.mobile}")
            # print(f"重置令牌：{reset_token}")

            # 6. 验证成功：返回 UserResponse.success（带 reset_token）
            # 注意：UserResponse.success 要求传 data 参数，按你的类定义传字典
            return UserResponse.success(
                data={
                    "reset_token": reset_token,
                    "msg": "验证码验证通过，可进行密码重置"
                }
            )

        # 7. 异常处理（都直接返回 UserResponse.failed）
        except User.DoesNotExist:
            return UserResponse.failed(data="该账号不存在")
        except Exception as e:
            # print(f"验证异常：{str(e)}")
            return UserResponse.failed(data=f"系统异常：{str(e)}")


@authentication_classes([])
@permission_classes([AllowAny])
class PasswordResetView(APIView):
    """忘记密码-重置密码接口"""
    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        # print(f"\n=== 重置密码接口日志 ===")
        # print(f"前端传的原始参数：{request.data}")  # 看前端到底传了什么
        # print(f"序列化器错误：{serializer.errors if not serializer.is_valid() else '无'}")  # 看哪里错了
        serializer.is_valid(raise_exception=True)

        reset_token = serializer.validated_data.get('reset_token')
        new_password = serializer.validated_data.get('new_password')
        redis_conn = get_redis_connection("sms")

        # 1. 验证重置令牌
        user_id = redis_conn.get(f"reset_token:{reset_token}")
        if not user_id:
            return UserResponse.failed("重置链接已过期，请重新验证")

        try:
            # 2. 查询用户
            user = User.objects.get(id=int(user_id.decode("utf-8")))
            # 3. 更新密码（前端已MD5加密，直接存储）
            user.password = new_password
            user.save()

            # 4. 删除已使用的令牌（防止重复使用）
            redis_conn.delete(f"reset_token:{reset_token}")

            return UserResponse.success("密码重置成功")
        except User.DoesNotExist:
            return UserResponse.failed("用户不存在")
        except Exception as e:
            return UserResponse.failed(f"重置失败：{str(e)}")
            
            
# 修改密码
@authentication_classes([])  # 免认证
@permission_classes([AllowAny])
class ModifyPasswordView(APIView):
    """登录后修改密码（验证旧密码+验证码，适配MD5加密）"""
    def post(self, request):
        # 1. 提取并校验基础参数
        old_password = request.data.get('old_password', '').strip()
        new_password = request.data.get('new_password', '').strip()
        phone = request.data.get('phone', '').strip()
        verify_code = request.data.get('verify_code', '').strip()

        # 基础必填校验
        if not all([old_password, new_password, phone, verify_code]):
            return UserResponse.failed("旧密码、新密码、手机号、验证码均为必填")
        
        # 新密码格式校验（和前端一致：6-20位，字母+数字）
        if not re.match(r'^(?=.*[a-zA-Z])(?=.*\d).{6,20}$', new_password):
            return UserResponse.failed("新密码需包含字母+数字，长度6-20位")

        try:
            # 2. 根据手机号查询用户
            user = User.objects.get(mobile=phone)
            
            # 🌟 关键修改1：MD5加密前端传的旧密码，和数据库密文对比
            def get_md5(pwd):
                md5 = hashlib.md5()
                md5.update(pwd.encode('utf-8'))
                return md5.hexdigest()
            
            md5_old_pwd = get_md5(old_password)  # 明文123456转MD5密文
            if md5_old_pwd != user.password:  # 对比数据库中的MD5密文
                return UserResponse.failed("旧密码错误")
            
            # 3. 验证短信验证码（复用已有的check_verify_code函数）
            redis_key = f"sms:{phone}"
            if not check_verify_code(redis_key, verify_code):
                return UserResponse.failed("验证码错误或已过期")
            
            # 🌟 关键修改2：新密码MD5加密后存储（和登录逻辑一致）
            md5_new_pwd = get_md5(new_password)
            user.password = md5_new_pwd  # 替换为MD5密文
            user.save()
            
            # 6. 返回成功响应
            return UserResponse.success("密码修改成功，请重新登录")
        
        except User.DoesNotExist:
            return UserResponse.failed("该手机号对应的用户不存在")
        except Exception as e:
            # 打印错误方便排查
            print(f"修改密码异常：{str(e)}")
            return UserResponse.failed(f"密码修改失败：{str(e)}")