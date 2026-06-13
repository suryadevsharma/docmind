import os

import chromadb
from chromadb.errors import NotFoundError
from chromadb import EmbeddingFunction
from dotenv import load_dotenv

load_dotenv()

class NoneEmbeddingFunction(EmbeddingFunction):
    def __init__(self):
        pass

    def name(self) -> str:
        return "none"

    def __call__(self, input):
        return []

CHROMA_DIR = os.getenv("CHROMA_DIR", "./chroma_db")
_client = chromadb.PersistentClient(path=CHROMA_DIR)


def create_collection(collection_id: str):
    return _client.get_or_create_collection(
        name=collection_id,
        embedding_function=NoneEmbeddingFunction()
    )


def add_chunks(collection_id: str, chunks: list[str], embeddings: list[list[float]], chunk_ids: list[str], metadatas: list[dict] = None) -> None:
    collection = create_collection(collection_id)
    collection.add(ids=chunk_ids, documents=chunks, embeddings=embeddings, metadatas=metadatas)


def query_similar(collection_id: str, query_embedding: list[float], n_results: int = 5) -> list[dict]:
    collection = _client.get_collection(
        name=collection_id,
        embedding_function=NoneEmbeddingFunction()
    )
    result = collection.query(query_embeddings=[query_embedding], n_results=n_results)
    docs = result.get("documents", [[]])
    metadatas = result.get("metadatas", [[]])
    
    output = []
    if docs and metadatas:
        for doc, meta in zip(docs[0], metadatas[0]):
            output.append({
                "text": doc,
                "metadata": meta or {}
            })
    return output



def delete_collection(collection_id: str) -> None:
    try:
        _client.delete_collection(name=collection_id)
    except NotFoundError:
        return
