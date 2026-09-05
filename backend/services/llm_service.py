import logging
import os
import random
import time
from typing import List, Tuple

from dotenv import load_dotenv
from google import genai

load_dotenv()

logger = logging.getLogger(__name__)

_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
_client = genai.Client(api_key=_api_key) if _api_key else None

SYSTEM_PROMPT = (
    "You are a helpful document assistant. Answer questions only based on the provided "
    "document context. If the answer is not in the context, say "
    "'I could not find this information in the document.' Be concise and accurate."
)

PRIMARY_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Retry configuration — bounded and conservative
MAX_RETRIES = 1          # At most 1 retry for transient errors
INITIAL_BACKOFF = 1.0    # Base backoff in seconds
MAX_BACKOFF = 4.0        # Cap backoff


def _is_quota_error(exc: Exception) -> bool:
    """Detect HTTP 429 / ResourceExhausted / rate-limit errors."""
    msg = str(exc).lower()
    return any(k in msg for k in ["429", "quota", "resourceexhausted", "rate limit", "rate_limit", "resource_exhausted"])


def _is_transient_error(exc: Exception) -> bool:
    """Detect transient 500/503/timeout errors that may succeed on retry."""
    msg = str(exc).lower()
    return any(k in msg for k in ["500", "503", "internal", "service unavailable", "deadline exceeded", "timeout", "unavailable"])


def _extract_retry_delay(exc: Exception) -> float | None:
    """Attempt to extract Google's recommended retry delay from error metadata."""
    try:
        # google.genai errors may carry retry_delay in their details
        if hasattr(exc, "details") and exc.details:
            for detail in exc.details:
                if hasattr(detail, "retry_delay"):
                    rd = detail.retry_delay
                    if hasattr(rd, "total_seconds"):
                        return rd.total_seconds()
                    return float(rd)
        # Check string representation as fallback
        msg = str(exc)
        if "retry_delay" in msg:
            # Very basic extraction — not critical if it fails
            import re
            match = re.search(r"retry_delay.*?(\d+\.?\d*)\s*s", msg)
            if match:
                return float(match.group(1))
    except Exception:
        pass
    return None


def _backoff_with_jitter(attempt: int) -> float:
    """Calculate exponential backoff with jitter."""
    base = min(INITIAL_BACKOFF * (2 ** attempt), MAX_BACKOFF)
    return base * (0.5 + random.random() * 0.5)  # jitter between 50%-100% of base


def _build_prompt(question: str, context_chunks: List[dict], chat_history: List[dict]) -> Tuple[str, List[str]]:
    """Build the LLM prompt from question, context chunks, and chat history.

    Returns:
        Tuple of (prompt_string, list_of_unique_chunk_texts).
    """
    # Deduplicate chunks while preserving order
    seen = set()
    unique_texts = []
    for c in (context_chunks or []):
        t = c.get("text", "").strip() if isinstance(c, dict) else str(c).strip()
        if t and t not in seen:
            seen.add(t)
            unique_texts.append(t)

    context = "\n\n---\n\n".join(unique_texts) if unique_texts else "No context found."
    history_text = "\n".join([f"{m['role']}: {m['content']}" for m in (chat_history or [])[-6:]])
    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Document Context:\n{context}\n\n"
        f"Recent Chat History:\n{history_text}\n\n"
        f"Question:\n{question}\n\n"
        "Answer:"
    )
    return prompt, unique_texts


def _extractive_fallback(context_chunks: List[str]) -> str:
    """Return a best-effort extractive answer when Gemini is unavailable."""
    if not context_chunks:
        return "I could not find this information in the document."
    snippet = context_chunks[0][:500].strip()
    return (
        "I am temporarily unable to use the Gemini API quota. "
        "Based on the top retrieved document section:\n\n"
        f"{snippet}"
    )


class GeminiRateLimitError(Exception):
    """Raised when Gemini quota is exhausted and the request should not be retried."""
    pass


def generate_answer(question: str, context_chunks: List[dict], chat_history: List[dict]) -> str:
    """Generate a non-streaming answer using the primary Gemini model.

    Raises GeminiRateLimitError if quota is exhausted.
    """
    if not _client:
        logger.error("Gemini API key not configured")
        return _extractive_fallback([])

    prompt, raw_texts = _build_prompt(question, context_chunks, chat_history)
    last_exc = None

    for attempt in range(MAX_RETRIES + 1):
        t0 = time.time()
        try:
            response = _client.models.generate_content(
                model=PRIMARY_MODEL,
                contents=prompt,
            )
            elapsed_ms = (time.time() - t0) * 1000
            ans = (response.text or "").strip()

            logger.info(
                f"[LLM] model={PRIMARY_MODEL} attempt={attempt} "
                f"duration={elapsed_ms:.0f}ms success=true"
            )

            if ans:
                return ans

            # Empty response — don't retry, just use extractive fallback
            logger.warning(f"[LLM] Empty response from {PRIMARY_MODEL}")
            return _extractive_fallback(raw_texts)

        except Exception as exc:
            elapsed_ms = (time.time() - t0) * 1000
            last_exc = exc

            if _is_quota_error(exc):
                retry_delay = _extract_retry_delay(exc)
                logger.warning(
                    f"[LLM] 429 quota hit model={PRIMARY_MODEL} attempt={attempt} "
                    f"duration={elapsed_ms:.0f}ms retry_delay={retry_delay}"
                )

                # If retry delay is short and we haven't retried yet, wait and retry once
                if attempt < MAX_RETRIES and retry_delay and retry_delay <= 5.0:
                    jittered = retry_delay + random.random() * 0.5
                    logger.info(f"[LLM] Waiting {jittered:.1f}s before retry (Google retry_delay={retry_delay}s)")
                    time.sleep(jittered)
                    continue

                # Quota exhausted — fail fast, do NOT cascade to other models
                raise GeminiRateLimitError(
                    "Gemini is temporarily rate-limited. Please try again in a moment."
                ) from exc

            if _is_transient_error(exc) and attempt < MAX_RETRIES:
                delay = _backoff_with_jitter(attempt)
                logger.warning(
                    f"[LLM] Transient error model={PRIMARY_MODEL} attempt={attempt} "
                    f"duration={elapsed_ms:.0f}ms error={exc.__class__.__name__} "
                    f"retrying in {delay:.1f}s"
                )
                time.sleep(delay)
                continue

            # Non-retryable error
            logger.error(
                f"[LLM] ERROR model={PRIMARY_MODEL} attempt={attempt} "
                f"duration={elapsed_ms:.0f}ms error={exc.__class__.__name__}: {exc}",
                exc_info=True,
            )
            break

    logger.error(f"[LLM] All retries exhausted: {last_exc}", exc_info=True)
    return _extractive_fallback(raw_texts)


def generate_answer_stream(question: str, context_chunks: List[dict], chat_history: List[dict]):
    """Generate a streaming answer using the primary Gemini model.

    Yields text chunks as they arrive from the model.
    Raises GeminiRateLimitError if quota is exhausted before any tokens are yielded.
    """
    if not _client:
        logger.error("Gemini API key not configured")
        yield _extractive_fallback([])
        return

    prompt, raw_texts = _build_prompt(question, context_chunks, chat_history)
    last_exc = None

    for attempt in range(MAX_RETRIES + 1):
        t0 = time.time()
        yielded_any = False
        try:
            response = _client.models.generate_content_stream(
                model=PRIMARY_MODEL,
                contents=prompt,
            )
            ttft_logged = False
            for chunk in response:
                text = ""
                try:
                    text = chunk.text
                except Exception:
                    # Fallback extraction from candidates
                    if hasattr(chunk, "candidates") and chunk.candidates:
                        c = chunk.candidates[0]
                        if hasattr(c, "content") and hasattr(c.content, "parts"):
                            text = "".join(
                                getattr(p, "text", "") for p in c.content.parts if hasattr(p, "text")
                            )
                if text:
                    if not ttft_logged:
                        ttft_ms = (time.time() - t0) * 1000
                        logger.info(f"[LLM-STREAM] model={PRIMARY_MODEL} ttft={ttft_ms:.0f}ms")
                        ttft_logged = True
                    yielded_any = True
                    yield text

            if yielded_any:
                total_ms = (time.time() - t0) * 1000
                logger.info(
                    f"[LLM-STREAM] model={PRIMARY_MODEL} attempt={attempt} "
                    f"duration={total_ms:.0f}ms success=true"
                )
                return

            # Stream completed but yielded nothing — use extractive fallback
            logger.warning(f"[LLM-STREAM] Empty stream from {PRIMARY_MODEL}")
            yield _extractive_fallback(raw_texts)
            return

        except Exception as exc:
            elapsed_ms = (time.time() - t0) * 1000
            last_exc = exc

            # If we already yielded partial content, don't retry — just stop
            if yielded_any:
                logger.error(
                    f"[LLM-STREAM] Interrupted after partial output model={PRIMARY_MODEL} "
                    f"duration={elapsed_ms:.0f}ms error={exc.__class__.__name__}: {exc}",
                    exc_info=True,
                )
                return

            if _is_quota_error(exc):
                retry_delay = _extract_retry_delay(exc)
                logger.warning(
                    f"[LLM-STREAM] 429 quota hit model={PRIMARY_MODEL} attempt={attempt} "
                    f"duration={elapsed_ms:.0f}ms retry_delay={retry_delay}"
                )

                if attempt < MAX_RETRIES and retry_delay and retry_delay <= 5.0:
                    jittered = retry_delay + random.random() * 0.5
                    logger.info(f"[LLM-STREAM] Waiting {jittered:.1f}s before retry")
                    time.sleep(jittered)
                    continue

                raise GeminiRateLimitError(
                    "Gemini is temporarily rate-limited. Please try again in a moment."
                ) from exc

            if _is_transient_error(exc) and attempt < MAX_RETRIES:
                delay = _backoff_with_jitter(attempt)
                logger.warning(
                    f"[LLM-STREAM] Transient error model={PRIMARY_MODEL} attempt={attempt} "
                    f"duration={elapsed_ms:.0f}ms retrying in {delay:.1f}s"
                )
                time.sleep(delay)
                continue

            logger.error(
                f"[LLM-STREAM] ERROR model={PRIMARY_MODEL} attempt={attempt} "
                f"duration={elapsed_ms:.0f}ms error={exc.__class__.__name__}: {exc}",
                exc_info=True,
            )
            break

    logger.error(f"[LLM-STREAM] All retries exhausted: {last_exc}", exc_info=True)
    fallback_text = _extractive_fallback(raw_texts)
    for word in fallback_text.split(" "):
        yield word + " "
