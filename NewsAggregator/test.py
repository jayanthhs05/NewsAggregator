import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "NewsAggregator.settings")
django.setup()

from core.tasks import translate_article_content
from core.models import Article

def test_translation_task():
    article = Article.objects.first()
    if article:
        print(f"Testing translation for article ID: {article.id}")
        task = translate_article_content.delay(article.id, 'es')
        print(f"Task ID: {task.id}")
        print("Check Celery logs to see task execution")
    else:
        print("No articles found in database")

if __name__ == "__main__":
    test_translation_task()
