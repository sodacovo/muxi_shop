# test_mail_task.py
from celery import Celery
from django.core.mail import send_mail
from django.conf import settings
import os

# 初始化Celery（和你的项目一致）
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'muxi_shop_api2.settings.settings_dev')
app = Celery('test_mail')
app.config_from_object('django.conf:settings', namespace='CELERY')

# 简单的测试任务：只发送邮件
@app.task
def test_celery_mail():
    try:
        result = send_mail(
            subject="测试邮件（Celery任务）",
            message="这是Celery任务发送的测试邮件",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=["2350496649@qq.com"],
            fail_silently=False,
        )
        return f"Celery邮件发送成功，数量：{result}"
    except Exception as e:
        return f"Celery邮件发送失败：{str(e)}"
