import os
import fitz  # pymupdf
import docx
from typing import List

knowledge_base: List[str] = []

def load_pdf(file_path: str) -> str:
    text = ""
    with fitz.open(file_path) as doc:
        for page in doc:
            text += page.get_text()
    return text

def load_docx(file_path: str) -> str:
    doc = docx.Document(file_path)
    return "\n".join([p.text for p in doc.paragraphs])

def split_text(text: str, max_tokens=500) -> List[str]:
    chunks = []
    current = ""
    for paragraph in text.split("\n"):
        if len(current) + len(paragraph) > max_tokens:
            chunks.append(current.strip())
            current = paragraph
        else:
            current += "\n" + paragraph
    if current.strip():
        chunks.append(current.strip())
    return chunks

def load_documents(folder: str = "presentations") -> List[str]:
    base = []
    for filename in os.listdir(folder):
        path = os.path.join(folder, filename)
        if filename.endswith(".pdf"):
            content = load_pdf(path)
        elif filename.endswith(".docx"):
            content = load_docx(path)
        else:
            continue
        base.extend(split_text(content))
    return base

def find_relevant_chunks(query: str, role: str, top_k: int = 3) -> List[str]:
    # очень простая метрика: находит фрагменты с совпадающими словами
    scores = []
    query_words = set(query.lower().split())
    for chunk in knowledge_base:
        chunk_words = set(chunk.lower().split())
        score = len(query_words & chunk_words)
        scores.append((score, chunk))
    scores.sort(reverse=True, key=lambda x: x[0])
    return [chunk for score, chunk in scores[:top_k] if score > 0]