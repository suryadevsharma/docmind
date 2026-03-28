import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import ChatSession, Document, Message, User
from schemas import ChatMessageCreate, ChatSessionCreate, ChatSessionOut, MessageOut
from services.embedding_service import embed_texts
from services.llm_service import generate_answer
from services.vector_service import query_similar

router = APIRouter(prefix="/api/chat", tags=["chat"])

_rate_limiter = defaultdict(deque)
MAX_PER_MINUTE = 20
WINDOW_SECONDS = 60


def resp(success: bool, data, message: str):
    return {"success": success, "data": data, "message": message}


def enforce_rate_limit(user_id: int):
    now = time.time()
    q = _rate_limiter[user_id]
    while q and now - q[0] > WINDOW_SECONDS:
        q.popleft()
    if len(q) >= MAX_PER_MINUTE:
        raise HTTPException(status_code=429, detail="Rate limit exceeded: max 20 messages per minute")
    q.append(now)


@router.post("/session")
async def create_session(
    payload: ChatSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = (
        db.query(Document)
        .filter(Document.id == payload.document_id, Document.user_id == current_user.id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    session = ChatSession(document_id=payload.document_id, user_id=current_user.id)
    db.add(session)
    db.commit()
    db.refresh(session)
    return resp(True, ChatSessionOut.model_validate(session).model_dump(), "Session created")


@router.post("/message")
async def send_message(
    payload: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    enforce_rate_limit(current_user.id)
    question = payload.message.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == payload.session_id, ChatSession.user_id == current_user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    doc = db.query(Document).filter(Document.id == session.document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    history_rows = (
        db.query(Message)
        .filter(Message.session_id == payload.session_id)
        .order_by(Message.created_at.asc())
        .all()
    )
    history = [{"role": h.role, "content": h.content} for h in history_rows]

    try:
        question_vec = embed_texts([question])[0]
        chunks = query_similar(doc.chroma_collection_id, question_vec, n_results=5)
        answer = generate_answer(question, chunks, history)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="Failed to generate response from AI provider. Please try again shortly.",
        ) from exc

    user_msg = Message(session_id=session.id, role="user", content=question)
    ai_msg = Message(session_id=session.id, role="assistant", content=answer)
    db.add(user_msg)
    db.add(ai_msg)
    db.commit()

    sources = [c[:240] + ("..." if len(c) > 240 else "") for c in chunks]
    return resp(True, {"answer": answer, "sources": sources}, "Message processed")


@router.get("/history/{session_id}")
async def get_history(session_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    session = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == current_user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = db.query(Message).filter(Message.session_id == session_id).order_by(Message.created_at.asc()).all()
    return resp(True, [MessageOut.model_validate(m).model_dump() for m in messages], "History fetched")


@router.get("/sessions/{document_id}")
async def get_sessions(document_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    doc = db.query(Document).filter(Document.id == document_id, Document.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.document_id == document_id, ChatSession.user_id == current_user.id)
        .order_by(ChatSession.created_at.desc())
        .all()
    )
    return resp(True, [ChatSessionOut.model_validate(s).model_dump() for s in sessions], "Sessions fetched")
