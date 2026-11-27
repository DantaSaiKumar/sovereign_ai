import re, math
from collections import Counter
from .db import get_chunks

TOKEN_RE = re.compile(r"[a-zA-Z0-9_./-]+")

def _tokens(text):
    return [t.lower() for t in TOKEN_RE.findall(text or "") if len(t) > 1]

def search(query, document_ids=None, top_k=5):
    rows = get_chunks(document_ids)
    if not rows:
        return []
    q = _tokens(query)
    if not q:
        return []
    # Lightweight BM25-like lexical retrieval; no embedding model or vector server required.
    docs = [_tokens(r["text"]) for r in rows]
    avgdl = sum(map(len, docs)) / max(1, len(docs))
    df = Counter(token for doc in docs for token in set(doc))
    n = len(docs)
    scored = []
    for row, terms in zip(rows, docs):
        tf = Counter(terms)
        score = 0.0
        for term in q:
            if not tf[term]:
                continue
            idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
            denom = tf[term] + 1.5 * (1 - 0.75 + 0.75 * len(terms) / max(avgdl, 1))
            score += idf * tf[term] * 2.5 / denom
        if score > 0:
            scored.append((score, row))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        {"document_id": r["document_id"], "filename": r["filename"], "page": r["page"],
         "text": r["text"], "score": round(score, 4)}
        for score, r in scored[:top_k]
    ]
