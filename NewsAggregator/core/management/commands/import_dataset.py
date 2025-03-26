from django.core.management.base import BaseCommand
from core.models import Article, NewsSource
from dateutil import parser
import json

class Command(BaseCommand):
    help = 'Imports BBC news dataset'

    def handle(self, *args, **options):
        with open('data/BBC-news.json') as f:
            data = json.load(f)
            
            for item in data:
                source, _ = NewsSource.objects.get_or_create(
                    name=item.get('publisher', 'BBC'),
                    defaults={
                        'base_url': 'https://www.bbc.com'
                    }
                )

                Article.objects.create(
                    source= source,
                    title= item['headline'],
                    raw_content= item['content'],
                    processed_content=item['content'],
                    publication_date= parser.parse(item['publication_date']),
                )
        self.stdout.write(self.style.SUCCESS(f'Successfully imported {len(data)} articles'))
