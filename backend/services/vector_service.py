import logging
import os
from typing import Any, Dict, List, Optional

import chromadb
from chromadb import EmbeddingFunction
from chromadb.errors import NotFoundError
from dotenv import load_dotenv

from services.embedding_service import embed_texts
from services.parser_service import parse_docx, parse_pdf

load_dotenv()

logger = logging.getLogger(__name__)


class DocumentUnavailableError(Exception):
    """Raised when Chroma collection is missing and the original document file cannot be found for re-indexing."""
    pass


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
        embedding_function=NoneEmbeddingFunction(),
    )


def add_chunks(
    collection_id: str,
    chunks: list[str],
    embeddings: list[list[float]],
    chunk_ids: list[str],
    metadatas: list[dict] = None,
) -> None:
    collection = create_collection(collection_id)
    collection.upsert(ids=chunk_ids, documents=chunks, embeddings=embeddings, metadatas=metadatas)


def reindex_document_file(
    collection_id: str,
    filepath: str,
    file_type: str,
    original_name: str,
    doc_id: Any = None,
) -> Any:
    """Re-extracts a document, regenerates embeddings, upserts into Chroma, and returns the collection."""
    logger.info(f"Re-indexing document from '{filepath}' into collection '{collection_id}'...")
    chunks = parse_pdf(filepath) if file_type == "pdf" else parse_docx(filepath)
    if not chunks:
        logger.warning(f"No readable text found when re-indexing '{filepath}'.")
        return create_collection(collection_id)

    raw_texts = [c["text"] for c in chunks]
    metadatas = [{"page": c["page"], "source": original_name or "Unknown"} for c in chunks]
    embeddings = embed_texts(raw_texts, task_type="retrieval_document")
    chunk_ids = [f"chunk_{doc_id or collection_id}_{i}" for i in range(len(chunks))]

    collection = create_collection(collection_id)
    collection.upsert(ids=chunk_ids, documents=raw_texts, embeddings=embeddings, metadatas=metadatas)
    logger.info(f"Successfully re-indexed {len(chunks)} chunks into collection '{collection_id}'.")
    return collection


def query_similar(
    collection_id: str,
    query_embedding: list[float],
    n_results: int = 5,
    doc: Optional[Any] = None,
    filepath: Optional[str] = None,
    file_type: Optional[str] = None,
    original_name: Optional[str] = None,
    doc_id: Optional[Any] = None,
) -> list[dict]:
    # Resolve document metadata if a doc object was passed
    if doc is not None:
        upload_dir = os.getenv("UPLOAD_DIR", "./uploads")
        doc_filename = getattr(doc, "filename", None)
        if doc_filename and not filepath:
            filepath = os.path.join(upload_dir, doc_filename)
        file_type = file_type or getattr(doc, "file_type", None)
        original_name = original_name or getattr(doc, "original_name", "document")
        doc_id = doc_id or getattr(doc, "id", None)

    collection = None
    needs_recovery = False

    try:
        collection = _client.get_collection(
            name=collection_id,
            embedding_function=NoneEmbeddingFunction(),
        )
        # If collection exists but is completely empty, it may need recovery if file is available
        if collection.count() == 0 and filepath and os.path.exists(filepath):
            logger.info(f"Collection '{collection_id}' is empty. Triggering re-index from file.")
            needs_recovery = True
    except (NotFoundError, ValueError) as not_found_exc:
        logger.warning(
            f"Chroma collection '{collection_id}' does not exist: {not_found_exc}. Checking for document recovery...",
            exc_info=True,
        )
        needs_recovery = True
    except Exception as exc:
        logger.error(f"Unexpected error getting Chroma collection '{collection_id}': {exc}", exc_info=True)
        needs_recovery = True

    # Robust recovery logic
    if needs_recovery:
        if filepath and os.path.exists(filepath):
            try:
                collection = reindex_document_file(
                    collection_id=collection_id,
                    filepath=filepath,
                    file_type=file_type or "pdf",
                    original_name=original_name or "document",
                    doc_id=doc_id,
                )
            except Exception as reindex_exc:
                logger.error(
                    f"Failed during auto-reindexing for collection '{collection_id}': {reindex_exc}",
                    exc_info=True,
                )
                raise DocumentUnavailableError(
                    f"Document '{original_name or 'file'}' could not be recovered. Please upload it again."
                ) from reindex_exc
        else:
            logger.warning(
                f"Chroma collection '{collection_id}' missing and document file '{filepath}' is unavailable on disk."
            )
            raise DocumentUnavailableError(
                f"Document '{original_name or 'file'}' is no longer available on the server. Please upload it again."
            )

    try:
        result = collection.query(query_embeddings=[query_embedding], n_results=n_results)
        docs = result.get("documents", [[]])
        metadatas = result.get("metadatas", [[]])

        output = []
        if docs and metadatas:
            for doc_text, meta in zip(docs[0], metadatas[0]):
                output.append({
                    "text": doc_text,
                    "metadata": meta or {},
                })
        return output
    except Exception as q_exc:
        logger.error(f"Error performing vector similarity search in '{collection_id}': {q_exc}", exc_info=True)
        raise


def delete_collection(collection_id: str) -> None:
    try:
        _client.delete_collection(name=collection_id)
    except (NotFoundError, ValueError):
        return
    except Exception as exc:
        logger.error(f"Error deleting collection '{collection_id}': {exc}", exc_info=True)
