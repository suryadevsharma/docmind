from typing import List
import zipfile

import fitz
from docx import Document as DocxDocument


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    words = text.split()
    if not words:
        return []

    chunks = []
    step = max(chunk_size - overlap, 1)
    for start in range(0, len(words), step):
        end = start + chunk_size
        chunk = " ".join(words[start:end]).strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(words):
            break
    return chunks


def parse_pdf(filepath: str) -> List[str]:
    pages_text = []
    with fitz.open(filepath) as pdf:
        for page in pdf:
            txt = page.get_text("text").strip()
            if txt:
                pages_text.append(txt)
    return chunk_text("\n".join(pages_text))


def parse_docx(filepath: str) -> List[str]:
    doc = DocxDocument(filepath)
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    return chunk_text("\n".join(paragraphs))


def detect_file_type(file_bytes: bytes) -> str:
    if file_bytes.startswith(b"%PDF"):
        return "pdf"

    if file_bytes.startswith(b"PK"):
        try:
            from io import BytesIO

            with zipfile.ZipFile(BytesIO(file_bytes)) as archive:
                names = set(archive.namelist())
                if "[Content_Types].xml" in names and "word/document.xml" in names:
                    return "docx"
        except Exception:
            return "unknown"

    return "unknown"
