import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from database import Base, engine
from routers.auth_router import router as auth_router
from routers.chat_router import router as chat_router
from routers.document_router import router as document_router

load_dotenv()

app = FastAPI(title="DocMind API", version="1.0.0")

os.makedirs(os.getenv("UPLOAD_DIR", "./uploads"), exist_ok=True)
os.makedirs(os.getenv("CHROMA_DIR", "./chroma_db"), exist_ok=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


@app.exception_handler(HTTPException)
async def http_exception_handler(_, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "data": None, "message": str(exc.detail)},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"success": False, "data": None, "message": f"Internal server error: {exc}"},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"success": False, "data": exc.errors(), "message": "Validation error"},
    )


@app.get("/")
async def root():
    return {"success": True, "data": {"app": "DocMind API"}, "message": "API is running"}


app.include_router(auth_router)
app.include_router(document_router)
app.include_router(chat_router)
