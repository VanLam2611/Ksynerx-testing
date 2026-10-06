import os
from celery import Celery
from celery.schedules import crontab

app = Celery(
    'celery_task',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),
    include=['app.tasks.sync_tasks'],
)

app.conf.beat_schedule = {
    'sync-vietful-product-data': {
        'task': 'app.tasks.sync_tasks.sync_vietful_product_data',
        'schedule': crontab(hour=1, minute=0),
    },
}

app.conf.timezone = 'Asia/Ho_Chi_Minh' 