import logging
import os
import time
from typing import List

from dotenv import load_dotenv
from google import genai

from services.metrics import metrics

load_dotenv()

logger = logging.getLogger(__name__)

_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
_client = genai.Client(api_key=_api_key) if _api_key else None

EMBEDDING_MODEL = "gemini-embedding-001"


def embed_texts(texts: List[str], task_type: str = "RETRIEVAL_DOCUMENT") -> List[List[float]]:
    """Generate embeddings for a list of texts using Gemini Embedding API.

    Args:
        texts: List of text strings to embed.
        task_type: One of RETRIEVAL_DOCUMENT, RETRIEVAL_QUERY, etc.

    Returns:
        List of embedding vectors (each a list of floats).
    """
    if not texts:
        return []

    if not _client:
        logger.error("Gemini API key not configured for embeddings")
        return [[0.0] * 3072 for _ in texts]

    all_embeddings: List[List[float]] = []
    batch_size = 50

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        t0 = time.time()
        try:
            metrics.inc_embedding_call()
            response = _client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=batch,
                config={"task_type": task_type},
            )
            elapsed_ms = (time.time() - t0) * 1000

            if response.embeddings:
                for emb in response.embeddings:
                    all_embeddings.append(emb.values)
                logger.info(
                    f"[EMBED] batch={i}-{i+len(batch)} count={len(batch)} "
                    f"model={EMBEDDING_MODEL} duration={elapsed_ms:.0f}ms"
                )
            else:
                logger.warning(
                    f"[EMBED] Empty response for batch {i}-{i+len(batch)}, "
                    f"using zero vectors"
                )
                all_embeddings.extend([[0.0] * 3072 for _ in batch])

        except Exception as exc:
            elapsed_ms = (time.time() - t0) * 1000
            msg = str(exc).lower()
            if any(k in msg for k in ["429", "quota", "resourceexhausted", "rate limit", "rate_limit"]):
                metrics.inc_429_response("embedding")
            logger.error(
                f"[EMBED] ERROR batch={i}-{i+len(batch)} "
                f"duration={elapsed_ms:.0f}ms error={exc.__class__.__name__}: {exc}",
                exc_info=True,
            )
            all_embeddings.extend([[0.0] * 3072 for _ in batch])

    return all_embeddings
