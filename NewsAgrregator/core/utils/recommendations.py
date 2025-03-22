import numpy as np
import torch
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from ..models import Article, UserActivity

def build_tfidf_matrix():
    articles = Article.objects.filter(processed_content__isnull=False)
    article_ids = [article.id for article in articles]
    contents = [article.processed_content for article in articles]
    vectorizer = TfidfVectorizer(stop_words='english', max_features=5000)
    tfidf_matrix = vectorizer.fit_transform(contents)
    return article_ids, tfidf_matrix, vectorizer

def get_content_based_recommendations(user_id, n=10):
    read_articles = UserActivity.objects.filter(user_id=user_id, activity_type='read').values_list('article_id', flat=True)
    if not read_articles: 
        return Article.objects.order_by('-publication_date')[:n]
    article_ids, tfidf_matrix, _ = build_tfidf_matrix()
    read_indices = [article_ids.index(aid) for aid in read_articles if aid in article_ids]
    if not read_indices: 
        return Article.objects.order_by('-publication_date')[:n]
    user_profile = tfidf_matrix[read_indices].mean(axis=0)
    cosine_similarities = cosine_similarity(user_profile, tfidf_matrix).flatten()
    similar_indices = cosine_similarities.argsort()[-(n+len(read_indices)):][::-1]
    recommended_indices = [idx for idx in similar_indices if article_ids[idx] not in read_articles][:n]
    return Article.objects.filter(id__in=[article_ids[idx] for idx in recommended_indices])

def get_sentence_bert_recommendations(user_id, n=10):
    read_activities = UserActivity.objects.filter(user_id=user_id, activity_type='read').select_related('article')
    if not read_activities: 
        return Article.objects.order_by('-publication_date')[:n]
    read_articles = [activity.article for activity in read_activities if activity.article.processed_content]
    all_articles = list(Article.objects.filter(processed_content__isnull=False))
    model = SentenceTransformer('paraphrase-MiniLM-L6-v2')
    article_contents = [article.processed_content for article in all_articles]
    all_embeddings = model.encode(article_contents, convert_to_tensor=True)
    read_indices = [all_articles.index(article) for article in read_articles if article in all_articles]
    read_embeddings = all_embeddings[read_indices]
    user_profile = torch.mean(read_embeddings, dim=0)
    cosine_similarities = torch.nn.functional.cosine_similarity(user_profile.unsqueeze(0), all_embeddings).numpy()
    read_article_ids = {article.id for article in read_articles}
    similar_indices = cosine_similarities.argsort()[::-1]
    recommended_indices = [idx for idx in similar_indices if all_articles[idx].id not in read_article_ids][:n]
    return [all_articles[idx] for idx in recommended_indices]
