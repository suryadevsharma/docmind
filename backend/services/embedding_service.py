import logging
import os
from typing import List

from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

logger = logging.getLogger(__name__)

_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
if _api_key:
    genai.configure(api_key=_api_key)


def _ensure_api_key():
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
    if key:
        genai.configure(api_key=key)
    return key


def embed_texts(texts: List[str], task_type: str = "retrieval_document") -> List[List[float]]:
    if not texts:
        return []

    _ensure_api_key()
    all_embeddings: List[List[float]] = []
    batch_size = 50

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        try:
            response = genai.embed_content(
                model="models/gemini-embedding-001",
                content=batch,
                task_type=task_type,
            )
            emb = response.get("embedding", [])
            # Handle potential 1D list for single-element batch
            if emb and isinstance(emb[0], (int, float)):
                all_embeddings.append(emb)
            elif emb and isinstance(emb[0], list):
                all_embeddings.extend(emb)
            else:
                logger.warning(f"Unexpected embedding response format for batch {i}: {type(emb)}")
                all_embeddings.extend([[0.0] * 3072 for _ in batch])
        except Exception as exc:
            logger.error(
                f"Gemini embedding API error on batch range [{i}:{i+len(batch)}]: {exc}",
                exc_info=True,
            )
            all_embeddings.extend([[0.0] * 3072 for _ in batch])

    return all_embeddings
