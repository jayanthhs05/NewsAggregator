from django.urls import path, include
from . import views

urlpatterns = [
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("signup/", views.signup, name="signup"),
    path('article/<int:pk>/', views.ArticleDetailView.as_view(), name='article_detail'),
    path('article/<int:article_id>/summarize/', views.generate_article_summary, name='generate_summary'),
    path('article/<int:article_id>/detect-fake-news/', views.detect_article_fake_news, name='detect_fake_news'),
    path('batch-process/', views.batch_process_articles, name='batch_process'),
]
