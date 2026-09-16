import logging
import traceback
from django.http import JsonResponse
from django.conf import settings


logger = logging.getLogger('app')

class GlobalErrorMiddleware:
    """全局异常捕获中间件：捕获所有未处理的错误，记录日志并返回友好响应"""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 正常处理请求
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        """当视图抛出未处理的异常时，自动触发此方法"""
        # 1. 构建详细的错误信息（包含请求路径、参数、堆栈）
        error_info = (
            f"【请求信息】\n"
            f"URL: {request.path}\n"
            f"方法: {request.method}\n"
            f"GET参数: {request.GET.dict()}\n"
            f"POST参数: {request.POST.dict() if request.method == 'POST' else '无'}\n\n"
            f"【错误信息】\n"
            f"类型: {type(exception).__name__}\n"
            f"内容: {str(exception)}\n\n"
            f"【错误堆栈】\n"
            f"{traceback.format_exc()}"  # 完整的错误堆栈，方便定位问题
        )

        # 2. 记录错误到日志（会触发邮件告警）
        logger.error(error_info)

        # 3. 返回友好的JSON响应（不暴露详细堆栈给前端）
        return JsonResponse({
            'code': 500,
            'message': '服务器内部错误，请稍后重试',
            'detail': str(exception) if settings.DEBUG else '生产环境不显示详细错误'
        }, status=500)