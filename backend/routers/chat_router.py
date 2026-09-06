import json
import logging
import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import ChatSession, Document, Message, User
from schemas import ChatMessageCreate, ChatSessionCreate, ChatSessionOut, MessageOut
from services.embedding_service import embed_texts
from services.intent_service import get_chitchat_response
from services.llm_service import GeminiRateLimitError, generate_answer, generate_answer_stream
from services.metrics import metrics
from services.vector_service import DocumentUnavailableError, query_similar

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])

# --- Rate limiting (preserved from original) ---
_rate_limiter = defaultdict(deque)
MAX_PER_MINUTE = 20
WINDOW_SECONDS = 60

# --- In-flight generation lock: prevents duplicate concurrent requests per session ---
_active_generating_sessions: set = set()


def resp(success: bool, data, message: str):
    return {"success": success, "data": data, "message": message}


def enforce_rate_limit(user_id: int):
    now = time.time()
    q = _rate_limiter[user_id]
    while q and now - q[0] > WINDOW_SECONDS:
        q.popleft()
    if len(q) >= MAX_PER_MINUTE:
        metrics.inc_429_response("local_rate_limit")
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

    doc = session.document
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Prevent concurrent generation on same session
    if session.id in _active_generating_sessions:
        raise HTTPException(
            status_code=409,
            detail="A response is already being generated for this chat session. Please wait.",
        )

    _active_generating_sessions.add(session.id)
    t_total = time.time()

    try:
        history_rows = (
            db.query(Message)
            .filter(Message.session_id == payload.session_id)
            .order_by(Message.created_at.desc())
            .limit(6)
            .all()
        )
        history_rows.reverse()
        history = [{"role": h.role, "content": h.content} for h in history_rows]

        chitchat = get_chitchat_response(question)
        if chitchat:
            logger.info(f"[CHAT] session_id={session.id} intent=chitchat")
            answer = chitchat
            chunks = []
            embed_ms = 0
            retrieval_ms = 0
            generation_ms = 0
        else:
            # Step 1: Embed the query (single embedding call)
            t0 = time.time()
            question_vec = embed_texts([question], task_type="RETRIEVAL_QUERY")[0]
            embed_ms = (time.time() - t0) * 1000

            # Step 2: Retrieve similar chunks from ChromaDB
            t0 = time.time()
            chunks = query_similar(doc.chroma_collection_id, question_vec, n_results=5, doc=doc)
            retrieval_ms = (time.time() - t0) * 1000

            # Step 3: Generate answer (single LLM call)
            t0 = time.time()
            answer = generate_answer(question, chunks, history)
            generation_ms = (time.time() - t0) * 1000

    except DocumentUnavailableError as unavail_err:
        logger.warning(f"Document unavailable for doc {doc.id}: {unavail_err}")
        return resp(
            True,
            {
                "answer": "The uploaded document file is no longer available on the server (it may have been cleared during a server restart). Please upload the document again to continue chatting.",
                "sources": [],
            },
            "Document unavailable",
        )
    except GeminiRateLimitError as rate_err:
        logger.warning(f"[CHAT] Gemini rate limit for user {current_user.id}: {rate_err}")
        return resp(
            True,
            {
                "answer": str(rate_err),
                "sources": [],
            },
            "Rate limited",
        )
    except Exception as exc:
        logger.error(f"Error generating answer in send_message: {exc}", exc_info=True)
        raise HTTPException(
            status_code=502,
            detail="Failed to generate response from AI provider. Please try again shortly.",
        ) from exc
    finally:
        _active_generating_sessions.discard(session.id)

    sources = []
    for c in chunks:
        sources.append({
            "text": c["text"][:240] + ("..." if len(c["text"]) > 240 else ""),
            "page": c["metadata"].get("page", 1),
            "source": c["metadata"].get("source", "Unknown")
        })

    # Step 4: Save to database (single write)
    t0 = time.time()
    try:
        user_msg = Message(session_id=session.id, role="user", content=question)
        ai_msg = Message(session_id=session.id, role="assistant", content=answer, sources=json.dumps(sources))
        db.add(user_msg)
        db.add(ai_msg)
        db.commit()
    except Exception as db_exc:
        logger.error(f"Database error saving message in send_message: {db_exc}", exc_info=True)
        db.rollback()
        raise
    db_ms = (time.time() - t0) * 1000

    total_ms = (time.time() - t_total) * 1000
    logger.info(
        f"[CHAT] session_id={session.id} user_id={current_user.id} "
        f"embedding={embed_ms:.0f}ms retrieval={retrieval_ms:.0f}ms "
        f"generation={generation_ms:.0f}ms db_save={db_ms:.0f}ms total={total_ms:.0f}ms"
    )

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


@router.post("/message/stream")
async def send_message_stream(
    request: Request,
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

    doc = session.document
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Prevent concurrent generation on same session
    if session.id in _active_generating_sessions:
        raise HTTPException(
            status_code=409,
            detail="A response is already being generated for this chat session. Please wait.",
        )

    # Lightweight local intent check BEFORE generating query embedding
    chitchat = get_chitchat_response(question)
    if chitchat:
        logger.info(f"[CHAT-STREAM] session_id={session.id} intent=chitchat")

        async def chitchat_stream_generator():
            _active_generating_sessions.add(session.id)
            t_total = time.time()
            try:
                yield f"data: {json.dumps({'type': 'sources', 'sources': []})}\n\n"

                words = chitchat.split(" ")
                for i, word in enumerate(words):
                    if await request.is_disconnected():
                        logger.info(f"[CHAT-STREAM] Client disconnected session_id={session.id}")
                        return
                    chunk = word + (" " if i < len(words) - 1 else "")
                    yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"

                t_db = time.time()
                try:
                    user_msg = Message(session_id=session.id, role="user", content=question)
                    ai_msg = Message(session_id=session.id, role="assistant", content=chitchat, sources=json.dumps([]))
                    db.add(user_msg)
                    db.add(ai_msg)
                    db.commit()
                except Exception as db_exc:
                    logger.error(f"Database error saving streaming chitchat: {db_exc}", exc_info=True)
                    db.rollback()
                db_ms = (time.time() - t_db) * 1000

                total_ms = (time.time() - t_total) * 1000
                logger.info(
                    f"[CHAT-STREAM] session_id={session.id} user_id={current_user.id} "
                    f"intent=chitchat db_save={db_ms:.0f}ms total={total_ms:.0f}ms"
                )

                yield 'data: {"type": "done"}\n\n'
            finally:
                _active_generating_sessions.discard(session.id)

        return StreamingResponse(chitchat_stream_generator(), media_type="text/event-stream")

    # Pre-generation steps: embed query + retrieve chunks (before entering SSE generator)
    try:
        t_embed = time.time()
        question_vec = embed_texts([question], task_type="RETRIEVAL_QUERY")[0]
        embed_ms = (time.time() - t_embed) * 1000

        t_retrieval = time.time()
        chunks = query_similar(doc.chroma_collection_id, question_vec, n_results=5, doc=doc)
        retrieval_ms = (time.time() - t_retrieval) * 1000
    except DocumentUnavailableError as unavail_err:
        logger.warning(f"Document unavailable for doc {doc.id}: {unavail_err}")
        async def unavailable_stream_generator():
            yield f"data: {json.dumps({'type': 'sources', 'sources': []})}\n\n"
            msg = "The uploaded document file is no longer available on the server (it may have been cleared during a server restart). Please upload the document again to continue chatting."
            yield f"data: {json.dumps({'type': 'content', 'content': msg})}\n\n"
            yield 'data: {"type": "done"}\n\n'
        return StreamingResponse(unavailable_stream_generator(), media_type="text/event-stream")
    except Exception as exc:
        logger.error(f"Failed to query document references for doc {doc.id}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=502,
            detail="Failed to query document references. Please try again shortly.",
        ) from exc

    sources = []
    for c in chunks:
        sources.append({
            "text": c["text"][:240] + ("..." if len(c["text"]) > 240 else ""),
            "page": c["metadata"].get("page", 1),
            "source": c["metadata"].get("source", "Unknown")
        })

    history_rows = (
        db.query(Message)
        .filter(Message.session_id == payload.session_id)
        .order_by(Message.created_at.desc())
        .limit(6)
        .all()
    )
    history_rows.reverse()
    history = [{"role": h.role, "content": h.content} for h in history_rows]

    async def event_generator():
        # Register active generation
        _active_generating_sessions.add(session.id)
        t_total = time.time()

        try:
            # Yield citations first
            yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"

            full_answer = ""
            generation_success = False
            t_gen = time.time()

            try:
                for chunk in generate_answer_stream(question, chunks, history):
                    # Check if client disconnected — stop generating
                    if await request.is_disconnected():
                        logger.info(f"[CHAT-STREAM] Client disconnected session_id={session.id}")
                        return

                    full_answer += chunk
                    yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"

                generation_success = True

            except GeminiRateLimitError as rate_err:
                logger.warning(f"[CHAT-STREAM] Gemini rate limit session_id={session.id}: {rate_err}")
                yield f"data: {json.dumps({'type': 'error', 'message': str(rate_err)})}\n\n"
                return
            except Exception as e:
                logger.error(f"[CHAT-STREAM] Gemini streaming error session_id={session.id}: {e}", exc_info=True)
                yield f"data: {json.dumps({'type': 'error', 'message': 'An error occurred during generation. Please try again.'})}\n\n"
                return

            gen_ms = (time.time() - t_gen) * 1000

            # Save to database only on successful generation
            if generation_success and full_answer.strip():
                t_db = time.time()
                try:
                    user_msg = Message(session_id=session.id, role="user", content=question)
                    ai_msg = Message(session_id=session.id, role="assistant", content=full_answer, sources=json.dumps(sources))
                    db.add(user_msg)
                    db.add(ai_msg)
                    db.commit()
                except Exception as db_exc:
                    logger.error(f"Database error saving streaming messages: {db_exc}", exc_info=True)
                    db.rollback()
                db_ms = (time.time() - t_db) * 1000
            else:
                db_ms = 0

            total_ms = (time.time() - t_total) * 1000
            logger.info(
                f"[CHAT-STREAM] session_id={session.id} user_id={current_user.id} "
                f"embedding={embed_ms:.0f}ms retrieval={retrieval_ms:.0f}ms "
                f"generation={gen_ms:.0f}ms db_save={db_ms:.0f}ms total={total_ms:.0f}ms"
            )

            yield 'data: {"type": "done"}\n\n'

        finally:
            _active_generating_sessions.discard(session.id)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.delete("/session/{session_id}")
async def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    db.delete(session)
    db.commit()
    return resp(True, None, "Session deleted successfully")
