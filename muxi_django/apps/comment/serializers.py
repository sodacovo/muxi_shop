"""
序列化（Serialization）
就是把“Python 对象”转换成“便于传输或存储的格式”（在 Web 里通常是 JSON 字符串）。
反序列化（Deserialization）
则正好相反：把 JSON 等外部格式转回 Python 对象。

"""

from rest_framework import serializers

from comment.models import Comment
from django.conf import settings


class CommentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Comment
        fields = '__all__'