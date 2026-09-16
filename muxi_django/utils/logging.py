import logging
import traceback
from threading import Thread, local  # 新增local用于线程隔离
from django.conf import settings
import os
from utils.email import send_generic_email

# 新增：线程局部变量，存储当前任务的上下文（订单号、任务类型）
local_data = local()

# 新增：日志过滤器，自动添加trade_no和task_type到日志记录
class ContextFilter(logging.Filter):
    def filter(self, record):
        # 给日志记录添加trade_no和task_type字段（默认unknown）
        record.trade_no = getattr(local_data, 'trade_no', 'unknown')
        record.task_type = getattr(local_data, 'task_type', 'system')
        return True

# 新增：上下文管理器，自动设置/清除线程变量（用于任务中绑定订单号）
class TaskContext:
    def __init__(self, trade_no, task_type):
        self.trade_no = trade_no
        self.task_type = task_type
        self.old_trade = None
        self.old_task = None

    def __enter__(self):
        # 保存旧上下文，设置新上下文
        self.old_trade = getattr(local_data, 'trade_no', None)
        self.old_task = getattr(local_data, 'task_type', None)
        local_data.trade_no = self.trade_no
        local_data.task_type = self.task_type

    def __exit__(self, exc_type, exc_val, exc_tb):
        # 退出时恢复旧上下文
        local_data.trade_no = self.old_trade
        local_data.task_type = self.old_task


# 保留你原有的LineCountRotatingFileHandler（无需修改）
class LineCountRotatingFileHandler(logging.FileHandler):
    """原有逻辑不变，已支持错误日志分割和邮件告警"""
    def __init__(self, filename, max_lines=5000, backup_count=10, encoding=None, delay=False):
        if not os.path.isabs(filename):
            filename = os.path.join(settings.BASE_DIR, filename)
        super().__init__(filename, mode='a', encoding=encoding, delay=delay)
        self.max_lines = max_lines
        self.backup_count = backup_count
        self.error_log_path = f"{os.path.splitext(filename)[0]}_error.log"

    # 以下方法保持不变...
    def emit(self, record):
        try:
            super().emit(record)
            if record.levelno >= logging.ERROR:
                self._write_error_log(record)
                self._send_error_email_async(record)
            self._rotate_if_needed()
        except Exception:
            self.handleError(record)

    def _write_error_log(self, record):
        error_msg = self.formatter.format(record) + "\n"
        with open(self.error_log_path, 'a', encoding=self.encoding) as f:
            f.write(error_msg)
        self._rotate_error_log_if_needed()

    def _rotate_error_log_if_needed(self):
        if not os.path.exists(self.error_log_path):
            return
        original_path = self.baseFilename
        self.baseFilename = self.error_log_path
        self._rotate_if_needed()
        self.baseFilename = original_path

    def _send_error_email_async(self, record):
        Thread(target=self._send_error_email, args=(record,)).start()

    def _send_error_email(self, record):
        try:
            error_traceback = ""
            if record.exc_info:
                error_traceback = ''.join(traceback.format_exception(*record.exc_info))
            html_content = f'''
            <div style="font-family:Arial,sans-serif;max-width:800px;margin:0 auto;padding:20px;border:1px solid #eee;border-radius:8px;">
                <h2 style="color:#d32f2f;margin-bottom:20px;">系统错误告警</h2>
                <table style="width:100%;border-collapse:collapse;margin-bottom:15px;">
                    <tr style="background:#f5f5f5;">
                        <td style="padding:8px;border:1px solid #ddd;font-weight:bold;">发生时间</td>
                        <td style="padding:8px;border:1px solid #ddd;">{self.formatter.formatTime(record, self.formatter.datefmt)}</td>
                    </tr>
                    <tr>
                        <td style="padding:8px;border:1px solid #ddd;font-weight:bold;">订单号</td>
                        <td style="padding:8px;border:1px solid #ddd;">{getattr(record, 'trade_no', 'unknown')}</td>  <!-- 新增：显示订单号 -->
                    </tr>
                    <tr style="background:#f5f5f5;">
                        <td style="padding:8px;border:1px solid #ddd;font-weight:bold;">任务类型</td>
                        <td style="padding:8px;border:1px solid #ddd;">{getattr(record, 'task_type', 'unknown')}</td>  <!-- 新增：显示任务类型 -->
                    </tr>
                    <tr>
                        <td style="padding:8px;border:1px solid #ddd;font-weight:bold;">错误级别</td>
                        <td style="padding:8px;border:1px solid #ddd;color:#d32f2f;">{record.levelname}</td>
                    </tr>
                    <tr style="background:#f5f5f5;">
                        <td style="padding:8px;border:1px solid #ddd;font-weight:bold;">错误模块</td>
                        <td style="padding:8px;border:1px solid #ddd;">{record.module}:{record.lineno}行</td>
                    </tr>
                    <tr>
                        <td style="padding:8px;border:1px solid #ddd;font-weight:bold;">错误信息</td>
                        <td style="padding:8px;border:1px solid #ddd;">{record.getMessage()}</td>
                    </tr>
                </table>
                <div style="margin-top:20px;">
                    <h4 style="margin-bottom:8px;">错误堆栈：</h4>
                    <pre style="background:#fafafa;padding:15px;border-radius:4px;border:1px solid #eee;white-space:pre-wrap;word-break:break-all;">
{error_traceback}
                    </pre>
                </div>
            </div>
            '''
            email_subject = f"【系统错误告警】{record.task_type}@{record.trade_no}：{record.getMessage()[:30]}"  # 优化标题
            success = send_generic_email(
                to_email=settings.ERROR_EMAIL_RECIPIENTS[0],
                subject=email_subject,
                html_content=html_content
            )
            if not success:
                raise Exception("通用邮件函数返回发送失败状态")
        except Exception as e:
            fail_msg = f"[{self.formatter.formatTime(record)}] 发送错误邮件失败：{str(e)}\n"
            with open(self.error_log_path, 'a', encoding=self.encoding) as f:
                f.write(fail_msg)

    def _rotate_if_needed(self):
        log_path = self.baseFilename
        if not os.path.exists(log_path):
            return
        try:
            with open(log_path, 'r', encoding=self.encoding) as f:
                current_lines = sum(1 for _ in f)
        except Exception as e:
            print(f"统计日志行数失败：{e}")
            return
        if current_lines > self.max_lines:
            keep_lines = self.max_lines - 2000
            if keep_lines < 1000:
                keep_lines = 1000
            with open(log_path, 'r', encoding=self.encoding) as f:
                lines = f.readlines()
            if len(lines) > keep_lines:
                lines = lines[-keep_lines:]
            with open(log_path, 'w', encoding=self.encoding) as f:
                f.writelines(lines)
            self._rotate_backup()

    def _rotate_backup(self):
        log_path = self.baseFilename
        for i in range(self.backup_count - 1, 0, -1):
            src = f"{log_path}.{i}"
            dst = f"{log_path}.{i + 1}"
            if os.path.exists(src):
                if os.path.exists(dst):
                    os.remove(dst)
                os.rename(src, dst)
        if os.path.exists(log_path):
            os.rename(log_path, f"{log_path}.1")