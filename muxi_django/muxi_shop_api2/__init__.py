
import pymysql
# 让 Django 把 pymysql 当作 MySQLdb 使用
pymysql.install_as_MySQLdb()

from .celery import app as celery_app
__all__ = ('celery_app',)