from django.contrib import admin
from .models import CustomUser, NewsSource, Article


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "source", "publication_date", "is_verified")
    list_filter = ("source", "is_verified")
    search_fields = ("title", "raw_content")


admin.site.register(CustomUser)
admin.site.register(NewsSource)