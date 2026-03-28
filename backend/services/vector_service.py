import os

import chromadb
from chromadb.errors import NotFoundError
from dotenv import load_dotenv

load_dotenv()

CHROMA_DIR = os.getenv("CHROMA_DIR", "./chroma_db")
_client = chromadb.PersistentClient(path=CHROMA_DIR)


def create_collection(collection_id: str):
    return _client.get_or_create_collection(name=collection_id)


def add_chunks(collection_id: str, chunks: list[str], embeddings: list[list[float]], chunk_ids: list[str]) -> None:
    collection = create_collection(collection_id)
    collection.add(ids=chunk_ids, documents=chunks, embeddings=embeddings)


def query_similar(collection_id: str, query_embedding: list[float], n_results: int = 5) -> list[str]:
    collection = _client.get_collection(name=collection_id)
    result = collection.query(query_embeddings=[query_embedding], n_results=n_results)
    docs = result.get("documents", [[]])
    return docs[0] if docs else []


def delete_collection(collection_id: str) -> None:
    try:
        _client.delete_collection(name=collection_id)
    except NotFoundError:
        return
