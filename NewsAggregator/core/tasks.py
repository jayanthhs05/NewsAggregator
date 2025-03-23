from celery import shared_task
from .models import NewsSource, Article
from .utils.scrapers import scrape_apnews, scrape_reuters
from .utils.clustering import cluster_recent_articles
from .utils.recommendations import build_tfidf_matrix


@shared_task(rate_limit="5/m")
def scrape_articles():
    for source in NewsSource.objects.filter(is_active=True):
        if "apnews" in source.base_url:
            articles = scrape_apnews(source.base_url)
        elif "reuters" in source.base_url:
            articles = scrape_reuters(source.base_url)

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


@shared_task(rate_limit="1/d")
def update_tfidf_matrix():
    build_tfidf_matrix()


@shared_task
def update_faiss_index():

    from .utils.recommendations import build_and_save_faiss_index

    build_and_save_faiss_index()
