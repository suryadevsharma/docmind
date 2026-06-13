# DocMind Project Bible
*Private Interview Preparation & Technical Reference Guide*

---

## 1. COMPLETE ARCHITECTURE DIAGRAM (ASCII)

The diagram below represents the complete system topology, data flow, interface ports, and connection protocols of the DocMind application:

```text
                                        +----------------------------------------------------------------+
                                        |                   EXTERNAL API SERVICES                        |
                                        |                                                                |
                                        |  +--------------------+             +-----------------------+  |
                                        |  | Google Gemini API  |             | Hugging Face Hub      |  |
                                        |  | (1.5 Flash Model)  |             | (Embedding Weights)   |  |
                                        |  +---------+----------+             +-----------+-----------+  |
                                        +------------|------------------------------------|--------------+
                                                     ^ HTTPS (gRPC-backed)                | HTTPS
                                                     | (stream or block response)         | (First run download only)
                                                     v                                    v
+-----------------------------+         +------------+------------------------------------+--------------+
|       FRONTEND LAYER        |         |                   BACKEND SERVICES LAYER                       |
|                             |         |                                                                |
|  +-----------------------+  |  HTTP   |  +----------------------+             +---------------------+  |
|  | React SPA (Vite)      |  |  POST   |  | FastAPI Web Server   |  In-memory  | sentence-           |  |
|  | Run Port: localhost   |  | ------->|  | Run Port: localhost  |------------>| transformers        |  |
|  |           :5173       |  |  GET    |  |           :8000      |  Function   | all-MiniLM-L6-v2    |  |
|  |                       |  | <-------|  |                      |  Call       | (384 Dimensions)    |  |
|  | - React Router SPA    |  |         |  | - Auth Router        |             +---------------------+  |
|  | - Axios HTTP Intercept|  |         |  | - Document Router    |                        |
|  | - Markdown Renderer   |  |         |  | - Chat Router        |                        |
|  | - SSE Event Listener  |  |         |  +----------+-----------+                        |
|  +-----------------------+  |         +-------------|------------------------------------|--------------+
+-----------------------------+                       |                                    |
                                                      | SQLAlchemy                         | ChromaDB API
                                                      | Dialect                            | (Client SDK)
                                                      v                                    v
                                        +-------------+-----------+             +----------+----------+
                                        | MySQL Database          |             | ChromaDB Vector DB  |
                                        | Run Port: localhost     |             | (Local Persistent   |
                                        |           :3306         |             |  Storage)           |
                                        |                         |             |                     |
                                        | - users                 |             | - Collections per   |
                                        | - documents             |             |   User & Document:  |
                                        | - chat_sessions         |             |   user_{u}_doc_{d}  |
                                        | - messages              |             | - Sentence Chunks   |
                                        +-------------------------+             +---------------------+
```

---

## 2. EVERY TECHNOLOGY USED WITH REASON

### Backend Web Server
* **FastAPI**
  * *What it is:* A modern, fast (high-performance), web framework for building APIs with Python 3.8+ based on standard Python type hints.
  * *Why chose it over alternatives:* FastAPI outperforms Flask and Django in API development due to asynchronous performance (based on Starlette and Uvicorn) and automated OpenAPI (`/docs`) generation using Pydantic. It provides out-of-the-box validation which simplifies building structured JSON endpoints.
  * *Exactly where used:* Configured in [main.py](file:///c:/Users/Asus/OneDrive/Desktop/New%20folder/docmind/backend/main.py) and router modules in the [routers/](file:///c:/Users/Asus/OneDrive/Desktop/New%20folder/docmind/backend/routers/) directory.

* **SQLAlchemy & PyMySQL**
  * *What it is:* SQLAlchemy is a SQL Toolkit and Object-Relational Mapper (ORM); PyMySQL is a pure-Python MySQL client library.
  * *Why chose it over alternatives:* SQLAlchemy allows using raw SQL queries alongside abstract database models. Its connection pooling and dialect abstractions allow us to easily switch between local SQLite development and Render-hosted production MySQL without rewriting query logic.
  * *Exactly where used:* Database connection setup is in [database.py](file:///c:/Users/Asus/OneDrive/Desktop/New%20folder/docmind/backend/database.py), schema models are in [models.py](file:///c:/Users/Asus/OneDrive/Desktop/New%20folder/docmind/backend/models.py), and session queries are distributed across the endpoints.

* **Passlib (with bcrypt) & Python-Jose**
  * *What it is:* Passlib handles secure password hashing, and Python-Jose generates and verifies JSON Web Tokens (JWT).
  * *Why chose it over alternatives:* Standard cryptography packages can be complex. `passlib[bcrypt]` offers simple, secure bcrypt hashing with work-factor configuration. `python-jose` handles JWT generation and validation safely using HS256 HMAC algorithms.
  * *Exactly where used:* Hashing and token validation helpers are located in [auth.py](file:///c:/Users/Asus/OneDrive/Desktop/New%20folder/docmind/backend/auth.py).

### Parsing & Machine Learning
* **PyMuPDF (fitz)**
  * *What it is:* A highly optimized, fast PDF rendering and text extraction library.
  * *Why chose it over alternatives:* It is substantially faster than PyPDF2 or PDFMiner, and it retains exact layout coordinates and fonts. This makes it highly accurate when extracting structured paragraphs page-by-page.
  * *Exactly where used:* PDF parsing is implemented in [parser_service.py](file:///c:/Users/Asus/OneDrive/Desktop/New%20folder/docmind/backend/services/parser_service.py#L25-L38).

* **python-docx**
  * *What it is:* A library to read and manipulate Microsoft Word (.docx) files.
  * *Why chose it over alternatives:* It parses the underlying OpenXML format of Word files efficiently without requiring interop or external document conversion utilities.
  * *Exactly where used:* DOCX parsing is implemented in [parser_service.py](file:///c:/Users/Asus/OneDrive/Desktop/New%20folder/docmind/backend/services/parser_service.py#L41-L53).

* **Sentence-Transformers (`all-MiniLM-L6-v2`)**
  * *What it is:* A framework to generate dense vector representations (embeddings) from raw text paragraphs.
  * *Why chose it over alternatives:* The `all-MiniLM-L6-v2` model is a lightweight (80MB) transformer model running locally. It produces high-quality 384-dimensional embeddings, meaning we avoid paying for embedding APIs (like OpenAI's text-embedding-ada-002) and execute embeddings locally with minimal latency.
  * *Exactly where used:* Embeddings generation is in [embedding_service.py](file:///c:/Users/Asus/OneDrive/Desktop/New%20folder/docmind/backend/services/embedding_service.py).

* **ChromaDB**
  * *What it is:* An open-source, lightweight vector database designed for AI application embeddings.
  * *Why chose it over alternatives:* Unlike Pinecone (which requires cloud configurations and API keys) or pgvector (which requires extensive database setup), ChromaDB runs locally as a persistent, embedded database. This makes local development simple while still scaling efficiently for document RAG applications.
  * *Exactly where used:* Vector indexing, querying, and deletion are handled in [vector_service.py](file:///c:/Users/Asus/OneDrive/Desktop/New%20folder/docmind/backend/services/vector_service.py).

* **Google Generative AI SDK (`google-generativeai`)**
  * *What it is:* The official SDK for interacting with Google's Gemini models.
  * *Why chose it over alternatives:* We chose Google Gemini 1.5 Flash due to its massive 1M token context window, extremely fast inference speeds, low cost per token, and strong performance in handling multi-turn RAG conversations compared to OpenAI's GPT-3.5 or GPT-4o-mini.
  * *Exactly where used:* LLM configurations and prompt generation are structured in [llm_service.py](file:///c:/Users/Asus/OneDrive/Desktop/New%20folder/docmind/backend/services/llm_service.py).

### Frontend Web App
* **React 18 & Vite**
  * *What it is:* React is a declarative UI library; Vite is a fast frontend build tool and dev server.
  * *Why chose it over alternatives:* React's component-based architecture is perfect for building interactive stateful elements (like streaming chat interfaces). Vite replaces Create React App (CRA) by offering instant hot-module reloading (HMR) and highly optimized ESbuild production bundling.
  * *Exactly where used:* The frontend source directory [frontend/src/](file:///c:/Users/Asus/OneDrive/Desktop/New%20folder/docmind/frontend/src/).

* **Tailwind CSS**
  * *What it is:* A utility-first CSS framework for rapid UI styling.
  * *Why chose it over alternatives:* It prevents writing verbose stylesheets and keeps styling consistent. By applying responsive dark-themed utility classes directly in component JSX, we achieve custom styled layouts quickly without stylesheet bloat.
  * *Exactly where used:* Tailwind configurations are in [tailwind.config.js](file:///c:/Users/Asus/OneDrive/Desktop/New%20folder/docmind/frontend/tailwind.config.js), global styles in [index.css](file:///c:/Users/Asus/OneDrive/Desktop/New%20folder/docmind/frontend/src/index.css), and styles applied directly in JSX components.

* **Axios**
  * *What it is:* A promise-based HTTP client for the browser.
  * *Why chose it over alternatives:* Axios simplifies writing HTTP requests by automatically transforming JSON data. It supports request/response interceptors, allowing us to attach authorization headers and catch unauthorized (401) expired tokens globally.
  * *Exactly where used:* Setup and token management are in [axios.js](file:///c:/Users/Asus/OneDrive/Desktop/New%20folder/docmind/frontend/src/api/axios.js).

---

## 3. 50 INTERVIEW QUESTIONS WITH DETAILED ANSWERS

### Backend (10 Questions)

#### Q1: Why did you choose FastAPI over Flask or Django for this project?
FastAPI was chosen because it is built on top of Starlette and Pydantic, enabling high-performance asynchronous operations using `async/await`. Flask is synchronous and requires third-party packages for validation and documentation. Django is a heavy, battery-included framework suited for monolithic applications. In a RAG application, backend endpoints spend significant time waiting on external AI services and local vector search. FastAPI's asynchronous nature allows the event loop to serve other requests while waiting, resulting in higher throughput.

#### Q2: Explain the authentication mechanism in this project.
Authentication is handled using stateless JWT (JSON Web Tokens). When a user registers or logs in via `/api/auth/register` or `/api/auth/login`, we check their credentials. If valid, we create a token signed with an HMAC-SHA256 signature containing their `sub` (user_id) as the payload and a configured expiration time. In [auth.py](file:///c:/Users/Asus/OneDrive/Desktop/New%20folder/docmind/backend/auth.py#L41-L59), the dependency function `get_current_user` extracts the token from the HTTP `Authorization: Bearer <token>` header, decodes it using our `SECRET_KEY`, and queries the database to retrieve the current user context.

#### Q3: Describe the API endpoint structure and standard response contract.
All API endpoints are grouped under logical routers: `auth_router`, `document_router`, and `chat_router`. Every endpoint returns a consistent response envelope modeled after the standard API contract defined in [schemas.py](file:///c:/Users/Asus/OneDrive/Desktop/New%20folder/docmind/backend/schemas.py#L8-L12):
```json
{
  "success": true,
  "data": {},
  "message": "..."
}
```
This is enforced using Pydantic serialization models (such as `UserOut`, `DocumentOut`, `ChatSessionOut`), which ensures that internal schemas or sensitive fields (like `hashed_password`) are never leaked to the client.

#### Q4: How is database connection pooling and lifecycle managed?
Database sessions are managed using SQLAlchemy's `sessionmaker` in [database.py](file:///c:/Users/Asus/OneDrive/Desktop/New%20folder/docmind/backend/database.py). We create a single SQL engine with `pool_pre_ping=True` to automatically recycle stale connections. The function `get_db` is defined as a generator:
```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```
FastAPI endpoints inject this connection using the `Depends(get_db)` dependency. This guarantees that a database connection is created when a request starts and closed once the response is sent.

#### Q5: How is request validation enforced on incoming payloads?
Request validation is managed by Pydantic schemas. In [schemas.py](file:///c:/Users/Asus/OneDrive/Desktop/New%20folder/docmind/backend/schemas.py), we define models like `UserCreate` with typed fields and constraints:
```python
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: Optional[str] = Field(default=None, max_length=255)
```
If a client sends an invalid request, FastAPI intercepts it and returns a `422 Unprocessable Entity` response detailing the validation error, rather than letting the request crash downstream code.

#### Q6: How do you handle errors and exceptions globally in FastAPI?
In [main.py](file:///c:/Users/Asus/OneDrive/Desktop/New%20folder/docmind/backend/main.py#L44-L65), we define global exception handlers for `HTTPException`, validation errors (`RequestValidationError`), and unhandled generic `Exception` types. These catch any errors raised in routers, format them to match our standard `{ success: false, data: None, message: str(exc.detail) }` JSON contract, and log the traceback while returning appropriate HTTP status codes (e.g., 400 for bad parameters, 500 for backend bugs).

#### Q7: Describe how file uploads work in this application. What validations do you perform?
In [document_router.py](file:///c:/Users/Asus/OneDrive/Desktop/New%20folder/docmind/backend/routers/document_router.py#L29-L109), the `/api/documents/upload` endpoint takes an `UploadFile`. We validate the following:
1. **Size Limit:** We read the file stream bytes and check if they exceed the maximum size (default 10MB) configured in `.env`.
2. **File Signature:** We read the starting bytes to verify the magic numbers (`%PDF` for PDFs and `PK` zip signature for DOCX) in [parser_service.py](file:///c:/Users/Asus/OneDrive/Desktop/New%20folder/docmind/backend/services/parser_service.py#L57-L72). This prevents extension spoofing.
3. **Filename Integrity:** We verify the filename exists and matches the detected extension before saving it locally.

#### Q8: What security measures have you implemented in the backend?
We have implemented several layers of security:
1. **Password Hashing:** Passwords are hashed using bcrypt with dynamic salts.
2. **Input Sanitization:** Fast APIs check payload structures using Pydantic, preventing basic injection attacks.
3. **Token Signatures:** Access tokens use HSM/HMAC SHA256 signatures with expiration validation.
4. **File Validation:** We validate file byte signatures, not just extensions, to prevent shell uploads.
5. **Secure Storage:** Uploaded files are renamed using randomly generated UUIDs, preventing directory traversal attacks.

#### Q9: What is the difference between async and sync routing, and where did you use each?
Endpoints that perform database operations or parse documents are written as `async def` in FastAPI. While SQLAlchemy operations are technically blocking (synchronous), writing async endpoints allows FastAPI to run them on a threadpool, preventing blocking the main thread.
For streaming chat completions, we use `async def` and yield chunks asynchronously over a `StreamingResponse` using generator functions. This avoids blocking connections while the LLM generates tokens.

#### Q10: How would you scale this backend to handle 10,000 requests per minute?
To scale the backend:
1. **Stateless Web Nodes:** Since FastAPI uses stateless JWTs, we can run multiple containerized Uvicorn instances behind an Nginx or AWS ALB load balancer.
2. **Database Connection Pool:** Implement a connection pooling layer like PgBouncer (if migrating to Postgres) or configure SQLAlchemy's connection limits.
3. **Asynchronous Task Queue:** Move parsing and embedding logic (which are CPU-bound) out of the main thread and into a Celery/Redis task queue.
4. **Distributed Vector Store:** Move ChromaDB from an embedded local instance to a client-server setup hosted on a dedicated database instance.

---

### Database (8 Questions)

#### Q11: Why did you choose MySQL as the relational database instead of MongoDB?
MySQL was chosen because this application requires relational integrity. Chat sessions, user records, documents, and messages have clear, nested relationships. For example, deleting a document must cascade to delete all associated chat sessions, which in turn cascades to delete all messages. MySQL handles ACID transactions and relational constraints natively. Combined with SQLAlchemy, it guarantees referential integrity, whereas MongoDB's document model would require manual, complex relational integrity checks.

#### Q12: Walk through the database schema. What tables exist and why?
There are four tables defined in [models.py](file:///c:/Users/Asus/OneDrive/Desktop/New%20folder/docmind/backend/models.py):
1. `users`: Stores user identity (`email`, `hashed_password`, `full_name`).
2. `documents`: Metadata of uploaded files (`filename` UUID, `original_name`, `file_type`, `chunk_count`, and `chroma_collection_id`).
3. `chat_sessions`: Tracks distinct chat windows opened against a specific document.
4. `messages`: Stores individual dialogue turns (`role` as user/assistant, `content` text, and JSON-serialized `sources` for citations).

#### Q13: Explain the relationships between your tables.
The tables are linked using relational foreign keys with cascading deletions:
* `User.id` has a one-to-many relationship with `Document` and `ChatSession`.
* `Document.id` has a one-to-many relationship with `ChatSession`. If a document is deleted, all chat sessions targeting that document are automatically deleted (`ondelete="CASCADE"`).
* `ChatSession.id` has a one-to-many relationship with `Message`. If a session is deleted, all messages in that session are deleted.

#### Q14: How are message citations stored in the database?
In [models.py](file:///c:/Users/Asus/OneDrive/Desktop/New%20folder/docmind/backend/models.py#L60), the `Message` table has a `sources` column configured as `Column(Text, nullable=True)`. This stores a JSON-serialized list of dictionaries containing keys for the source text snippet, page number, and original file name. When fetching history in [schemas.py](file:///c:/Users/Asus/OneDrive/Desktop/New%20folder/docmind/backend/schemas.py#L81-L89), a Pydantic `field_validator` deserializes this string back into a JSON array for the React frontend to display.

#### Q15: What is your database indexing strategy?
We index columns that are frequently used in `WHERE` clauses, sorting, or `JOIN` operations:
* `users.email`: Indexed and marked unique to ensure fast lookups during login.
* `documents.user_id`: Indexed to quickly retrieve a user's uploaded files.
* `chat_sessions.document_id` and `user_id`: Indexed for quick chat history lookups.
* `messages.session_id`: Indexed to fetch dialogue histories in order.

#### Q16: How do you optimize query performance as tables grow?
1. **Limit Columns:** We fetch specific fields when possible rather than using `SELECT *`.
2. **Eager Loading:** In multi-table fetches, we use SQLAlchemy `joinedload` or `subqueryload` to prevent the N+1 query problem.
3. **Database Indexing:** Ensure all foreign key columns have indexes.
4. **Pagination:** Implement offsets or cursor-based pagination on messages and documents, returning smaller chunks of data to the client.

#### Q17: How is the database seeded for development and testing?
Seeding is handled dynamically. In [test_backend.py](file:///c:/Users/Asus/OneDrive/Desktop/New%20folder/docmind/backend/test_backend.py), we create an in-memory SQLite database (`test_docmind.db`) for testing, generate the schemas, and register a mock user. For local development, running `uvicorn main:app` invokes SQLAlchemy's `create_all()` hook on startup in [main.py](file:///c:/Users/Asus/OneDrive/Desktop/New%20folder/docmind/backend/main.py#L31-L42), creating the database structure automatically.

#### Q18: What is the ORM configuration and dialect abstraction?
We instantiate database sessions using:
```python
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
```
The `DATABASE_URL` is read from environmental variables. In local development, this defaults to `sqlite:///./docmind.db` which is parsed by SQLite. In production, we pass `mysql+pymysql://...`, and SQLAlchemy handles the dialect translation without changes to our models.

---

### Machine Learning / AI (10 Questions)

#### Q19: Which embedding model did you choose and why?
We chose `sentence-transformers/all-MiniLM-L6-v2`. It is a lightweight (80MB) transformer model trained on over 1 billion sentence pairs. It maps sentences and paragraphs to a dense 384-dimensional vector space. We chose it because it can run locally on CPU with minimal latency, avoiding the network costs and rate limits of external APIs. It performs well on semantic search tasks, matching query meaning to document segments.

#### Q20: Explain the document parsing and chunking strategy.
In [parser_service.py](file:///c:/Users/Asus/OneDrive/Desktop/New%20folder/docmind/backend/services/parser_service.py), documents are split page-by-page. Extracted page text is parsed into word arrays and chunked using a sliding window:
* **Chunk Size:** 500 words. This ensures each block has enough context for the LLM.
* **Overlap:** 50 words. This prevents losing context for information split across chunk boundaries.
For PDFs, we extract text page-by-page. For DOCX, we read paragraph arrays and estimate the page number.

#### Q21: What vector database is used and how is it initialized?
We use ChromaDB. It is initialized in [vector_service.py](file:///c:/Users/Asus/OneDrive/Desktop/New%20folder/docmind/backend/services/vector_service.py) as a persistent client on disk:
```python
CHROMA_DIR = os.getenv("CHROMA_DIR", "./chroma_db")
_client = chromadb.PersistentClient(path=CHROMA_DIR)
```
Collections are created dynamically per document. Each document index gets a unique identifier (`user_{user_id}_doc_{doc_id}`). This structure keeps data isolated and prevents users from querying other users' indexes.

#### Q22: What are the input features and dimensions of your vectors?
The input features are raw text paragraphs extracted from documents. The embedding model (`all-MiniLM-L6-v2`) converts these text chunks into 384-dimensional floating-point vector lists. The cosine similarity calculation in ChromaDB uses these dimensions to rank relevant document chunks against user queries.

#### Q23: Walk through the retrieval (vector query) process in detail.
When a user asks a question:
1. The question is converted into a 384-dimensional vector using the local embedding service:
   `question_vec = embed_texts([question])[0]`
2. We query ChromaDB using this vector:
   `chunks = query_similar(doc.chroma_collection_id, question_vec, n_results=5)`
3. ChromaDB calculates cosine similarity against the collection and returns the top 5 matching text chunks along with metadata (page number, source filename).

#### Q24: Which LLM is used and how does it generate answers?
We use Google Gemini 1.5 Flash via the `google-generativeai` SDK. In [llm_service.py](file:///c:/Users/Asus/OneDrive/Desktop/New%20folder/docmind/backend/services/llm_service.py), the model is configured with a strict system prompt:
```text
You are a helpful document assistant. Answer questions only based on the provided document context. If the answer is not in the context, say 'I could not find this information in the document.' Be concise and accurate.
```
We combine this system prompt, the retrieved document context, the user's query, and the recent chat history into a single prompt for Gemini to generate the answer.

#### Q25: How does the backend support streaming answers?
In [llm_service.py](file:///c:/Users/Asus/OneDrive/Desktop/New%20folder/docmind/backend/services/llm_service.py#L84-L108), the function `generate_answer_stream` calls Gemini with `stream=True`:
```python
response = _model.generate_content(prompt, stream=True)
for chunk in response:
    if chunk.text:
        yield chunk.text
```
The chat router wraps this generator in a FastAPI `StreamingResponse` using the `text/event-stream` media type. This allows the server to stream tokens to the frontend as they are generated, reducing perceived latency.

#### Q26: What is the fallback mechanism if the Gemini API quota is exceeded?
If the Gemini API fails due to rate limits (HTTP 429) or quota issues, the system runs an extractive fallback in [llm_service.py](file:///c:/Users/Asus/OneDrive/Desktop/New%20folder/docmind/backend/services/llm_service.py#L52-L60):
```python
def _extractive_fallback(context_chunks: list[str]) -> str:
    if not context_chunks:
        return "I could not find this information in the document."
    snippet = context_chunks[0][:500].strip()
    return f"I am temporarily unable to use the Gemini API quota. Based on the top retrieved document section:\n\n{snippet}"
```
This returns the most relevant raw text chunk directly to the user rather than failing completely.

#### Q27: How does the system remember conversation history?
We support conversational memory by storing chat logs in the relational database. When querying the LLM, the chat router fetches the last 6 messages from the database for the active session, formats them as a conversational log, and includes them in the prompt context. This allows the model to resolve contextual follow-up questions (like "What did the previous section say about that?").

#### Q28: What are the main real-world limitations of this RAG pipeline?
1. **Parsing Non-Text Formats:** Scanned image PDFs are ignored because we do not run OCR (Optical Character Recognition).
2. **Keyword Match vs semantic:** Standard embedding models can struggle with highly technical terms or acronyms if they are not represented in the training data.
3. **Simple Chunking:** Our sliding word window can split related concepts across chunks. Using semantic chunking would improve accuracy.
4. **Context Window Limits:** While Gemini supports massive context windows, querying a large number of retrieved chunks increases latency.

---

### Frontend (7 Questions)

#### Q29: Describe the React component layout and view structure.
The UI uses a single-page React architecture:
* **Authentication Pages:** [Login.jsx](file:///c:/Users/Asus/OneDrive/Desktop/New%20folder/docmind/frontend/src/pages/Login.jsx) and [Register.jsx](file:///c:/Users/Asus/OneDrive/Desktop/New%20folder/docmind/frontend/src/pages/Register.jsx) manage credential validation and JWT storage.
* **Workspace Dashboard:** [Dashboard.jsx](file:///c:/Users/Asus/OneDrive/Desktop/New%20folder/docmind/frontend/src/pages/Dashboard.jsx) lists uploaded document cards and manages upload modals.
* **Workspace Chat:** [ChatPage.jsx](file:///c:/Users/Asus/OneDrive/Desktop/New%20folder/docmind/frontend/src/pages/ChatPage.jsx) displays the interactive workspace, containing active chat sessions and the document chat window.

#### Q30: How is state managed in the frontend?
State is managed locally using React hooks. Since the application views are clearly separated, we do not need complex state containers like Redux. 
* We use `useState` for UI states (like active sessions, document lists, and upload progress).
* We use `useMemo` to cache derived states (like formatting document titles) to prevent unnecessary re-renders.
* We use `useRef` to target DOM nodes, such as scrolling the chat window to the bottom when new tokens arrive.

#### Q31: Explain the routing setup and route protection.
Routing is managed by `react-router-dom` in [App.jsx](file:///c:/Users/Asus/OneDrive/Desktop/New%20folder/docmind/frontend/src/App.jsx). We wrap secure routes (Dashboard, ChatPage) with a `ProtectedRoute` wrapper:
```javascript
function ProtectedRoute({ children }) {
  const token = localStorage.getItem("token");
  if (!token) return <Navigate to="/login" replace />;
  return children;
}
```
If a user is unauthenticated, they are redirected to `/login`. If the API returns a 401 error, an Axios interceptor clears the token and redirects the browser back to the login screen.

#### Q32: How does the client communicate with the streaming API endpoint?
To receive streaming data, we use the browser's native `fetch` API rather than Axios because Axios does not natively support reading streams line-by-line. In [ChatWindow.jsx](file:///c:/Users/Asus/OneDrive/Desktop/New%20folder/docmind/frontend/src/components/ChatWindow.jsx), we read the stream using a reader loop:
```javascript
const reader = response.body.getReader();
const decoder = new TextDecoder();
// Read chunk-by-chunk and parse by event boundaries
```
This updates the chat UI in real-time as chunks are received.

#### Q33: How are source citations and snippets rendered?
Citations are rendered as interactive elements. In [MessageBubble.jsx](file:///c:/Users/Asus/OneDrive/Desktop/New%20folder/docmind/frontend/src/components/MessageBubble.jsx#L41-L60), we map the `sources` array to HTML `<details>` elements:
* The summary line displays the source name and page number.
* Clicking the element expands it to show the full text snippet.
This allows users to verify answers without cluttering the chat history.

#### Q34: What styling system is used and how is responsiveness managed?
We use Tailwind CSS. Responsiveness is built using utility classes like `flex-col lg:flex-row`. For example, on mobile screens, the chat session sidebar sits above the conversation thread, but on desktop screens, it moves to the side using grid layouts. Buttons and modals use transitions (`transition duration-300`) to create a polished user experience.

#### Q35: What performance optimizations have you implemented on the client?
1. **Optimistic UI Updates:** When a message is sent, we add the user message and an assistant placeholder to the UI immediately, before the request completes. This makes the interface feel fast and responsive.
2. **Selective State Updates:** We only update the specific message bubble receiving tokens, preventing full-list re-renders.
3. **Lazy Bundle Compilation:** Vite bundles assets into chunked files, keeping the initial bundle size small.

---

### Deployment & DevOps (7 Questions)

#### Q36: Describe the production deployment architecture.
* **Frontend:** Hosted on Vercel. Static assets are served from Vercel's global CDN.
* **Backend:** Hosted on Render as an ASGI web service running Uvicorn.
* **Database:** Hosted on an external MySQL database linked via connection strings.
* **Vector Storage:** Local ChromaDB data is persisted on Render's local disk volume.

#### Q37: What environment variables are required for this application?
The backend requires:
* `DATABASE_URL`: Connection string for the MySQL database.
* `SECRET_KEY`: Security salt for signing JWT tokens.
* `GEMINI_API_KEY`: Google Generative AI access credential.
* `CHROMA_DIR` & `UPLOAD_DIR`: Output folder paths for indexes and documents.
The frontend requires:
* `VITE_API_BASE_URL`: The URL of the hosted backend API.

#### Q38: How does the build process work?
* **Backend:** Render reads `requirements.txt`, installs the dependencies, and runs `uvicorn main:app --host 0.0.0.0 --port $PORT`. On startup, SQLAlchemy creates any missing database tables.
* **Frontend:** Vercel installs the npm packages, compiles JSX, and runs `vite build`. The resulting static assets in `dist/` are deployed to Vercel's hosting nodes.

#### Q39: What free tier limitations did you face and how did you resolve them?
1. **Cold Starts:** Render's free tier spins down backend web services after 15 minutes of inactivity. To resolve this, we can set up a ping cron job to keep the service warm.
2. **Ephemeral Disk Storage:** Render's free instances wipe the local filesystem on rebuilds. For production, we can connect ChromaDB to a cloud instance or mount a persistent disk volume.
3. **Gemini API Limits:** Gemini's free tier has a rate limit of 15 requests per minute. We handle this with backend rate limiting and our extractive fallback system.

#### Q40: How is the application containerized with Docker?
The project includes a `Dockerfile` in the [backend/](file:///c:/Users/Asus/OneDrive/Desktop/New%20folder/docmind/backend/Dockerfile) directory:
```dockerfile
FROM python:3.10
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```
This containerizes the application environment, making it easy to deploy on container orchestration platforms like AWS ECS, GCP Cloud Run, or Kubernetes.

#### Q41: Explain the differences between development and production environments.
* **Database:** Development uses a local SQLite database file, while production uses a remote MySQL database.
* **CORS:** Development allows origins from localhost, while production restricts CORS headers to the deployed frontend domain.
* **Debugging:** Development runs Uvicorn with `--reload` enabled for fast iteration, which is disabled in production for performance.
* **Logging:** Production routes backend errors to a logging service, hiding raw stack traces from clients for security.

#### Q42: How does vercel.json handle routing for React Router?
In our newly created [vercel.json](file:///c:/Users/Asus/OneDrive/Desktop/New%20folder/docmind/frontend/vercel.json) file:
```json
{
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ]
}
```
This rewrite rule tells Vercel's server to redirect all requests to `index.html`. This allows React Router to handle page navigation in the browser, preventing 404 errors when refreshing the page on sub-routes.

---

### Project & System Design (8 Questions)

#### Q43: Walk through the system design of the application.
The application is structured into four main layers:
1. **Client (React):** Manages the user interface, session state, and SSE streaming.
2. **API Gate (FastAPI):** Handles authentication, request validation, and rate limiting.
3. **Database (MySQL):** Stores relational schemas for users, sessions, and chat logs.
4. **AI & Vector Pipeline:** Manages text chunking, local embeddings, vector retrieval, and Gemini completions.
This design separates concern, making it easy to swap frontend components or backend frameworks without affecting the core data pipeline.

#### Q44: What was the hardest technical challenge you faced and how did you resolve it?
The hardest challenge was implementing fast, responsive streaming completions while maintaining accurate search citations. Initially, using standard API calls caused long wait times for users. 
We resolved this by implementing a dual-event streaming system. When a message is sent, the backend first queries ChromaDB and immediately yields the source citations as a structured JSON SSE event. The server then streams the LLM response word-by-word. This approach keeps response times fast while preserving citation accuracy.

#### Q45: Walk through the end-to-end flow of uploading a document.
1. The user drops a file in the React frontend.
2. The client uploads the file to `/api/documents/upload` with a JWT auth header.
3. The backend validates the file signature (magic bytes) and size.
4. The document is saved to the local `uploads/` folder with a unique UUID name.
5. `PyMuPDF` extracts the text page-by-page.
6. The text is chunked into 500-word blocks with 50-word overlaps.
7. Local embeddings are generated for each chunk.
8. The chunks, vectors, and metadata are indexed in a document-specific ChromaDB collection.
9. Relational metadata is saved to the MySQL database, and the frontend updates the workspace.

#### Q46: Walk through the end-to-end flow of sending a chat message.
1. The user types a message in the session chat window.
2. The client displays the user's message immediately (optimistic UI update).
3. The client opens an HTTP POST connection to `/api/chat/message/stream`.
4. The backend verifies the session exists and rate-limits the request.
5. The query is converted to a vector using the local embedding service.
6. ChromaDB retrieves the top 5 matching text chunks.
7. The backend yields the source citations as the first stream event.
8. Recent chat history and retrieved chunks are combined into a prompt for Gemini.
9. The backend streams Gemini's response token-by-token to the client.
10. Once complete, the backend saves the dialogue exchange to the database and closes the stream.

#### Q47: How is data isolation maintained between different users?
We enforce data isolation at both database and vector layers:
* **Relational Layer:** All database queries filter by `user_id` using the authenticated user context (e.g., `db.query(Document).filter(Document.user_id == current_user.id)`).
* **Vector Layer:** Collections are created with user-specific names: `user_{user_id}_doc_{doc_id}`. This prevents users from accessing indexes belonging to other users, even if they guess a document ID.

#### Q48: What features would you add next to this project?
1. **Asynchronous Processing:** Use Celery and Redis to process large documents in the background.
2. **Hybrid Search:** Combine semantic vector retrieval with keyword-based search (BM25) to improve query relevance.
3. **Multi-Document Chat:** Allow users to query multiple documents at the same time in a single chat session.
4. **OCR Integration:** Add an OCR engine like Tesseract to extract text from scanned images and PDFs.

#### Q49: How would you scale the AI pipeline to handle a massive increase in active users?
* **Dedicated Embedding Service:** Move the embedding model to a dedicated container on an instance with GPU acceleration.
* **Dedicated Vector Instance:** Move ChromaDB from an embedded local instance to a managed vector search service (like Pinecone or pgvector).
* **Distributed Rate Limiting:** Replace the in-memory rate limiter with a Redis-backed token bucket system, allowing rate limits to be shared across multiple backend web nodes.

#### Q50: What makes this project unique compared to basic RAG tutorials?
Most tutorials use cloud services (like OpenAI and Pinecone) for their entire pipeline, which can be expensive. This project runs its core parsing, chunking, embedding, and vector database layers locally. Additionally, it features dynamic collection names for data isolation, a secure file validation pipeline, database-backed conversation history, and real-time streaming citations. These additions make it a production-ready, secure application rather than a basic prototype.

---

## 4. KEY NUMBERS TO MEMORIZE

* **13 API Endpoints:** Complete API surface (3 Auth, 3 Documents, 6 Chat, 1 Root Health Check).
* **4 Database Tables:** `users`, `documents`, `chat_sessions`, and `messages`.
* **384 Vector Dimensions:** The output size of embeddings generated by `all-MiniLM-L6-v2`.
* **500 Words Chunk Size:** The sliding window size used to parse documents.
* **50 Words Overlap:** The overlap size used to preserve context between chunks.
* **10 Megabytes:** The maximum file size allowed for uploads.
* **20 Messages per Minute:** The rate limit per user for the chat API.
* **6 Messages:** The lookback limit used to load conversation history for context.
* **Top 5 Chunks:** The number of retrieved document snippets passed to Gemini for answer generation.
* **1M Tokens:** The context window size supported by Google Gemini 1.5 Flash.

---

## 5. 2-MINUTE SPOKEN PITCH

### Problem Statement (2-3 sentences)
"Many organizations struggle to search and retrieve information from large volumes of internal documentation, such as PDFs and Word files. Users often spend hours manually reading through pages to find answers, while using generic public AI models can leak sensitive data and lead to incorrect answers."

### How it Works (3-4 sentences)
"To solve this, I built DocMind, a secure, document-based QA application. The backend is built with FastAPI, which handles file uploads, validates file signatures, and chunks text. It generates vector embeddings locally using the `all-MiniLM-L6-v2` transformer model and indexes them in a persistent ChromaDB database. When a user asks a question, the system retrieves relevant snippets, formats them as context, and streams the answer using Google Gemini 1.5 Flash alongside verified citations."

### Uniqueness (2-3 sentences)
"What makes DocMind unique is its local-first approach to data processing, which handles embeddings and vector indexing locally to reduce API costs. It also features strict multi-tenant data isolation by creating separate vector collections per user, and includes a fallback retrieval system if LLM limits are exceeded."

### Personal Contribution (2-3 sentences)
"I developed the end-to-end application, including building the FastAPI routes, designing the database models with SQLAlchemy, and setting up the local vector search pipeline. On the frontend, I built the React workspace with responsive Tailwind CSS layouts and implemented an SSE connection to stream text and citations to the user in real-time."

### Impact & Results (1-2 sentences)
"The resulting application provides an interactive, secure QA system with response times under two seconds. The test suite verifies that all endpoints run successfully in less than seven seconds."
