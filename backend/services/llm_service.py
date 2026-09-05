import logging
import os
import time
from typing import Dict, List, Tuple

from dotenv import load_dotenv
import google.generativeai as genai
try:
    from google.api_core import exceptions
except Exception:
    exceptions = None

load_dotenv()

logger = logging.getLogger(__name__)

_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
if _api_key:
    genai.configure(api_key=_api_key)

SYSTEM_PROMPT = (
    "You are a helpful document assistant. Answer questions only based on the provided "
    "document context. If the answer is not in the context, say "
    "'I could not find this information in the document.' Be concise and accurate."
)

PRIMARY_MODEL = "gemini-2.5-flash"
FALLBACK_MODELS = ["gemini-flash-latest"]
MAX_500_RETRIES = 2
INITIAL_BACKOFF = 0.3

_cached_models: Dict[str, genai.GenerativeModel] = {}


def _get_model(model_name: str) -> genai.GenerativeModel:
    if model_name not in _cached_models:
        _cached_models[model_name] = genai.GenerativeModel(model_name)
    return _cached_models[model_name]


def _is_transient_error(exc: Exception) -> bool:
    if exceptions and isinstance(exc, (exceptions.InternalServerError, exceptions.ServiceUnavailable)):
        return True
    msg = str(exc).lower()
    return any(k in msg for k in ["500", "503", "internal error", "service unavailable", "deadline exceeded", "timeout"])


def _is_quota_error(exc: Exception) -> bool:
    if exceptions and isinstance(exc, exceptions.ResourceExhausted):
        return True
    msg = str(exc).lower()
    return any(k in msg for k in ["429", "quota", "resourceexhausted", "rate limit"])


def _build_prompt(question: str, context_chunks: List[dict], chat_history: List[dict]) -> Tuple[str, List[str]]:
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
    if not context_chunks:
        return "I could not find this information in the document."
    snippet = context_chunks[0][:500].strip()
    return (
        "I am temporarily unable to use the Gemini API quota. "
        "Based on the top retrieved document section:\n\n"
        f"{snippet}"
    )


def generate_answer(question: str, context_chunks: List[dict], chat_history: List[dict]) -> str:
    prompt, raw_texts = _build_prompt(question, context_chunks, chat_history)
    candidate_models = [PRIMARY_MODEL] + [m for m in FALLBACK_MODELS if m != PRIMARY_MODEL]
    last_exc = None

    for model_name in candidate_models:
        model = _get_model(model_name)
        attempt = 0
        while attempt <= MAX_500_RETRIES:
            try:
                response = model.generate_content(prompt)
                ans = (response.text or "").strip()
                if ans:
                    return ans
                break
            except Exception as exc:
                last_exc = exc
                if _is_quota_error(exc):
                    logger.warning(f"Quota limit hit on model '{model_name}'. Trying next available model...")
                    break
                if _is_transient_error(exc) and attempt < MAX_500_RETRIES:
                    delay = INITIAL_BACKOFF * (2 ** attempt)
                    logger.warning(
                        f"Temporary error ({exc.__class__.__name__}) on '{model_name}', "
                        f"retrying {attempt+1}/{MAX_500_RETRIES} in {delay:.2f}s..."
                    )
                    time.sleep(delay)
                    attempt += 1
                    continue
                logger.error(f"Gemini API error on '{model_name}': {exc}", exc_info=True)
                break

    logger.error(f"All Gemini models exhausted in generate_answer: {last_exc}", exc_info=True)
    return _extractive_fallback(raw_texts)


def generate_answer_stream(question: str, context_chunks: List[dict], chat_history: List[dict]):
    prompt, raw_texts = _build_prompt(question, context_chunks, chat_history)
    candidate_models = [PRIMARY_MODEL] + [m for m in FALLBACK_MODELS if m != PRIMARY_MODEL]
    last_exc = None

    for model_name in candidate_models:
        model = _get_model(model_name)
        attempt = 0
        while attempt <= MAX_500_RETRIES:
            yielded_any = False
            try:
                response = model.generate_content(prompt, stream=True)
                for chunk in response:
                    text = ""
                    try:
                        text = chunk.text
                    except Exception:
                        if hasattr(chunk, "candidates") and chunk.candidates:
                            c = chunk.candidates[0]
                            if hasattr(c, "content") and hasattr(c.content, "parts"):
                                text = "".join(
                                    getattr(p, "text", "") for p in c.content.parts if hasattr(p, "text")
                                )
                    if text:
                        yielded_any = True
                        yield text

                if yielded_any:
                    return

                # If stream returned 0 chunks, attempt non-streaming fallback before giving up
                logger.warning(f"Stream yielded empty response on '{model_name}'. Trying non-streaming fallback...")
                non_stream_resp = model.generate_content(prompt)
                fallback_ans = (non_stream_resp.text or "").strip()
                if fallback_ans:
                    yield fallback_ans
                    return
                break
            except Exception as exc:
                last_exc = exc
                if yielded_any:
                    logger.error(f"Gemini stream interrupted after partial output on '{model_name}': {exc}", exc_info=True)
                    return

                if _is_quota_error(exc):
                    logger.warning(f"Quota limit hit on '{model_name}'. Trying next available model...")
                    break

                if _is_transient_error(exc) and attempt < MAX_500_RETRIES:
                    delay = INITIAL_BACKOFF * (2 ** attempt)
                    logger.warning(
                        f"Temporary error ({exc.__class__.__name__}) on '{model_name}', "
                        f"retrying {attempt+1}/{MAX_500_RETRIES} in {delay:.2f}s..."
                    )
                    time.sleep(delay)
                    attempt += 1
                    continue

                # Non-streaming fallback if streaming fails before any output
                try:
                    logger.info(f"Attempting non-streaming fallback for '{model_name}'...")
                    non_stream_resp = model.generate_content(prompt)
                    ans = (non_stream_resp.text or "").strip()
                    if ans:
                        yield ans
                        return
                except Exception as ns_exc:
                    logger.warning(f"Non-streaming fallback failed on '{model_name}': {ns_exc}")

                logger.error(f"Gemini streaming error on '{model_name}': {exc}", exc_info=True)
                break

    logger.error(f"All Gemini models exhausted on streaming: {last_exc}", exc_info=True)
    fallback_text = _extractive_fallback(raw_texts)
    for word in fallback_text.split(" "):
        yield word + " "
