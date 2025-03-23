from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import TemplateView, DetailView
from .forms import CustomUserCreationForm
from .models import *
from django.contrib.auth.decorators import login_required
from .utils.recommendations import get_content_based_recommendations, get_faiss_recommendations


class DashboardView(TemplateView):
    template_name = "core/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["articles"] = Article.objects.all().order_by("-publication_date")[:50]
        return context


class CustomLoginView(LoginView):
    template_name = "registration/login.html"
    redirect_authenticated_user = True


class ArticleDetailView(DetailView):
    model = Article
    template_name = 'core/article_detail.html'
    context_object_name = 'article'


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


@login_required
def personalized_feed(request):
    use_sbert = request.GET.get('use_sbert', 'false').lower() == 'true'
    articles = get_faiss_recommendations(request.user.id, 20) if use_sbert else get_content_based_recommendations(request.user.id, 20)
    return render(request, 'core/personalized_feed.html', {'articles': articles})

@login_required
def article_detail(request, article_id):
    article = Article.objects.get(id=article_id)
    UserActivity.objects.create(user=request.user, article=article, activity_type='read')
    recommendations = get_faiss_recommendations(request.user.id, 5) if request.GET.get('use_sbert') else get_content_based_recommendations(request.user.id, 5)
    return render(request, 'core/article_detail.html', {'article': article, 'recommendations': recommendations})

def event_clusters(request):
    return render(request, 'core/event_clusters.html', {'clusters': EventCluster.objects.all().prefetch_related('articles')})

