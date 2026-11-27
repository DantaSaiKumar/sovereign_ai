import sqlite3
from contextlib import contextmanager
from .config import DB_PATH, ensure_dirs

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS documents (
  id TEXT PRIMARY KEY, filename TEXT NOT NULL, stored_path TEXT NOT NULL,
  file_type TEXT NOT NULL, sha256 TEXT NOT NULL, status TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS chunks (
  id INTEGER PRIMARY KEY AUTOINCREMENT, document_id TEXT NOT NULL,
  filename TEXT NOT NULL, page INTEGER, text TEXT NOT NULL,
  FOREIGN KEY(document_id) REFERENCES documents(id)
);
CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(document_id);
CREATE TABLE IF NOT EXISTS tasks (
  id TEXT PRIMARY KEY, question TEXT NOT NULL, status TEXT NOT NULL,
  answer TEXT, verification TEXT, sources_json TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS approvals (
  id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT NOT NULL,
  decision TEXT NOT NULL, reviewer TEXT NOT NULL, note TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL,
  event TEXT NOT NULL, payload_json TEXT NOT NULL,
  previous_hash TEXT NOT NULL, event_hash TEXT NOT NULL
);
"""

@contextmanager
def connect():
    ensure_dirs()
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    with connect() as conn:
        conn.executescript(SCHEMA)

def add_document(doc):
    with connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO documents(id,filename,stored_path,file_type,sha256,status,created_at) VALUES(?,?,?,?,?,?,?)",
            (doc["id"], doc["filename"], doc["stored_path"], doc["file_type"],
             doc["sha256"], doc.get("status", "indexed"), doc["created_at"])
        )

def add_chunks(document_id, filename, chunks):
    with connect() as conn:
        conn.execute("DELETE FROM chunks WHERE document_id=?", (document_id,))
        conn.executemany(
            "INSERT INTO chunks(document_id,filename,page,text) VALUES(?,?,?,?)",
            [(document_id, filename, c.get("page"), c["text"]) for c in chunks]
        )

def get_chunks(document_ids=None):
    with connect() as conn:
        if document_ids:
            marks = ",".join("?" for _ in document_ids)
            rows = conn.execute(
                f"SELECT document_id,filename,page,text FROM chunks WHERE document_id IN ({marks})",
                tuple(document_ids)
            ).fetchall()
        else:
            rows = conn.execute("SELECT document_id,filename,page,text FROM chunks").fetchall()
        return [dict(r) for r in rows]

def list_documents():
    with connect() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT id,filename,file_type,status,created_at,sha256 FROM documents ORDER BY created_at DESC"
        ).fetchall()]

def save_task(task):
    with connect() as conn:
        conn.execute(
            "INSERT INTO tasks(id,question,status,answer,verification,sources_json,created_at) VALUES(?,?,?,?,?,?,?)",
            (task["id"], task["question"], task["status"], task.get("answer"),
             task.get("verification"), task.get("sources_json"), task["created_at"])
        )

def update_task(task_id, status, answer=None, verification=None, sources_json=None):
    with connect() as conn:
        conn.execute(
            "UPDATE tasks SET status=?,answer=?,verification=?,sources_json=? WHERE id=?",
            (status, answer, verification, sources_json, task_id)
        )

def get_task(task_id):
    with connect() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        return dict(row) if row else None

def list_tasks(limit=30):
    with connect() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()]

def save_approval(task_id, decision, reviewer, note, created_at):
    with connect() as conn:
        conn.execute(
            "INSERT INTO approvals(task_id,decision,reviewer,note,created_at) VALUES(?,?,?,?,?)",
            (task_id, decision, reviewer, note, created_at)
        )

def list_approvals(task_id):
    with connect() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM approvals WHERE task_id=? ORDER BY id DESC", (task_id,)
        ).fetchall()]
