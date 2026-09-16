import datetime
import re
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from user.models import User
from utils.Password_encode import get_md5
from utils.verify import check_verify_code


class UserSerializer(serializers.ModelSerializer):
    # email作为用户名进行登录， 这里我们需要做一个唯一性的验证
    email = serializers.EmailField(
        required=True, allow_blank=False,
        validators=[UniqueValidator(queryset=User.objects.all(), message='用户已存在！')]
    )
    password = serializers.CharField(write_only=True) # 只往数据库里写，不要往回读
    birthday = serializers.DateTimeField(format="%Y-%m-%d", required=False, read_only=True)
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", required=False, read_only=True)
    # create 方法会被自动调用，这里可以做一些数据的验证或者是存储之前数据的加工
    def create(self, validated_data):
        print(validated_data)
        validated_data['password'] = get_md5(validated_data['password'])
        validated_data['create_time'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        result = User.objects.create(**validated_data)
        return result

    class Meta:
        model = User
        fields = "__all__"


class VerifyCodeSerializer(serializers.Serializer):
    """发送验证码序列化器（用于/user/verify-code/接口）"""
    phone = serializers.CharField(required=True)  # 前端传的统一字段

    def validate(self, data):
        # 从phone字段中拆分邮箱/手机号（核心修复）
        raw_phone = data.get('phone', '').strip()
        
        # 复用验证验证码时的邮箱判断逻辑（保持一致）
        def is_email_format(val):
            email_re = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
            return bool(email_re.match(val))
        
        if is_email_format(raw_phone):
            # 是邮箱：存入email字段，供视图调用邮件接口
            data['email'] = raw_phone
            data.pop('phone')  # 清除phone字段，避免混淆
        else:
            # 是手机号：保留phone字段，供视图调用短信接口
            data['phone'] = raw_phone
        
        return data




class RegisterSerializer(serializers.ModelSerializer):
    """注册序列化器（仅修复邮箱注册验证码键名，不影响手机注册）"""
    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all(), message="邮箱已注册")]
    )
    password = serializers.CharField(write_only=True)
    verify_code = serializers.CharField(write_only=True, required=True)
    # phone：临时字段（接收验证码用，手机注册传手机号，邮箱注册传邮箱）
    phone = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = User
        fields = ['email', 'password', 'name', 'mobile', 'verify_code', 'phone']
        extra_kwargs = {
            'mobile': {'required': False, 'allow_blank': True},
            'name': {'required': True, 'allow_blank': False}
        }

    def validate(self, data):
        """仅修改键名生成逻辑，其他逻辑（手机注册相关）完全不变"""
        # 1. 提取参数（原有逻辑不变）
        verify_code = data.pop('verify_code')
        email = data.get('email', '').strip()
        phone = data.get('phone', '').strip()

        # 2. 新增：判断phone字段的格式（邮箱/手机号），动态选择键名前缀
        def is_email_format(val):
            """工具函数：判断是否为邮箱格式"""
            email_re = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
            return bool(email_re.match(val))

        # 核心修复：键名生成逻辑（手机注册仍用sms:，邮箱注册用email:）
        if phone:
            if is_email_format(phone):
                # 邮箱注册：phone字段值为邮箱，键名用 email:{phone}
                key = f"email:{phone}"
            else:
                # 手机注册：phone字段值为手机号，键名仍用 sms:{phone}（原有逻辑不变）
                key = f"sms:{phone}"
        else:
            # 极端情况：无phone时用email键名（原有逻辑不变）
            key = f"email:{email}"

        # 3. 验证码校验（原有逻辑不变）
        if not check_verify_code(key, verify_code):
            raise serializers.ValidationError("验证码错误或已过期")

        # 4. 移除临时字段phone + 手机注册时同步mobile（原有逻辑不变，确保手机注册正常）
        data.pop('phone', None)
        if phone and not is_email_format(phone):  # 仅手机注册时赋值mobile
            data['mobile'] = phone

        return data

    def create(self, validated_data):
        """创建用户：密码加密 + 填充创建时间"""
        # 1. 密码加密（使用项目自带的MD5加密工具）
        validated_data["password"] = get_md5(validated_data["password"])
        # 2. 填充创建时间（确保User模型有create_time字段）
        validated_data["create_time"] = datetime.datetime.now()
        # 3. 创建用户（此时validated_data已无phone字段，无TypeError）
        return User.objects.create(**validated_data)


class PasswordResetVerifySerializer(serializers.Serializer):
    """忘记密码-验证码验证序列化器（适配前端统一传递phone字段）"""
    # 核心修改：仅接收phone字段（邮箱/手机号都通过该字段传递，与注册一致）
    phone = serializers.CharField(required=True)
    verify_code = serializers.CharField(required=True, write_only=True)

    def validate(self, data):
        # 1. 提取并清洗参数（与注册流程逻辑一致）
        verify_code = data.get('verify_code').strip()  # 验证码去空格
        phone = data.get('phone', '').strip()          # 账号（邮箱/手机号）去空格

        # 2. 验证账号不为空
        if not phone:
            raise serializers.ValidationError("请输入邮箱或手机号")

        # 3. 复用注册时的键名生成逻辑（核心：判断phone是邮箱还是手机号）
        def is_email_format(val):
            """判断是否为邮箱格式（与注册序列化器逻辑完全一致）"""
            email_re = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
            return bool(email_re.match(val))

        # 生成与注册一致的Redis键名
        if is_email_format(phone):
            key = f"email:{phone}"  # 邮箱账号：键名=email:邮箱
        else:
            key = f"sms:{phone}"    # 手机号账号：键名=sms:手机号

        # 4. 校验验证码（逻辑不变，确保键名匹配）
        if not check_verify_code(key, verify_code):
            raise serializers.ValidationError("验证码错误或已过期")

        # 5. 补充：将账号按类型存入data，供视图查询用户使用
        if is_email_format(phone):
            data['email'] = phone  # 视图中用email查询用户
        else:
            data['phone'] = phone  # 视图中用phone查询用户

        return data


# PasswordResetSerializer 无需修改（参数格式未变）
class PasswordResetSerializer(serializers.Serializer):
    """忘记密码-重置密码序列化器"""
    reset_token = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, write_only=True)

    def validate_new_password(self, value):
        # 验证密码格式：6-20位，含字母+数字
        def validate_new_password(self, value):
        # 只保留“非空”校验（可选），删除长度和字母数字校验
            if not value:
                raise serializers.ValidationError("新密码不能为空")
            # 直接返回前端传的MD5串，不做其他校验（前端已校验过原始密码）
            return value