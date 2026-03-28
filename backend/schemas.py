from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, EmailStr, Field


class ApiResponse(BaseModel):
    success: bool
    data: Any = None
    message: str


class TokenData(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: Optional[str] = Field(default=None, max_length=255)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentOut(BaseModel):
    id: int
    user_id: int
    filename: str
    original_name: str
    file_type: str
    chunk_count: int
    chroma_collection_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChatSessionCreate(BaseModel):
    document_id: int


class ChatSessionOut(BaseModel):
    id: int
    document_id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ChatMessageCreate(BaseModel):
    session_id: int
    message: str = Field(min_length=1, max_length=4000)


class MessageOut(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChatAnswerOut(BaseModel):
    answer: str
    sources: List[str]
