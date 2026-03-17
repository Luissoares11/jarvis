import numpy as np
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")


def cosine_similarity(a, b) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def build_topic_embeddings(memory: dict) -> dict:
    if not memory:
        return {}
    return {
        topic: model.encode(topic, convert_to_numpy=True)
        for topic in memory.keys()
    }


def build_value_embeddings(memory: dict) -> list[dict]:
    rows = []
    for topic, values in memory.items():
        for value in values:
            text = f"{topic} :: {value}"
            rows.append({
                "topic": topic,
                "value": value,
                "text": text,
                "embedding": model.encode(text, convert_to_numpy=True)
            })
    return rows


def find_best_topic(query: str, topic_embeddings: dict, threshold: float = 0.58):
    if not topic_embeddings:
        return None, 0.0

    query_vec = model.encode(query, convert_to_numpy=True)

    best_topic = None
    best_score = 0.0

    for topic, vec in topic_embeddings.items():
        score = cosine_similarity(query_vec, vec)
        if score > best_score:
            best_score = score
            best_topic = topic

    if best_score >= threshold:
        return best_topic, best_score

    return None, best_score


def find_best_value(query: str, value_embeddings: list[dict], threshold: float = 0.52):
    if not value_embeddings:
        return None, 0.0

    query_vec = model.encode(query, convert_to_numpy=True)

    best_row = None
    best_score = 0.0

    for row in value_embeddings:
        score = cosine_similarity(query_vec, row["embedding"])
        if score > best_score:
            best_score = score
            best_row = row

    if best_score >= threshold:
        return best_row, best_score

    return None, best_score