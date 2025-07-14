# knowledge_base.py
from pathlib import Path

ROLE_TO_TOPICS = {
    "client": ["ЛИТРО", "реакционные", "преимущества", "гарантия", "услуги", "комиссия"],
    "manager": ["ситуации", "кейсы", "отказ", "клиент", "КАСКО", "кредит", "банк"]
}

def load_documents():
    chunks = []
    base_dir = Path("files")  # путь к папке с документами
    
    files = {
        "реакционные скрипты Литро.pdf": base_dir / "реакционные скрипты Литро.pdf",
        "Ситуационные кейсы.docx": base_dir / "Ситуационные кейсы.docx",
        "Welcome-курс.docx": base_dir / "Welcome-курс.docx"
    }

    import docx, fitz  # PyMuPDF для PDF
    for name, path in files.items():
        if not path.exists(): continue

        if path.suffix == ".docx":
            doc = docx.Document(path)
            text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        elif path.suffix == ".pdf":
            pdf = fitz.open(path)
            text = "\n".join(page.get_text() for page in pdf)
        else:
            continue
        
        # Разделение по смысловым блокам (на абзацы по 5 строк)
        for part in text.split("\n\n"):
            if len(part.strip()) > 100:
                chunks.append({
                    "source": name,
                    "text": part.strip().replace("\n", " ")
                })

    return chunks

def find_relevant_chunks(query: str, role: str, limit=3):
    query_lower = query.lower()
    topics = ROLE_TO_TOPICS.get(role, [])
    results = []

    for chunk in knowledge_base:
        if any(topic in chunk["text"].lower() for topic in topics):
            if query_lower.split()[0] in chunk["text"].lower():
                results.append(chunk)
    
    return [c["text"] for c in results[:limit]]


# Загружаем сразу при импорте
knowledge_base = load_documents()
