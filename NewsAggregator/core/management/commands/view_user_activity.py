from django.core.management.base import BaseCommand
from core.models import UserActivity, Article, CustomUser
from django.db.models import Count
from django.utils import timezone

class Command(BaseCommand):
    help = 'View user activity and personalized feed statistics'

    def handle(self, *args, **options):
        # Get all users
        users = CustomUser.objects.all()
        
        for user in users:
            self.stdout.write(f"\nUser: {user.username}")
            
            # Get user's reading activity
            activities = UserActivity.objects.filter(
                user=user,
                activity_type='read'
            ).select_related('article').order_by('-timestamp')
            
            if activities.exists():
                self.stdout.write("\nRecent reading activity:")
                for activity in activities[:5]:  # Show last 5 activities
                    self.stdout.write(
                        f"- {activity.timestamp}: Read article '{activity.article.title}'"
                    )
                
                # Get article topics
                article_ids = activities.values_list('article_id', flat=True)
                articles = Article.objects.filter(id__in=article_ids)
                
                self.stdout.write("\nArticle topics:")
                for article in articles[:5]:
                    self.stdout.write(f"- {article.title}")
            else:
                self.stdout.write("No reading activity found for this user")
            
            self.stdout.write("\n" + "="*50) 