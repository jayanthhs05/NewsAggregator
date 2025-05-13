import os
from celery import Celery
from core.tasks import update_event_clusters, update_tfidf_matrix
from celery.schedules import crontab
import multiprocessing

# Set the multiprocessing start method to 'spawn'
multiprocessing.set_start_method('spawn', force=True)

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'NewsAggregator.settings')

app = Celery('NewsAggregator')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
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

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')