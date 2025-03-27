from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", RedirectView.as_view(url="/main/dashboard/", permanent=True)),
    path("accounts/", include("django.contrib.auth.urls")),
    path("main/", include("core.urls")),
]
