import os
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import Document, User
from schemas import DocumentOut
from services.embedding_service import embed_texts
from services.parser_service import detect_file_type, parse_docx, parse_pdf
from services.vector_service import add_chunks, create_collection, delete_collection

router = APIRouter(prefix="/api/documents", tags=["documents"])

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "10"))

os.makedirs(UPLOAD_DIR, exist_ok=True)


def resp(success: bool, data, message: str):
    return {"success": success, "data": data, "message": message}


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    file_bytes = await file.read()
    max_size = MAX_FILE_SIZE_MB * 1024 * 1024
    if len(file_bytes) > max_size:
        raise HTTPException(status_code=400, detail=f"File exceeds {MAX_FILE_SIZE_MB}MB limit")

    file_type = detect_file_type(file_bytes)
    if file_type not in {"pdf", "docx"}:
        raise HTTPException(status_code=400, detail="Only valid PDF or DOCX files are allowed")
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    lower_name = file.filename.lower()
    if file_type == "pdf" and not lower_name.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File extension does not match detected PDF content")
    if file_type == "docx" and not lower_name.endswith(".docx"):
        raise HTTPException(status_code=400, detail="File extension does not match detected DOCX content")

    ext = "pdf" if file_type == "pdf" else "docx"
    safe_name = f"{uuid4().hex}.{ext}"
    file_path = os.path.join(UPLOAD_DIR, safe_name)
    with open(file_path, "wb") as out:
        out.write(file_bytes)

    chunks = parse_pdf(file_path) if file_type == "pdf" else parse_docx(file_path)
    if not chunks:
        os.remove(file_path)
        raise HTTPException(status_code=400, detail="No readable text found in document")

    doc = Document(
        user_id=current_user.id,
        filename=safe_name,
        original_name=file.filename,
        file_type=file_type,
        chunk_count=len(chunks),
        chroma_collection_id=f"tmp_{uuid4().hex}",
    )

    collection_id = ""
    try:
        db.add(doc)
        db.commit()
        db.refresh(doc)

        collection_id = f"user_{current_user.id}_doc_{doc.id}"
        doc.chroma_collection_id = collection_id
        db.add(doc)
        db.commit()
        db.refresh(doc)

        embeddings = embed_texts(chunks)
        chunk_ids = [f"chunk_{doc.id}_{i}" for i in range(len(chunks))]
        create_collection(collection_id)
        add_chunks(collection_id, chunks, embeddings, chunk_ids)
    except SQLAlchemyError as exc:
        db.rollback()
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Database error during upload: {exc}") from exc
    except Exception as exc:
        db.rollback()
        if collection_id:
            delete_collection(collection_id)
        if doc.id:
            try:
                db.delete(doc)
                db.commit()
            except Exception:
                db.rollback()
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Failed to process document: {exc}") from exc

    return resp(True, DocumentOut.model_validate(doc).model_dump(), "Document uploaded successfully")


@router.get("/")
async def list_documents(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    docs = (
        db.query(Document)
        .filter(Document.user_id == current_user.id)
        .order_by(Document.created_at.desc())
        .all()
    )
    return resp(True, [DocumentOut.model_validate(d).model_dump() for d in docs], "Documents fetched")


@router.delete("/{document_id}")
async def delete_document(document_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    doc = db.query(Document).filter(Document.id == document_id, Document.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    delete_collection(doc.chroma_collection_id)
    path = os.path.join(UPLOAD_DIR, doc.filename)
    if os.path.exists(path):
        os.remove(path)

    db.delete(doc)
    db.commit()
    return resp(True, None, "Document deleted")
