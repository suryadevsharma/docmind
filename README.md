# DocMind

Production-ready RAG Document Q&A app for uploading PDF/DOCX files and chatting with their contents using AI.

## Screenshot Placeholder

- `docs/screenshots/login.png`
- `docs/screenshots/dashboard.png`
- `docs/screenshots/chat.png`

## Features

- JWT authentication (register, login, current user endpoint)
- Secure document upload with file signature validation (PDF/DOCX) and size limit
- Parsing and chunking pipeline (500 tokens, 50 overlap)
- Google Gemini Embeddings (`gemini-embedding-001`) + persistent ChromaDB vector search
- Gemini 2.5/3.5 Flash answer generation with retrieval context and chat memory
- Session-based document chat history persisted in MySQL
- Real-time streaming chat completions using Server-Sent Events (SSE) and robust client-side buffering
- Comprehensive backend integration test suite with fast, mock-driven execution
- Responsive dark-themed React UI with upload modal, document cards, and source snippets
- Basic rate limiting for chat endpoint (20 messages/minute/user)
- Standard API response contract: `{ success, data, message }`

## Architecture Diagram (ASCII)

```text
+-------------------+        HTTPS         +----------------------+
| React + Vite UI   | <------------------> | FastAPI Backend      |
| (Vercel)          |                      | (Render)             |
+-------------------+                      +----------+-----------+
                                                      |
                                                      | SQLAlchemy
                                                      v
                                            +----------------------+
                                            | MySQL               |
                                            | users/documents/... |
                                            +----------------------+
                                                      |
                                                      | vector ops
                                                      v
                                            +----------------------+
                                            | ChromaDB (local)    |
                                            | chunk embeddings     |
                                            +----------------------+
                                                      |
                                                      | context + prompt
                                                      v
                                            +----------------------+
                                            | Gemini 2.5 Flash    |
                                            +----------------------+
```

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, SQLAlchemy, PyMySQL, python-jose, bcrypt |
| Parsing | PyMuPDF, python-docx |
| Embeddings | Google Gemini Embeddings (`gemini-embedding-001`) |
| Vector DB | ChromaDB (persistent local storage) |
| LLM | Google Gemini 2.5/3.5 Flash (`google-generativeai`) |
| Frontend | React 18, Vite, Tailwind CSS, Axios |
| Deployment | Render (API), Vercel (Web) |

## Local Setup

1. Clone and enter project:
   - `git clone <your-repo-url>`
   - `cd docmind`
2. Backend setup:
   - `cd backend`
   - `python -m venv .venv`
   - Windows: `.venv\Scripts\activate`
   - `pip install -r requirements.txt`
   - `copy .env.example .env` and update values (MySQL + Gemini key)
   - Ensure MySQL database `docmind` exists
   - Run API: `uvicorn main:app --reload --port 8000`
3. Frontend setup:
   - `cd ../frontend`
   - `npm install`
   - `copy .env.example .env`
   - `npm run dev`
4. Open app at `http://localhost:5173`

### Running Tests

We have a fast, mock-driven backend integration test suite that tests authentication, document upload, standard chat, and streaming chat endpoints without requiring network calls or loading heavy model files:

1. Enter backend folder: `cd backend`
2. Run pytest using the virtual environment:
   * Windows: `..\.venv\Scripts\python -m pytest test_backend.py`
   * Unix/macOS: `../.venv/bin/python -m pytest test_backend.py`

## API Documentation

Base URL: `http://localhost:8000`

### Auth

- `POST /api/auth/register`
  - Body: `{ email, password, full_name }`
- `POST /api/auth/login`
  - Body: `{ email, password }`
- `GET /api/auth/me`
  - Header: `Authorization: Bearer <token>`

### Documents

- `POST /api/documents/upload`
  - Auth required
  - Multipart: `file` (PDF/DOCX, max 10MB)
- `GET /api/documents/`
  - Auth required
- `DELETE /api/documents/{document_id}`
  - Auth required

### Chat

- `POST /api/chat/session`
  - Auth required
  - Body: `{ document_id }`
- `POST /api/chat/message`
  - Auth required
  - Body: `{ session_id, message }`
- `GET /api/chat/history/{session_id}`
  - Auth required
- `GET /api/chat/sessions/{document_id}`
  - Auth required

All responses follow:

```json
{
  "success": true,
  "data": {},
  "message": "..."
}
```

## Deployment Guide

### Backend on Render

1. Create a new Web Service from repo, root set to `backend`.
2. Build command: `pip install -r requirements.txt`
3. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Add environment variables from `backend/.env.example`.
5. Provision/render-link external MySQL database and update `DATABASE_URL`.
6. Deploy and verify `/` health endpoint.

### Frontend on Vercel

1. Import repo in Vercel and set root directory to `frontend`.
2. Build command: `npm run build`
3. Output directory: `dist`
4. Add `VITE_API_BASE_URL` as Render backend URL.
5. Deploy and test auth, upload, and chat flow.

## Future Improvements

- Background job queue for large document processing
- Token-aware chunking and metadata-enriched retrieval
- Typing indicators for streaming transitions
- Role-based access and organization-level document sharing
- Frontend end-to-end (e2e) tests using Cypress or Playwright
- Redis-backed distributed rate limiting
