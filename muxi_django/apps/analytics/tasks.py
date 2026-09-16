from celery import shared_task
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta

@shared_task
def refresh_analytics_cache():
    """每1小时刷新所有分析缓存（修复重复定义+缓存清除不彻底）"""
    # 1. 定义需要清除的缓存前缀和时间范围
    cache_prefixes = [
        'sales_analysis_',
        'order_status_analysis_',
        'seckill_analysis_'
    ]
    time_ranges = ['1d', '7d', '30d']
    
    # 2. 生成「今天+昨天」的日期前缀（覆盖24小时内的所有缓存）
    # 原因：缓存Key包含日期+小时，可能跨天，需覆盖昨天和今天的所有小时
    today = timezone.now().strftime("%Y%m%d")
    yesterday = (timezone.now() - timedelta(days=1)).strftime("%Y%m%d")
    date_prefixes = [today, yesterday]
    
    # 3. 循环清除所有相关缓存（精准匹配所有可能的Key）
    deleted_keys = 0
    for prefix in cache_prefixes:
        for time_range in time_ranges:
            for date in date_prefixes:
                # 匹配格式：前缀_时间范围_日期+任意小时（如 sales_analysis_7d_20251127*）
                # 注意：Redis缓存支持通配符 *，其他缓存（如Memcached）也兼容该语法
                key_pattern = f"{prefix}{time_range}_{date}*"
                # 获取所有匹配的Key并删除
                keys = cache.keys(key_pattern)
                if keys:
                    cache.delete_many(keys)
                    deleted_keys += len(keys)
    
    # 4. 打印日志（方便Celery日志排查）
    print(f"Analytics cache refreshed successfully! Deleted {deleted_keys} old cache keys.")
    return f"Refreshed {deleted_keys} cache keys"