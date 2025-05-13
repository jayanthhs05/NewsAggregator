from celery import shared_task
from .models import NewsSource, Article
from .utils.scrapers import get_scraper_for_url, parse_date
from .utils.clustering import cluster_recent_articles
from .utils.recommendations import build_tfidf_matrix
from .utils.article_summarizer import summarize_article
from .utils.fake_news_detector import detect_fake_news
from .utils.translation import translate_article_content
from libretranslatepy import LibreTranslateAPI
from django.conf import settings
import logging
from celery.result import AsyncResult
import multiprocessing

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def translate_article_content(self, article_id, target_lang):
    try:
        lt = LibreTranslateAPI(settings.LIBRETRANSLATE_API)
        article = Article.objects.get(id=article_id)
        content = article.processed_content or article.raw_content
        if not content:
            raise ValueError("No content to translate")

        logger.info(f"Starting translation of article {article_id} to {target_lang}")
        logger.info(f"Using LibreTranslate API at: {settings.LIBRETRANSLATE_API}")

        chunk_size = 5000
        chunks = [
            content[i : i + chunk_size] for i in range(0, len(content), chunk_size)
        ]
        translated_chunks = []
        for i, chunk in enumerate(chunks):
            logger.info(f"Translating chunk {i+1}/{len(chunks)}")
            try:
                translated = lt.translate(
                    q=chunk,
                    source="en",
                    target=target_lang,
                    timeout=settings.LIBRETRANSLATE_TIMEOUT,
                )
                if not translated or translated == chunk:
                    logger.warning(f"Translation returned same content for chunk {i+1}")
                    continue
                translated_chunks.append(translated)
            except Exception as chunk_error:
                logger.error(f"Error translating chunk {i+1}: {str(chunk_error)}")
                raise

        if not translated_chunks:
            raise ValueError("No content was successfully translated")

        translated_content = " ".join(translated_chunks)
        logger.info(f"Successfully translated article {article_id}")
        
        article.translated_content = translated_content
        article.save()
        return translated_content
    except Exception as e:
        logger.error(f"Translation failed: {str(e)}")
        self.retry(countdown=30, exc=e)
        return f"Translation failed: {str(e)}"


@shared_task
def check_translation_status(task_id):
    task = AsyncResult(task_id)
    return {"status": task.status, "result": task.result}


@shared_task(rate_limit="5/m")
def scrape_articles():
    """
    Celery task to scrape articles from active news sources.
    """
    import logging

    logger = logging.getLogger(__name__)
    logger.info("Starting article scraping task")

    active_sources = NewsSource.objects.filter(is_active=True)
    logger.info(f"Found {active_sources.count()} active news sources")

    for source in active_sources:
        try:
            logger.info(f"Processing source: {source.name} ({source.base_url})")
            scraper = get_scraper_for_url(source.base_url)

            if not scraper:
                logger.warning(
                    f"No scraper found for {source.name} ({source.base_url})"
                )
                continue

            logger.info(f"Using scraper for {source.name}")
            articles = scraper(source.base_url)

            if not articles:
                logger.warning(f"No articles found from {source.name}")
                continue

            logger.info(f"Found {len(articles)} articles from {source.name}")
            new_count = 0
            for article_data in articles:
                try:
                    existing = Article.objects.filter(
                        source=source, title=article_data["title"]
                    ).exists()

                    if not existing:
                        Article.objects.create(
                            source=source,
                            title=article_data["title"],
                            raw_content=article_data["content"],
                            processed_content=article_data["content"],
                            publication_date=parse_date(article_data["date"]),
                        )
                        new_count += 1
                        logger.info(f"Added new article: {article_data['title']}")
                except Exception as e:
                    logger.error(
                        f"Error saving article '{article_data.get('title', 'Unknown')}': {str(e)}"
                    )

            logger.info(
                f"Scraped {len(articles)} articles from {source.name}, added {new_count} new articles"
            )

        except Exception as e:
            logger.error(f"Error scraping {source.name}: {str(e)}")
            logger.exception(e)  # This will log the full traceback

    logger.info("Finished article scraping task")


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
