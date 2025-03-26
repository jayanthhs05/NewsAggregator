from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib import messages
from .utils.article_summarizer import summarize_article
from .utils.fake_news_detector import detect_fake_news
from django.urls import reverse_lazy
from django.views.generic import TemplateView, DetailView
from .forms import CustomUserCreationForm
from .models import *
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from .tasks import translate_article_task
from django.contrib.auth.decorators import login_required
from .utils.recommendations import (
    get_content_based_recommendations,
    get_faiss_recommendations,
)
from .tasks import process_article_summary, process_fake_news_detection


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
    template_name = "core/article_detail.html"
    context_object_name = "article"


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
    # use_sbert = request.GET.get("use_sbert", "false").lower() == "true"
    # articles = (
    #     get_faiss_recommendations(request.user.id, 20)
    #     if use_sbert
    #     else get_content_based_recommendations(request.user.id, 20)
    # )
    articles = Article.objects.all()
    return render(request, "core/personalized_feed.html", {"articles": articles})


@login_required
def article_detail(request, article_id):
    article = Article.objects.get(id=article_id)
    UserActivity.objects.create(
        user=request.user, article=article, activity_type="read"
    )
    recommendations = (
        get_faiss_recommendations(request.user.id, 5)
        if request.GET.get("use_sbert")
        else get_content_based_recommendations(request.user.id, 5)
    )
    return render(
        request,
        "core/article_detail.html",
        {"article": article, "recommendations": recommendations},
    )


def event_clusters(request):
    return render(
        request,
        "core/event_clusters.html",
        {"clusters": EventCluster.objects.all().prefetch_related("articles")},
    )


def generate_article_summary(request, article_id):
    article = get_object_or_404(Article, id=article_id)
    summary = summarize_article(article.content)
    article.article_summary = summary
    article.save()
    messages.success(request, "Article summary generated successfully!")
    return redirect("article_detail", article_id=article.id)


def detect_article_fake_news(request, article_id):
    article = get_object_or_404(Article, id=article_id)
    is_fake, confidence = detect_fake_news(article.content)
    article.is_fake_news = is_fake
    article.fake_news_confidence = confidence
    article.save()
    messages.success(request, "Fake news detection completed!")
    return redirect("article_detail", article_id=article.id)


def batch_process_articles(request):
    if request.method == "POST":
        article_ids = request.POST.getlist("article_ids")
        process_type = request.POST.get("process_type")

        for article_id in article_ids:
            if process_type == "summary":
                process_article_summary.delay(int(article_id))
            elif process_type == "fake_news":
                process_fake_news_detection.delay(int(article_id))

        messages.success(
            request,
            f"Batch processing of {len(article_ids)} articles has been started!",
        )
        return redirect("dashboard")

    articles = Article.objects.all()
    return render(request, "core/batch_process.html", {"articles": articles})

@require_http_methods(["POST"])
def translate_article_view(request, article_id):
    target_lang = request.POST.get('target_lang', 'en')
    task = translate_article_task.delay(article_id, target_lang)
    return JsonResponse({
        'task_id': task.id,
        'status_url': f'/tasks/status/{task.id}/'
    })