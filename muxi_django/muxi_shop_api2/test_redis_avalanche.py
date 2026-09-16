from django.conf import settings
import sys
class MockCeleryModule:
    class MockApp:
        pass
    app = MockApp()
sys.modules['muxi_shop_api2.celery'] = MockCeleryModule()
sys.modules['celery'] = MockCeleryModule()

# 导入必要模块（无Goods模型导入）
import os
import random
import django
from django.db import connections  # 原生SQL查询
from django.core.cache import caches

# 配置Django环境
sys.path.append("/www/wwwroot/muxi_django")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "muxi_shop_api2.settings.settings_dev")
django.setup()

# 获取Redis测试库实例
test_cache = caches["test_redis"]

# 批量添加商品缓存（用原生SQL查询，不导入Goods模型）
# 你的商品ID范围：1270-1276
goods_ids = range(1270, 1276)
with connections['default'].cursor() as cursor:
    # 原生SQL查询：获取存在的商品数据（id、name、p_price）
    cursor.execute("""
        SELECT id, name, p_price FROM goods WHERE id IN %s
    """, [tuple(goods_ids)])  # 批量查询，效率更高
    rows = cursor.fetchall()  # 获取所有符合条件的商品

    for row in rows:
        goods_id, name, p_price = row
        # 组装商品数据（和之前一致）
        goods_data = {
            "id": goods_id,
            "name": name,
            "price": float(p_price) if p_price else 0.0  # 处理空价格
        }
        # 随机过期时间：1小时+0-5分钟
        expire_time = 3600 + random.randint(0, 300)
        cache_key = f"test:goods:{goods_id}"
        test_cache.set(cache_key, goods_data, expire_time)
        print(f"✅ 商品{goods_id}缓存成功，过期时间：{expire_time}秒，缓存key：{cache_key}")
        print(f"📌 缓存库配置：{settings.CACHES['test_redis']['LOCATION']}")  # 正确获取配置
        print(f"📌 实际写入的key：{cache_key}")  # 打印key名称
        print(f"✅ 商品{goods_id}缓存成功，过期时间：{expire_time}秒，缓存key：{cache_key}")

    # 输出不存在的商品ID
    existing_ids = [row[0] for row in rows]
    non_existing_ids = [gid for gid in goods_ids if gid not in existing_ids]
    for gid in non_existing_ids:
        print(f"❌ 商品{gid}不存在，跳过")