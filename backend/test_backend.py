import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Mock heavy third-party libraries to avoid slow loading/downloads/network calls during tests
sys.modules["sentence_transformers"] = MagicMock()
sys.modules["chromadb"] = MagicMock()
sys.modules["chromadb.errors"] = MagicMock()
sys.modules["google"] = MagicMock()
sys.modules["google.generativeai"] = MagicMock()

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
    mock_embed_texts.return_value = [[0.1] * 384, [0.2] * 384]

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
    mock_embed.return_value = [[0.1] * 384]
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
    mock_embed.return_value = [[0.1] * 384]
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
