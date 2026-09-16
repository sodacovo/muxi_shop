from django.db import models

class User(models.Model):
    name = models.CharField(max_length=255, blank=True, null=True)
    birthday = models.DateTimeField(blank=True, null=True)
    mobile = models.CharField(max_length=255, blank=True, null=True)
    gender = models.CharField(max_length=255, blank=True, null=True)
    email = models.CharField(max_length=255, blank=True, null=True)
    password = models.CharField(max_length=255, blank=True, null=True)
    create_time = models.DateTimeField(blank=True, null=True)
    # 新增：头像和背景URL字段（存储图片访问路径）
    avatar = models.CharField(max_length=255, blank=True, null=True, default="")  # 头像URL
    background = models.CharField(max_length=255, blank=True, null=True, default="")  # 背景URL

    class Meta:
        managed = False  # 不允许Django管理此表（手动创建）
        db_table = 'user'

class WeiboProfile(models.Model):
    access_token = models.CharField(max_length=255, verbose_name="微博access_token")
    wuid = models.CharField(max_length=50, unique=True, verbose_name="微博用户唯一ID")
    user_profile = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,  # 关联用户删除时设为NULL
        blank=True,
        null=True,
        verbose_name="关联系统用户",
        db_column='user_profile_id'  # 匹配数据库字段名
    )
    create_time = models.DateTimeField(verbose_name="创建时间")

    class Meta:
        managed = False  # 关键：表已手动创建，无需Django迁移管理
        db_table = 'weibo_profile'
        verbose_name = "微博用户关联表"
        verbose_name_plural = verbose_name