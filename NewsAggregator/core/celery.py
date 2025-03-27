from __future__ import absolute_import
from celery import Celery
from core.tasks import update_event_clusters, update_tfidf_matrix
from celery.schedules import crontab


app = Celery('core')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(3600, update_event_clusters.s())
    sender.add_periodic_task(86400, update_tfidf_matrix.s())

app.conf.beat_schedule = {
    'update-faiss-index-daily': {
        'task': 'core.tasks.update_faiss_index',
        'schedule': crontab(hour=3, minute=0),
    },
}

app.conf.task_routes = {
    'core.tasks.translate_article_content': {'queue': 'translations'},
}