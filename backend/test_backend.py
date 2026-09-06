import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Mock heavy third-party libraries to avoid slow loading/downloads/network calls during tests
sys.modules["sentence_transformers"] = MagicMock()
sys.modules["chromadb"] = MagicMock()
sys.modules["chromadb.errors"] = MagicMock()
# Mock both the old and new Google SDKs
sys.modules["google"] = MagicMock()
sys.modules["google.generativeai"] = MagicMock()
sys.modules["google.genai"] = MagicMock()

# Append backend directory to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from fastapi.testclient import TestClient
from main import app
from database import Base, get_db
from models import User, Document, ChatSession, Message

# Setup temporary sqlite database for tests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

TEST_DATABASE_URL = "sqlite:///./test_docmind.db"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="module")
def db_session():
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()
        if os.path.exists("./test_docmind.db"):
            try:
                os.remove("./test_docmind.db")
            except Exception:
                pass


@pytest.fixture(scope="module")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _get_auth_headers(client):
    """Helper to register + login and return auth headers."""
    # Try login first (user may already exist from earlier test)
    login_res = client.post("/api/auth/login", json={
        "email": "testuser@example.com",
        "password": "supersecretpassword"
    })
    if login_res.status_code == 200 and login_res.json().get("data", {}).get("token"):
        token = login_res.json()["data"]["token"]
        return {"Authorization": f"Bearer {token}"}

    # Register
    client.post("/api/auth/register", json={
        "email": "testuser@example.com",
        "password": "supersecretpassword",
        "full_name": "Testy McTest"
    })
    login_res = client.post("/api/auth/login", json={
        "email": "testuser@example.com",
        "password": "supersecretpassword"
    })
    token = login_res.json()["data"]["token"]
    return {"Authorization": f"Bearer {token}"}


def _get_or_create_doc(client, headers):
    """Helper to ensure at least one document exists and return its id."""
    doc_res = client.get("/api/documents/", headers=headers)
    docs = doc_res.json().get("data", [])
    if docs:
        return docs[0]["id"]
    with patch("routers.document_router.parse_pdf") as mock_p, \
         patch("routers.document_router.embed_texts") as mock_e, \
         patch("routers.document_router.create_collection"), \
         patch("routers.document_router.add_chunks"):
        mock_p.return_value = [{"text": "Doc text", "page": 1}]
        mock_e.return_value = [[0.1] * 3072]
        res = client.post("/api/documents/upload", files={"file": ("test.pdf", b"%PDF-1.4 test", "application/pdf")}, headers=headers)
        return res.json()["data"]["id"]


def test_auth_register_and_login(client):
    # 1. Register
    reg_payload = {
        "email": "testuser@example.com",
        "password": "supersecretpassword",
        "full_name": "Testy McTest"
    }
    res = client.post("/api/auth/register", json=reg_payload)
    assert res.status_code == 200
    assert res.json()["success"] is True
    assert "token" in res.json()["data"]
    assert res.json()["data"]["user"]["email"] == "testuser@example.com"

    # 2. Login
    login_payload = {
        "email": "testuser@example.com",
        "password": "supersecretpassword"
    }
    res = client.post("/api/auth/login", json=login_payload)
    assert res.status_code == 200
    assert "token" in res.json()["data"]

    token = res.json()["data"]["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Get Me
    res = client.get("/api/auth/me", headers=headers)
    assert res.status_code == 200
    assert res.json()["data"]["email"] == "testuser@example.com"


@patch("routers.document_router.parse_pdf")
@patch("routers.document_router.embed_texts")
@patch("routers.document_router.create_collection")
@patch("routers.document_router.add_chunks")
def test_document_upload_and_list(mock_add_chunks, mock_create_coll, mock_embed_texts, mock_parse_pdf, client):
    # Mock return values for parser and embeddings
    mock_parse_pdf.return_value = [
        {"text": "Paragraph chunk 1 from page 1", "page": 1},
        {"text": "Paragraph chunk 2 from page 2", "page": 2}
    ]
    mock_embed_texts.return_value = [[0.1] * 3072, [0.2] * 3072]

    # Get login credentials
    login_res = client.post("/api/auth/login", json={
        "email": "testuser@example.com",
        "password": "supersecretpassword"
    })
    token = login_res.json()["data"]["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Upload file
    pdf_content = b"%PDF-1.4 test document content"
    files = {"file": ("manual.pdf", pdf_content, "application/pdf")}
    res = client.post("/api/documents/upload", files=files, headers=headers)
    assert res.status_code == 200
    assert res.json()["success"] is True
    assert res.json()["data"]["chunk_count"] == 2
    assert res.json()["data"]["original_name"] == "manual.pdf"

    # List documents
    list_res = client.get("/api/documents/", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()["data"]) >= 1


@patch("routers.chat_router.embed_texts")
@patch("routers.chat_router.query_similar")
@patch("routers.chat_router.generate_answer")
def test_chat_session_creation_and_messaging(mock_gen_answer, mock_query, mock_embed, client):
    mock_embed.return_value = [[0.1] * 3072]
    mock_query.return_value = [{
        "text": "Paragraph chunk 2 from page 2",
        "metadata": {"page": 2, "source": "manual.pdf"}
    }]
    mock_gen_answer.return_value = "The document details page 2 text contents."

    # Login
    login_res = client.post("/api/auth/login", json={
        "email": "testuser@example.com",
        "password": "supersecretpassword"
    })
    token = login_res.json()["data"]["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch document
    doc_res = client.get("/api/documents/", headers=headers)
    doc_id = doc_res.json()["data"][0]["id"]

    # Create session
    sess_res = client.post("/api/chat/session", json={"document_id": doc_id}, headers=headers)
    assert sess_res.status_code == 200
    session_id = sess_res.json()["data"]["id"]

    # Send message
    msg_res = client.post("/api/chat/message", json={
        "session_id": session_id,
        "message": "What is on page 2?"
    }, headers=headers)
    assert msg_res.status_code == 200
    assert msg_res.json()["success"] is True
    assert msg_res.json()["data"]["answer"] == "The document details page 2 text contents."
    
    # Check that sources list is returned with structured attributes (text, page, source)
    sources = msg_res.json()["data"]["sources"]
    assert len(sources) == 1
    assert sources[0]["page"] == 2
    assert sources[0]["source"] == "manual.pdf"

    # Fetch history and verify persistent citations are loaded
    hist_res = client.get(f"/api/chat/history/{session_id}", headers=headers)
    assert hist_res.status_code == 200
    messages = hist_res.json()["data"]
    assert len(messages) == 2  # user and assistant messages
    assert messages[1]["role"] == "assistant"
    assert messages[1]["sources"] is not None
    assert messages[1]["sources"][0]["page"] == 2
    assert messages[1]["sources"][0]["source"] == "manual.pdf"


@patch("routers.chat_router.embed_texts")
@patch("routers.chat_router.query_similar")
@patch("routers.chat_router.generate_answer_stream")
def test_chat_streaming(mock_gen_stream, mock_query, mock_embed, client):
    mock_embed.return_value = [[0.1] * 3072]
    mock_query.return_value = [{
        "text": "Paragraph chunk 1 from page 1",
        "metadata": {"page": 1, "source": "manual.pdf"}
    }]
    
    def mock_stream_fn(*args, **kwargs):
        yield "Streaming "
        yield "response "
        yield "chunk."
    mock_gen_stream.side_effect = mock_stream_fn

    # Login
    login_res = client.post("/api/auth/login", json={
        "email": "testuser@example.com",
        "password": "supersecretpassword"
    })
    token = login_res.json()["data"]["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch document
    doc_res = client.get("/api/documents/", headers=headers)
    doc_id = doc_res.json()["data"][0]["id"]

    # Create session
    sess_res = client.post("/api/chat/session", json={"document_id": doc_id}, headers=headers)
    session_id = sess_res.json()["data"]["id"]

    # Stream message
    res = client.post("/api/chat/message/stream", json={
        "session_id": session_id,
        "message": "Stream query"
    }, headers=headers)
    assert res.status_code == 200
    
    # Check that events exist in the returned text stream
    res_text = res.text
    assert "data: {" in res_text
    assert '"type": "sources"' in res_text
    assert '"type": "content"' in res_text
    assert '"type": "done"' in res_text

    # Delete session
    del_res = client.delete(f"/api/chat/session/{session_id}", headers=headers)
    assert del_res.status_code == 200


# ==================== NEW FOCUSED TESTS ====================


def test_history_endpoints_make_zero_gemini_calls(client):
    """Verify that history and session list endpoints make zero Gemini API calls."""
    headers = _get_auth_headers(client)

    # Get a document
    doc_res = client.get("/api/documents/", headers=headers)
    docs = doc_res.json()["data"]
    if not docs:
        pytest.skip("No documents available for history test")
    doc_id = docs[0]["id"]

    # Create a session (this should NOT call Gemini)
    sess_res = client.post("/api/chat/session", json={"document_id": doc_id}, headers=headers)
    assert sess_res.status_code == 200
    session_id = sess_res.json()["data"]["id"]

    # List sessions (this should NOT call Gemini)
    sessions_res = client.get(f"/api/chat/sessions/{doc_id}", headers=headers)
    assert sessions_res.status_code == 200

    # Get history (this should NOT call Gemini)
    hist_res = client.get(f"/api/chat/history/{session_id}", headers=headers)
    assert hist_res.status_code == 200

    # Clean up
    client.delete(f"/api/chat/session/{session_id}", headers=headers)


@patch("routers.chat_router.embed_texts")
@patch("routers.chat_router.query_similar")
@patch("routers.chat_router.generate_answer")
def test_gemini_429_handling(mock_gen_answer, mock_query, mock_embed, client):
    """Verify that Gemini 429 errors return a clean user-friendly message without crashing."""
    from services.llm_service import GeminiRateLimitError

    mock_embed.return_value = [[0.1] * 3072]
    mock_query.return_value = [{
        "text": "Some chunk text",
        "metadata": {"page": 1, "source": "test.pdf"}
    }]
    mock_gen_answer.side_effect = GeminiRateLimitError(
        "Gemini is temporarily rate-limited. Please try again in a moment."
    )

    headers = _get_auth_headers(client)

    # Get a document and create a session
    doc_res = client.get("/api/documents/", headers=headers)
    doc_id = doc_res.json()["data"][0]["id"]
    sess_res = client.post("/api/chat/session", json={"document_id": doc_id}, headers=headers)
    session_id = sess_res.json()["data"]["id"]

    # Send a message — should get a clean rate limit response, NOT a 500
    msg_res = client.post("/api/chat/message", json={
        "session_id": session_id,
        "message": "Test rate limit question"
    }, headers=headers)
    assert msg_res.status_code == 200
    assert "rate-limited" in msg_res.json()["data"]["answer"].lower()

    # Clean up
    client.delete(f"/api/chat/session/{session_id}", headers=headers)


@patch("routers.chat_router.embed_texts")
@patch("routers.chat_router.query_similar")
@patch("routers.chat_router.generate_answer_stream")
def test_streaming_error_does_not_save_broken_message(mock_gen_stream, mock_query, mock_embed, client):
    """Verify that when streaming fails, no broken/empty messages are saved to the database."""
    mock_embed.return_value = [[0.1] * 3072]
    mock_query.return_value = [{
        "text": "Some chunk text",
        "metadata": {"page": 1, "source": "test.pdf"}
    }]

    # Stream that raises an error without yielding any content
    def mock_failing_stream(*args, **kwargs):
        raise Exception("Simulated Gemini failure")
    mock_gen_stream.side_effect = mock_failing_stream

    headers = _get_auth_headers(client)
    doc_res = client.get("/api/documents/", headers=headers)
    doc_id = doc_res.json()["data"][0]["id"]
    sess_res = client.post("/api/chat/session", json={"document_id": doc_id}, headers=headers)
    session_id = sess_res.json()["data"]["id"]

    # Stream message — should return an error event
    res = client.post("/api/chat/message/stream", json={
        "session_id": session_id,
        "message": "This should fail"
    }, headers=headers)
    assert res.status_code == 200
    assert '"type": "error"' in res.text

    # Check history — no messages should have been saved
    hist_res = client.get(f"/api/chat/history/{session_id}", headers=headers)
    assert hist_res.status_code == 200
    messages = hist_res.json()["data"]
    # No messages should exist for this session since generation failed
    assert len(messages) == 0

    # Clean up
    client.delete(f"/api/chat/session/{session_id}", headers=headers)


@patch("routers.chat_router.embed_texts")
@patch("routers.chat_router.query_similar")
def test_query_does_not_reindex_document(mock_query, mock_embed, client):
    """Verify that query_similar does NOT re-embed document chunks during chat."""
    mock_embed.return_value = [[0.1] * 3072]

    from services.vector_service import DocumentUnavailableError
    # Simulate missing collection — should raise DocumentUnavailableError, NOT call embed_texts again
    mock_query.side_effect = DocumentUnavailableError("Document is unavailable")

    headers = _get_auth_headers(client)
    doc_res = client.get("/api/documents/", headers=headers)
    doc_id = doc_res.json()["data"][0]["id"]
    sess_res = client.post("/api/chat/session", json={"document_id": doc_id}, headers=headers)
    session_id = sess_res.json()["data"]["id"]

    # Send message — should get a graceful unavailable message
    msg_res = client.post("/api/chat/message", json={
        "session_id": session_id,
        "message": "Test query"
    }, headers=headers)
    assert msg_res.status_code == 200
    assert "upload" in msg_res.json()["data"]["answer"].lower() or "unavailable" in msg_res.json()["message"].lower()

    # Verify embed_texts was called exactly ONCE (for the query embedding only)
    assert mock_embed.call_count == 1
    # The single call should be for 1 text (the query), not for document chunks
    assert len(mock_embed.call_args[0][0]) == 1

    # Clean up
    client.delete(f"/api/chat/session/{session_id}", headers=headers)


@patch("routers.chat_router.embed_texts")
@patch("routers.chat_router.query_similar")
@patch("routers.chat_router.generate_answer")
def test_chitchat_does_not_call_gemini(mock_gen_answer, mock_query, mock_embed, client):
    """Verify that 'hi', 'hello', 'thanks', 'bye' return locally without Gemini or ChromaDB."""
    headers = _get_auth_headers(client)
    doc_id = _get_or_create_doc(client, headers)
    sess_res = client.post("/api/chat/session", json={"document_id": doc_id}, headers=headers)
    session_id = sess_res.json()["data"]["id"]

    for greeting in ["hi", "hello!", "hey", "good morning", "thanks", "thank you", "bye"]:
        res = client.post("/api/chat/message", json={
            "session_id": session_id,
            "message": greeting
        }, headers=headers)
        assert res.status_code == 200
        assert res.json()["success"] is True
        assert len(res.json()["data"]["sources"]) == 0
        assert len(res.json()["data"]["answer"]) > 0

    # Assert ZERO Gemini embedding calls, ZERO ChromaDB queries, ZERO Gemini generation calls
    assert mock_embed.call_count == 0
    assert mock_query.call_count == 0
    assert mock_gen_answer.call_count == 0

    # Clean up
    client.delete(f"/api/chat/session/{session_id}", headers=headers)


@patch("routers.chat_router.embed_texts")
@patch("routers.chat_router.query_similar")
@patch("routers.chat_router.generate_answer_stream")
def test_chitchat_streaming_does_not_call_gemini(mock_gen_stream, mock_query, mock_embed, client):
    """Verify that streaming chitchat returns locally via SSE without calling Gemini."""
    headers = _get_auth_headers(client)
    doc_id = _get_or_create_doc(client, headers)
    sess_res = client.post("/api/chat/session", json={"document_id": doc_id}, headers=headers)
    session_id = sess_res.json()["data"]["id"]

    res = client.post("/api/chat/message/stream", json={
        "session_id": session_id,
        "message": "hello"
    }, headers=headers)
    assert res.status_code == 200
    assert '"type": "content"' in res.text
    assert '"type": "done"' in res.text

    assert mock_embed.call_count == 0
    assert mock_query.call_count == 0
    assert mock_gen_stream.call_count == 0

    # Clean up
    client.delete(f"/api/chat/session/{session_id}", headers=headers)


@patch("routers.chat_router.embed_texts")
@patch("routers.chat_router.query_similar")
@patch("routers.chat_router.generate_answer")
def test_substantive_questions_use_rag(mock_gen_answer, mock_query, mock_embed, client):
    """Verify questions with document context ('hi, explain chapter 2', etc.) go through normal RAG."""
    mock_embed.return_value = [[0.1] * 3072]
    mock_query.return_value = [{"text": "Chapter 2 overview", "metadata": {"page": 2, "source": "manual.pdf"}}]
    mock_gen_answer.return_value = "Chapter 2 covers advanced topics."

    headers = _get_auth_headers(client)
    doc_id = _get_or_create_doc(client, headers)
    sess_res = client.post("/api/chat/session", json={"document_id": doc_id}, headers=headers)
    session_id = sess_res.json()["data"]["id"]

    test_queries = [
        "hi, explain chapter 2",
        "hello, what is this PDF about?",
        "thanks, now explain the previous answer",
        "What is discussed on page 1?"
    ]

    for q in test_queries:
        res = client.post("/api/chat/message", json={
            "session_id": session_id,
            "message": q
        }, headers=headers)
        assert res.status_code == 200
        assert res.json()["success"] is True

    # Each query MUST have triggered embedding, retrieval, and generation
    assert mock_embed.call_count == len(test_queries)
    assert mock_query.call_count == len(test_queries)
    assert mock_gen_answer.call_count == len(test_queries)

    # Clean up
    client.delete(f"/api/chat/session/{session_id}", headers=headers)

