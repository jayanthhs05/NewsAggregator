from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Article
from .tasks import translate_article_task

@receiver(post_save, sender=Article)
def handle_article_translation(sender, instance, created, **kwargs):
    if created and instance.content:
        translate_article_task.delay(instance.id, target_lang='en')