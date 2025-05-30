from django.urls import path, include
from . import views

urlpatterns = [
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("signup/", views.signup, name="signup"),
    path('article/<int:article_id>/', views.article_detail, name='article_detail'),
    path('article/<int:article_id>/summarize/', views.generate_article_summary, name='generate_summary'),
    path('article/<int:article_id>/detect-fake-news/', views.detect_article_fake_news, name='detect_fake_news'),
    path('batch-process/', views.batch_process_articles, name='batch_process'),
    path('article/<int:article_id>/translate/', views.translate_article_view, name='translate-article'),
    path('event-clusters/', views.event_clusters, name='event_clusters'),
    path('tasks/status/<str:task_id>/', views.task_status, name='task_status'),
    path('article/<int:article_id>/content/', views.article_content, name='article_content'),
    path('personalized-feed/', views.personalized_feed, name='personalized_feed'),
]
