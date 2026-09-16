from django.core.mail.backends.smtp import EmailBackend
from django.conf import settings
import smtplib
from smtplib import SMTPException


class CustomSMTPBackend(EmailBackend):
    def _get_connection(self, host=None, port=None, username=None, password=None,
                        use_tls=None, fail_silently=False, use_ssl=None):
        # 优先使用传入的参数，没有则用settings配置
        host = host or self.host
        port = port or self.port
        username = username or self.username
        password = password or self.password
        use_tls = use_tls if use_tls is not None else self.use_tls
        use_ssl = use_ssl if use_ssl is not None else self.use_ssl

        # 关键：手动创建SMTP_SSL连接，只传host和port，不传keyfile/certfile
        try:
            if use_ssl:
                # 直接创建SMTP_SSL，仅传递必要参数（避免keyfile报错）
                connection = smtplib.SMTP_SSL(host, port)
            else:
                connection = smtplib.SMTP(host, port)
            
            # 保持原有的TLS和认证逻辑（不改动）
            if use_tls:
                connection.starttls()
            if self.timeout is not None:
                connection.timeout = self.timeout
            if username and password:
                connection.login(username, password)
            return connection
        except SMTPException as e:
            if not fail_silently:
                raise e
            return None