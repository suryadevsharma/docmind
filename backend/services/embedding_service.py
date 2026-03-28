from sentence_transformers import SentenceTransformer

_model = SentenceTransformer("all-MiniLM-L6-v2")


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    vectors = _model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
    return vectors.tolist()
