from django.urls import path, include
from . import views

urlpatterns = [
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("signup/", views.signup, name="signup"),
    path('article/<int:pk>/', views.ArticleDetailView.as_view(), name='article_detail'),
]
