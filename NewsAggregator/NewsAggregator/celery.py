import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "NewsAggregator.settings")

app = Celery("NewsAggregator")
app.config_from_object("core.celery_config")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "update-faiss-index-daily": {
        "task": "core.tasks.update_faiss_index",
        "schedule": crontab(hour=3, minute=0),
    },
    "scrape-articles-hourly": {
        "task": "core.tasks.scrape_articles",
        "schedule": crontab(minute=0),  # Run every hour
    }
}
