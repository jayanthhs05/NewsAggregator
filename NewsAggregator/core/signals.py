from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Article

@receiver(post_save, sender=Article)
def handle_article_translation(sender, instance, created, **kwargs):
    if created and instance.raw_content:
        from .tasks import translate_article_content
        translate_article_content.delay(instance.id, target_lang='en')
