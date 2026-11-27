import csv, io, uuid
from datetime import datetime, timezone
from pathlib import Path
from .config import UPLOAD_DIR, MAX_TEXT_CHARS, CHUNK_SIZE, CHUNK_OVERLAP
from .security import safe_filename, validate_upload, sha256_bytes
from .db import add_document, add_chunks
from .audit import append_event

def split_chunks(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    text = (text or "").strip()
    if not text:
        return []
    chunks, start = [], 0
    while start < len(text):
        end = min(len(text), start + size)
        piece = text[start:end].strip()
        if piece:
            chunks.append({"page": None, "text": piece})
        if end >= len(text):
            break
        start = max(start + 1, end - overlap)
    return chunks

def extract_file(filename, data):
    ext = Path(filename).suffix.lower()
    if ext == ".txt" or ext == ".md":
        return [{"page": None, "text": data.decode("utf-8", errors="replace")}]
    if ext == ".pdf":
        try:
            import fitz
        except ImportError as exc:
            raise RuntimeError("PDF support requires PyMuPDF. Install requirements.txt.") from exc
        pages = []
        with fitz.open(stream=data, filetype="pdf") as pdf:
            for index, page in enumerate(pdf):
                text = page.get_text("text").strip()
                if text:
                    pages.append({"page": index + 1, "text": text})
        if not pages:
            raise ValueError("No embedded text found. This may be a scanned PDF; run OCR on page images.")
        return pages
    if ext == ".docx":
        from docx import Document
        doc = Document(io.BytesIO(data))
        text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        for table in doc.tables:
            text += "\n" + "\n".join(" | ".join(c.text for c in row.cells) for row in table.rows)
        return [{"page": None, "text": text}]
    if ext == ".csv":
        decoded = data.decode("utf-8-sig", errors="replace")
        rows = list(csv.reader(io.StringIO(decoded)))
        text = "\n".join(" | ".join(row) for row in rows[:10000])
        return [{"page": None, "text": text}]
    if ext == ".xlsx":
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        blocks = []
        for ws in wb.worksheets:
            blocks.append(f"Sheet: {ws.title}")
            for row in ws.iter_rows(values_only=True):
                vals = ["" if v is None else str(v) for v in row]
                if any(vals):
                    blocks.append(" | ".join(vals))
        return [{"page": None, "text": "\n".join(blocks)}]
    if ext in {".png", ".jpg", ".jpeg", ".webp"}:
        # OCR is optional; image reasoning is handled by the local vision model when available.
        try:
            from PIL import Image
            import pytesseract
            image = Image.open(io.BytesIO(data))
            text = pytesseract.image_to_string(image)
        except Exception:
            text = ""
        return [{"page": None, "text": text or "[Image uploaded. Use local vision analysis to inspect visual content.]"}]
    raise ValueError("Unsupported file type.")

def ingest_bytes(filename, data):
    ext = validate_upload(filename, len(data))
    original_name = safe_filename(filename)
    extracted = extract_file(original_name, data)
    total = sum(len(p["text"]) for p in extracted)
    if total > MAX_TEXT_CHARS:
        raise ValueError("Extracted text exceeds the per-document processing limit.")
    doc_id = uuid.uuid4().hex
    stored_name = f"{doc_id}_{original_name}"
    stored_path = UPLOAD_DIR / stored_name
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    stored_path.write_bytes(data)
    all_chunks = []
    for page in extracted:
        for chunk in split_chunks(page["text"]):
            chunk["page"] = page.get("page")
            all_chunks.append(chunk)
    created = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": doc_id, "filename": original_name, "stored_path": str(stored_path),
        "file_type": ext, "sha256": sha256_bytes(data), "status": "indexed",
        "created_at": created
    }
    add_document(doc)
    add_chunks(doc_id, original_name, all_chunks)
    append_event("document_ingested", {"document_id": doc_id, "filename": original_name,
                                       "sha256": doc["sha256"], "chunks": len(all_chunks)})
    return doc, len(all_chunks)
