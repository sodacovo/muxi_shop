import os
from celery import Celery
from celery.schedules import crontab  

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'muxi_shop_api2.settings.settings_dev')

app = Celery('muxi_shop_api2')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


app.conf.beat_schedule = {
    'update-celery-queue-metrics': {
        'task': 'order.tasks.update_celery_queue_metrics',
        'schedule': crontab(minute=0), 
    },
    'cancel-unpaid-orders': {
        'task': 'order.tasks.cancel_unpaid_orders',
        'schedule': crontab(minute=0),  
    },
    # 数据分析缓存刷新任务（每小时整点执行，和其他任务同步）
    'refresh-analytics-cache': {
        'task': 'analytics.tasks.refresh-analytics-cache',
        'schedule': crontab(minute=0), 
    },
}


app.conf.update(
    beat_logger='celery.beat',
    worker_logger='celery.worker',
    log_level='INFO',
)