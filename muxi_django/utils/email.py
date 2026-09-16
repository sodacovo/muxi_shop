import smtplib
import ssl
from email.mime.text import MIMEText
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

# ------------------------------ 秒杀成功邮件（优化异常判断）------------------------------
def send_seckill_success_email(to_email, goods_name, trade_no, price, pay_url):
    subject = f'秒杀成功——订单 {trade_no}'
    html_content = f'''
<p>您好，{to_email.split('@')[0]}！</p>
<p>您已成功秒杀 <strong style="color:#f00">{goods_name}</strong></p>
<p>订单号：<code>{trade_no}</code></p>
<p>秒杀价：<span style="color:#f00;font-weight:bold">{price} 元</span></p>
<p><a href="{pay_url}" target="_blank">点击前往支付</a>（15 分钟内有效）</p>
'''
    send_success = False  # 标记邮件是否实际发送成功
    try:
        msg = MIMEText(html_content, 'html', 'utf-8')
        msg['From'] = settings.EMAIL_HOST_USER
        msg['To'] = to_email
        msg['Subject'] = subject

        # 复用稳定的SSL上下文逻辑
        context = ssl.create_default_context()
        context.options |= ssl.OP_NO_TLSv1
        context.options |= ssl.OP_NO_TLSv1_1

        with smtplib.SMTP_SSL(settings.EMAIL_HOST, settings.EMAIL_PORT, context=context) as server:
            server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            # 单独捕获发送阶段异常
            try:
                server.sendmail(settings.EMAIL_HOST_USER, [to_email], msg.as_string())
                send_success = True  # 发送成功才标记
                logger.info('✅ 秒杀邮件已发送：%s，订单号：%s', to_email, trade_no)
            except Exception as send_err:
                logger.error('❌ 秒杀邮件发送过程失败：%s, %s', to_email, str(send_err), exc_info=True)
                return False

    except Exception as conn_err:
        # 连接/关闭阶段异常处理
        if send_success:
            # 发送成功后出现的关闭异常，仅警告（不影响结果）
            logger.warning('⚠️ 秒杀邮件已发送，但关闭连接出错：%s, %s', to_email, str(conn_err))
        else:
            # 发送前的连接异常，确认为失败
            logger.error('❌ 秒杀邮件连接异常：%s, %s', to_email, str(conn_err), exc_info=True)
            return False

    # 最终返回发送结果（发送成功即使有关闭异常也返回True）
    return send_success

# ------------------------------ 验证码邮件（保持优化后的逻辑）------------------------------
def send_email_verify_code(to_email, code):
    """注册页验证码邮件发送（修复关闭连接异常导致的误判）"""
    send_success = False  # 初始标记为失败
    try:
        email_content = f"您的木犀商城注册验证码是：{code}，5分钟内有效。请勿泄露给他人。"
        msg = MIMEText(email_content, 'plain', 'utf-8')
        msg['Subject'] = "木犀商城注册验证码"
        msg['From'] = settings.EMAIL_HOST_USER
        msg['To'] = to_email

        context = ssl.create_default_context()
        context.options |= ssl.OP_NO_TLSv1
        context.options |= ssl.OP_NO_TLSv1_1

        with smtplib.SMTP_SSL(settings.EMAIL_HOST, settings.EMAIL_PORT, context=context) as server:
            server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            try:
                server.sendmail(settings.EMAIL_HOST_USER, [to_email], msg.as_string())
                send_success = True  # 发送成功标记
                logger.info(f"✅ 验证码邮件已发送：{to_email}，验证码：{code}")
            except Exception as send_err:
                logger.error(f"❌ 验证码发送过程失败：{to_email}，错误：{str(send_err)}", exc_info=True)
                return False

    except Exception as conn_err:
        if send_success:
            logger.warning(f"⚠️ 验证码发送成功，但关闭连接时出错：{to_email}，错误：{str(conn_err)}")
        else:
            logger.error(f"❌ 验证码邮件连接异常：{to_email}，错误：{str(conn_err)}", exc_info=True)
            return False

    return send_success
    

def send_generic_email(to_email, subject, html_content):
    """通用邮件发送函数"""
    send_success = False
    try:
        msg = MIMEText(html_content, 'html', 'utf-8')
        msg['From'] = settings.EMAIL_HOST_USER
        msg['To'] = to_email
        msg['Subject'] = subject

        context = ssl.create_default_context()
        context.options |= ssl.OP_NO_TLSv1
        context.options |= ssl.OP_NO_TLSv1_1

        with smtplib.SMTP_SSL(settings.EMAIL_HOST, settings.EMAIL_PORT, context=context) as server:
            server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            try:
                server.sendmail(settings.EMAIL_HOST_USER, [to_email], msg.as_string())
                send_success = True
                logger.info(f'✅ 通用邮件已发送：{to_email}，主题：{subject}')
            except Exception as send_err:
                logger.error(f'❌ 通用邮件发送失败：{to_email}，{str(send_err)}', exc_info=True)
                return False
    except Exception as conn_err:
        if send_success:
            logger.warning(f'⚠️ 通用邮件已发送，但关闭连接出错：{to_email}，{str(conn_err)}')
        else:
            logger.error(f'❌ 通用邮件连接异常：{to_email}，{str(conn_err)}', exc_info=True)
            return False
    return send_success
