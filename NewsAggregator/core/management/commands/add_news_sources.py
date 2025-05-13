from django.core.management.base import BaseCommand
from core.models import NewsSource


class Command(BaseCommand):
    help = "Add predefined news sources to the database"

    def handle(self, *args, **options):

        news_sources = [
            {
                "name": "NPR",
                "base_url": "https://www.npr.org/sections/news/",
                "scraping_interval": 1800,
            },
            {
                "name": "The Guardian",
                "base_url": "https://www.theguardian.com/international",
                "scraping_interval": 1800,
            },
            {
                "name": "Al Jazeera English",
                "base_url": "https://www.aljazeera.com",
                "scraping_interval": 1800,
            },
            {
                "name": "USA Today",
                "base_url": "https://www.usatoday.com/news/",
                "scraping_interval": 1800,
            },
            {
                "name": "ABC News (AU)",
                "base_url": "https://www.abc.net.au/news/",
                "scraping_interval": 1800,
            },
        ]

        for source_data in news_sources:
            source, created = NewsSource.objects.get_or_create(
                name=source_data["name"],
                defaults={
                    "base_url": source_data["base_url"],
                    "scraping_interval": source_data["scraping_interval"],
                    "is_active": True,
                },
            )

            status = "Created" if created else "Already exists"
            self.stdout.write(
                self.style.SUCCESS(f"{status}: {source.name} ({source.base_url})")
            )

        count = NewsSource.objects.count()
        self.stdout.write(self.style.SUCCESS(f"Total news sources: {count}"))
