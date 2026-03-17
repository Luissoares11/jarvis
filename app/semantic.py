import numpy as np
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")


def build_embeddings(keys):
    if not keys:
        return {}
    return {key: model.encode(key, convert_to_numpy=True) for key in keys}


def find_best_match(query: str, embeddings: dict, threshold: float = 0.6):
    if not embeddings:
        return None

    query_vec = model.encode(query, convert_to_numpy=True)

    best_key = None
    best_score = 0.0

    for key, vec in embeddings.items():
        score = float(np.dot(query_vec, vec) / (np.linalg.norm(query_vec) * np.linalg.norm(vec)))
        if score > best_score:
            best_score = score
            best_key = key

    if best_score >= threshold:
        return best_key

    return None