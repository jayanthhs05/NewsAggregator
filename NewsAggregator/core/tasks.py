from celery import shared_task
from .models import NewsSource, Article
from .utils.scrapers import scrape_apnews
from .utils.clustering import cluster_recent_articles
from .utils.recommendations import build_tfidf_matrix
from .utils.article_summarizer import summarize_article
from .utils.fake_news_detector import detect_fake_news
from .utils.translation import translate_article_content
from libretranslatepy import LibreTranslateAPI
from django.conf import settings
import logging
from celery.result import AsyncResult

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def translate_article_content(self, article_id, target_lang):
    try:
        lt = LibreTranslateAPI(settings.LIBRETRANSLATE_API)
        article = Article.objects.get(id=article_id)
        content = article.processed_content or article.raw_content
        if not content:
            raise ValueError("No content to translate")
            
        chunk_size = 5000
        chunks = [content[i:i+chunk_size]
            for i in range(0, len(content), chunk_size)]
        translated_chunks = []
        for chunk in chunks:
            translated = lt.translate(
                q=chunk,
                source="en",
                target=target_lang,
                timeout=settings.LIBRETRANSLATE_TIMEOUT
            )
            translated_chunks.append(translated)
        article.translated_content = " ".join(translated_chunks)
        article.save()
        return True
    except Exception as e:
        logger.error(f"Translation failed: {str(e)}")
        self.retry(countdown=30, exc=e)
        return False

@shared_task
def check_translation_status(task_id):
    task = AsyncResult(task_id)
    return {
        'status': task.status,
        'result': task.result
    }


@shared_task(rate_limit="5/m")
def scrape_articles():
    for source in NewsSource.objects.filter(is_active=True):
        if "apnews" in source.base_url:
            articles = scrape_apnews(source.base_url)

        for article_data in articles:
            Article.objects.update_or_create(
                source=source,
                title=article_data["title"],
                defaults={
                    "raw_content": article_data["content"],
                    "publication_date": article_data["date"],
                },
            )


@shared_task(rate_limit="1/h")
def update_event_clusters():
    cluster_recent_articles(days=7)


@shared_task(rate_limit="1/h")
def update_tfidf_matrix():
    build_tfidf_matrix()


@shared_task
def update_faiss_index():

    from .utils.recommendations import build_and_save_faiss_index

    build_and_save_faiss_index()


@shared_task
def process_article_summary(article_id):
    try:
        article = Article.objects.get(id=article_id)
        summary = summarize_article(article.content)
        article.article_summary = summary
        article.save()
        return f"Successfully summarized article {article_id}"
    except Article.DoesNotExist:
        return f"Article {article_id} does not exist"
    except Exception as e:
        return f"Error summarizing article {article_id}: {str(e)}"


@shared_task
def process_fake_news_detection(article_id):
    try:
        article = Article.objects.get(id=article_id)
        is_fake, confidence = detect_fake_news(article.content)
        article.is_fake_news = is_fake
        article.fake_news_confidence = confidence
        article.save()
        return f"Successfully processed fake news detection for article {article_id}"
    except Article.DoesNotExist:
        return f"Article {article_id} does not exist"
    except Exception as e:
        return (
            f"Error processing fake news detection for article {article_id}: {str(e)}"
        )
