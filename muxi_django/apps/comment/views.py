from django.http import JsonResponse
from django.shortcuts import render
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import CreateModelMixin, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin, \
    ListModelMixin
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSetMixin

from comment.models import Comment
from comment.serializers import CommentSerializer
from utils import ResponseMessage
from django.conf import settings
from django.http import HttpResponse


# ========== 新增：头像 URL 替换函数（核心） ==========
def replace_avatar_url(original_url):
    """
    兼容有/无 https:// 的 URL，替换为 Nginx 代理 URL
    """
    if not original_url:
        return "https://www.nwq1309.shop/default.png"
    
    # 统一处理：先去掉可能的 http/https 前缀，再匹配域名
    url_lower = original_url.lower()
    # 替换 misc.360buyimg.com（兼容有/无协议）
    if "misc.360buyimg.com" in url_lower:
        # 方式1：直接替换域名部分（不管有没有协议）
        return original_url.replace(
            "misc.360buyimg.com", 
            "www.nwq1309.shop/avatar-misc"
        ).replace("http://", "").replace("https://", "")
        # 最终生成：www.nwq1309.shop/avatar-misc/user/...
    elif "storage.360buyimg.com" in url_lower:
        return original_url.replace(
            "storage.360buyimg.com", 
            "www.nwq1309.shop/avatar-storage"
        ).replace("http://", "").replace("https://", "")
    return original_url

def test_settings(request):
    # 打印当前使用的settings文件路径
    return HttpResponse(f"当前运行的settings：{settings.SETTINGS_MODULE}")

# 有空了解一下继承顺序的问题
# Create your views here.
class CommentGenericAPIView(ViewSetMixin,GenericAPIView,
                            CreateModelMixin,
                            RetrieveModelMixin,
                            UpdateModelMixin,
                            DestroyModelMixin,
                            ListModelMixin):
    queryset = Comment.objects
    serializer_class = CommentSerializer

    def single(self, request, pk):
        return self.retrieve(request, pk)

    def my_list(self, request):
        if not request.user.get("status"):
            return JsonResponse(request.user, safe=False)
        return self.list(request)

    def edit(self, request, pk):
        return self.update(request, pk)

    def my_save(self, request):
        return self.create(request)

    def my_delete(self, request, pk):
        return self.destroy(request, pk)


class CommentAPIView(APIView):
    """评论列表接口（支持分页）"""

    def get(self, request):
        try:
            # 1. 获取并校验参数（原有逻辑不变）
            sku_id = request.GET.get('sku_id')
            page = request.GET.get('page', 1)
            if not sku_id:
                return ResponseMessage.CommentResponse.failed("缺少sku_id参数（商品原始SKU）")
            if not page.isdigit():
                return ResponseMessage.CommentResponse.failed("page参数必须是数字（如1、2）")
            page = int(page)
            page_size = 15
            start = (page - 1) * page_size
            end = page * page_size

            # 2. 查询评论（原有逻辑不变）
            queryset = Comment.objects.filter(
                sku_id=sku_id
            ).order_by('-create_time')[start:end]

            # 3. 序列化 + 替换头像 URL（核心修改）
            ser = CommentSerializer(queryset, many=True)
            comment_data = ser.data  # 序列化后的原始数据
            
            # 遍历每条评论，替换 user_image_url
            for comment in comment_data:
                if "user_image_url" in comment:
                    comment["user_image_url"] = replace_avatar_url(comment["user_image_url"])

            # 4. 返回处理后的数据（原有逻辑不变）
            return ResponseMessage.CommentResponse.success(comment_data)

        except Exception as e:
            return ResponseMessage.CommentResponse.failed(f"获取评论失败：{str(e)[:30]}")


class CommentCountAPIView(APIView):
    """评论总数接口"""
    def get(self, request):
        try:
            sku_id = request.GET.get('sku_id')
            if not sku_id:
                return ResponseMessage.CommentResponse.failed("缺少sku_id参数（商品原始SKU）")
            count = Comment.objects.filter(sku_id=sku_id).count()
            return ResponseMessage.CommentResponse.success(count)
        except Exception as e:
            return ResponseMessage.CommentResponse.failed(f"获取评论总数失败：{str(e)[:20]}")