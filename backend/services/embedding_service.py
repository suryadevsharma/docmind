import os
import google.generativeai as genai

_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
genai.configure(api_key=_api_key)


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    try:
        response = genai.embed_content(
            model="models/gemini-embedding-001",
            content=texts,
            task_type="retrieval_document",
        )
        return response.get("embedding", [])
    except Exception as exc:
        print(f"Gemini embedding API error: {exc}")
        return [[0.0] * 3072 for _ in texts]
