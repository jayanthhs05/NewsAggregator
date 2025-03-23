from django.db import models
from django.contrib.auth.models import AbstractUser


class CustomUser(AbstractUser):
    PREFERRED_LANGUAGES = [("en", "English"), ("es", "Spanish"), ("fr", "French")]
    preferred_sources = models.ManyToManyField("NewsSource")
    language_preference = models.CharField(
        max_length=2, choices=PREFERRED_LANGUAGES, default="en"
    )
    newsletter_subscription = models.BooleanField(default=True)


class NewsSource(models.Model):
    name = models.CharField(max_length=200)
    base_url = models.URLField()
    scraping_interval = models.PositiveIntegerField(default=3600)
    is_active = models.BooleanField(default=True)


class Article(models.Model):
    source = models.ForeignKey(NewsSource, on_delete=models.CASCADE)
    title = models.CharField(max_length=500)
    raw_content = models.TextField()
    processed_content = models.TextField(null=True)
    summary = models.TextField(null=True)
    translated_content = models.TextField(null=True)
    publication_date = models.DateTimeField()
    is_verified = models.BooleanField(default=False)
    verification_score = models.FloatField(null=True)
    is_fake_news = models.BooleanField(default=False, null=True)
    fake_news_confidence = models.FloatField(null=True, blank=True)
    article_summary = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class EventCluster(models.Model):
    name = models.CharField(max_length=200)
    articles = models.ManyToManyField('Article', related_name='event_clusters')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class UserActivity(models.Model):
    ACTIVITY_TYPES = [
        ('read', 'Read Article'), 
        ('click', 'Clicked Link'),
        ('share', 'Shared Article'),
        ('save', 'Saved Article'),
    ]
    user = models.ForeignKey('CustomUser', on_delete=models.CASCADE)
    article = models.ForeignKey('Article', on_delete=models.CASCADE)
    activity_type = models.CharField(max_length=10, choices=ACTIVITY_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)