import numpy as np
import torch
import faiss
import os
import pickle
from django.conf import settings
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from ..models import Article, UserActivity


def build_tfidf_matrix():
    articles = Article.objects.filter(processed_content__isnull=False)
    article_ids = [article.id for article in articles]
    contents = [article.processed_content for article in articles]
    vectorizer = TfidfVectorizer(stop_words="english", max_features=5000)
    tfidf_matrix = vectorizer.fit_transform(contents)
    return article_ids, tfidf_matrix, vectorizer


def get_content_based_recommendations(user_id, n=10):
    read_articles = UserActivity.objects.filter(
        user_id=user_id, activity_type="read"
    ).values_list("article_id", flat=True)
    if not read_articles:
        return Article.objects.order_by("-publication_date")[:n]
    article_ids, tfidf_matrix, _ = build_tfidf_matrix()
    read_indices = [
        article_ids.index(aid) for aid in read_articles if aid in article_ids
    ]
    if not read_indices:
        return Article.objects.order_by("-publication_date")[:n]
    user_profile = tfidf_matrix[read_indices].mean(axis=0)
    cosine_similarities = cosine_similarity(user_profile, tfidf_matrix).flatten()
    similar_indices = cosine_similarities.argsort()[-(n + len(read_indices)) :][::-1]
    recommended_indices = [
        idx for idx in similar_indices if article_ids[idx] not in read_articles
    ][:n]
    return Article.objects.filter(
        id__in=[article_ids[idx] for idx in recommended_indices]
    )


def get_sentence_bert_recommendations(user_id, n=10):
    read_activities = UserActivity.objects.filter(
        user_id=user_id, activity_type="read"
    ).select_related("article")
    if not read_activities:
        return Article.objects.order_by("-publication_date")[:n]
    read_articles = [
        activity.article
        for activity in read_activities
        if activity.article.processed_content
    ]
    all_articles = list(Article.objects.filter(processed_content__isnull=False))
    model = SentenceTransformer("paraphrase-MiniLM-L6-v2")
    article_contents = [article.processed_content for article in all_articles]
    all_embeddings = model.encode(article_contents, convert_to_tensor=True)
    read_indices = [
        all_articles.index(article)
        for article in read_articles
        if article in all_articles
    ]
    read_embeddings = all_embeddings[read_indices]
    user_profile = torch.mean(read_embeddings, dim=0)
    cosine_similarities = torch.nn.functional.cosine_similarity(
        user_profile.unsqueeze(0), all_embeddings
    ).numpy()
    read_article_ids = {article.id for article in read_articles}
    similar_indices = cosine_similarities.argsort()[::-1]
    recommended_indices = [
        idx for idx in similar_indices if all_articles[idx].id not in read_article_ids
    ][:n]
    return [all_articles[idx] for idx in recommended_indices]


FAISS_INDEX_PATH = os.path.join(settings.BASE_DIR, "faiss_index")
FAISS_ARTICLES_PATH = os.path.join(settings.BASE_DIR, "faiss_articles.pkl")
FAISS_EMBEDDINGS_PATH = os.path.join(settings.BASE_DIR, "faiss_embeddings.npy")


def build_and_save_faiss_index():
    all_articles = list(Article.objects.filter(processed_content__isnull=False))
    model = SentenceTransformer("paraphrase-MiniLM-L6-v2")
    article_contents = [article.processed_content for article in all_articles]

    embeddings = model.encode(article_contents, convert_to_numpy=True)

    faiss.normalize_L2(embeddings)

    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)

    faiss.write_index(index, FAISS_INDEX_PATH)
    with open(FAISS_ARTICLES_PATH, "wb") as f:
        pickle.dump(all_articles, f)
    np.save(FAISS_EMBEDDINGS_PATH, embeddings)

    return all_articles, index, embeddings


def load_faiss_index():
    if not os.path.exists(FAISS_INDEX_PATH):
        return build_and_save_faiss_index()

    index = faiss.read_index(FAISS_INDEX_PATH)
    with open(FAISS_ARTICLES_PATH, "rb") as f:
        all_articles = pickle.load(f)
    embeddings = np.load(FAISS_EMBEDDINGS_PATH)

    return all_articles, index, embeddings


def get_faiss_recommendations(user_id, n=10):
    read_activities = UserActivity.objects.filter(
        user_id=user_id, activity_type="read"
    ).select_related("article")
    if not read_activities:
        return Article.objects.order_by("-publication_date")[:n]

    read_articles = [
        activity.article
        for activity in read_activities
        if activity.article.processed_content
    ]
    if not read_articles:
        return Article.objects.order_by("-publication_date")[:n]

    all_articles, index, embeddings = load_faiss_index()

    model = SentenceTransformer("paraphrase-MiniLM-L6-v2")
    read_contents = [article.processed_content for article in read_articles]
    read_embeddings = model.encode(read_contents, convert_to_numpy=True)

    user_profile = np.mean(read_embeddings, axis=0)

    user_profile = user_profile / np.linalg.norm(user_profile)

    user_profile = np.array([user_profile]).astype("float32")
    scores, indices = index.search(user_profile, n + len(read_articles))

    read_article_ids = {article.id for article in read_articles}
    recommended_articles = []
    for idx in indices[0]:
        if idx < len(all_articles) and all_articles[idx].id not in read_article_ids:
            recommended_articles.append(all_articles[idx])
            if len(recommended_articles) >= n:
                break

    return recommended_articles

def hybrid_recommendations(user_id):
    tfidf_rec = get_content_based_recommendations(user_id, n=5)
    sbert_rec = get_sentence_bert_recommendations(user_id, n=5)
    faiss_rec = get_faiss_recommendations(user_id, n=5)
    seen = set()
    return [
        r for r in (tfidf_rec + sbert_rec + faiss_rec)
        if not (r.id in seen or seen.add(r.id))
    ]
