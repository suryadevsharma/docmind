import os

from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
genai.configure(api_key=_api_key)

SYSTEM_PROMPT = (
    "You are a helpful document assistant. Answer questions only based on the provided "
    "document context. If the answer is not in the context, say "
    "'I could not find this information in the document.' Be concise and accurate."
)

_PREFERRED_MODELS = [
    "gemini-1.5-flash-latest",
    "gemini-1.5-flash",
    "gemini-1.5-pro-latest",
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash",
]


def _resolve_model_name() -> str:
    try:
        models = list(genai.list_models())
        available = {
            m.name.replace("models/", ""): set(m.supported_generation_methods or [])
            for m in models
        }

        for name in _PREFERRED_MODELS:
            methods = available.get(name, set())
            if "generateContent" in methods:
                return name

        # Fallback: first model that supports generateContent
        for name, methods in available.items():
            if "generateContent" in methods:
                return name
    except Exception:
        # If listing fails, we still try a common default.
        pass
    return "gemini-1.5-flash"


_model = genai.GenerativeModel(_resolve_model_name())


def _extractive_fallback(context_chunks: list[str]) -> str:
    if not context_chunks:
        return "I could not find this information in the document."
    snippet = context_chunks[0][:500].strip()
    return (
        "I am temporarily unable to use the Gemini API quota. "
        "Based on the top retrieved document section:\n\n"
        f"{snippet}"
    )


def generate_answer(question: str, context_chunks: list[str], chat_history: list[dict]) -> str:
    context = "\n\n---\n\n".join(context_chunks) if context_chunks else "No context found."
    history_text = "\n".join([f"{m['role']}: {m['content']}" for m in chat_history[-6:]])
    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Document Context:\n{context}\n\n"
        f"Recent Chat History:\n{history_text}\n\n"
        f"Question:\n{question}\n\n"
        "Answer:"
    )
    try:
        response = _model.generate_content(prompt)
        return (response.text or "").strip()
    except Exception as exc:
        msg = str(exc).lower()
        if "quota" in msg or "429" in msg or "rate limit" in msg:
            return _extractive_fallback(context_chunks)
        raise
