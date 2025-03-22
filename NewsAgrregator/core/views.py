from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import TemplateView
from .forms import CustomUserCreationForm
from .models import *


class DashboardView(TemplateView):
    template_name = "core/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["articles"] = Article.objects.filter(
            source__in=self.request.user.preferred_sources.all()
        ).order_by("-publication_date")[:50]
        return context


class CustomLoginView(LoginView):
    template_name = "registration/login.html"
    redirect_authenticated_user = True


def signup(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("dashboard")
    else:
        form = CustomUserCreationForm()
    return render(request, "registration/signup.html", {"form": form})
