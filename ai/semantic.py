from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# Load model once
model = SentenceTransformer("all-MiniLM-L6-v2")

def find_best_match(query, keys):
    """
    Returns the key from `keys` that best matches `query` semantically.
    """
    if not keys:
        return None

    key_list = list(keys)

    query_vector = model.encode([query])
    key_vectors = model.encode(key_list)

    scores = cosine_similarity(query_vector, key_vectors)

    best_index = scores.argmax()

    return key_list[best_index]