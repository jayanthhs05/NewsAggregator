import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors
from ..models import Article, EventCluster

def auto_tune_eps(X, n_neighbors=2):
    neighbors = NearestNeighbors(n_neighbors=n_neighbors)
    neighbors.fit(X)
    distances, _ = neighbors.kneighbors(X)
    distances = np.sort(distances[:, n_neighbors-1])
    deltas = np.diff(distances)
    return distances[np.argmax(deltas)]

def cluster_recent_articles(days=7):
    recent_articles = Article.objects.filter(processed_content__isnull=False)
    if recent_articles.count() < 5: 
        return
    article_ids = [article.id for article in recent_articles]
    contents = [article.processed_content for article in recent_articles]
    vectorizer = TfidfVectorizer(stop_words='english', max_features=5000)
    tfidf_matrix = vectorizer.fit_transform(contents)
    eps = auto_tune_eps(tfidf_matrix.toarray())
    dbscan = DBSCAN(eps=eps, min_samples=2, metric='cosine')
    labels = dbscan.fit_predict(tfidf_matrix)
    for cluster_id in set(labels):
        if cluster_id == -1: 
            continue
        cluster_article_indices = np.where(labels == cluster_id)[0]
        cluster_article_ids = [article_ids[idx] for idx in cluster_article_indices]
        cluster_texts = [contents[idx] for idx in cluster_article_indices]
        cluster_tfidf = vectorizer.transform(cluster_texts)
        feature_names = vectorizer.get_feature_names_out()
        cluster_vec = cluster_tfidf.mean(axis=0).A1
        top_terms = [feature_names[idx] for idx in cluster_vec.argsort()[-5:][::-1]]
        event_cluster, _ = EventCluster.objects.get_or_create(name=" ".join(top_terms))
        event_cluster.articles.add(*cluster_article_ids)
