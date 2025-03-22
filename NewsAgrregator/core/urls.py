from django.urls import path, include
from . import views

urlpatterns = [
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("signup/", views.signup, name="signup"),
]
