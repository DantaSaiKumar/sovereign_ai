import hashlib, json
from datetime import datetime, timezone
from .db import connect

GENESIS = "0" * 64

def append_event(event: str, payload: dict):
    created_at = datetime.now(timezone.utc).isoformat()
    payload_json = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    with connect() as conn:
        row = conn.execute("SELECT event_hash FROM audit ORDER BY id DESC LIMIT 1").fetchone()
        previous_hash = row["event_hash"] if row else GENESIS
        material = f"{created_at}|{event}|{payload_json}|{previous_hash}"
        event_hash = hashlib.sha256(material.encode("utf-8")).hexdigest()
        conn.execute(
            "INSERT INTO audit(created_at,event,payload_json,previous_hash,event_hash) VALUES(?,?,?,?,?)",
            (created_at, event, payload_json, previous_hash, event_hash)
        )
    return event_hash

def verify_chain():
    with connect() as conn:
        rows = conn.execute("SELECT * FROM audit ORDER BY id").fetchall()
    previous = GENESIS
    for row in rows:
        material = f'{row["created_at"]}|{row["event"]}|{row["payload_json"]}|{previous}'
        expected = hashlib.sha256(material.encode("utf-8")).hexdigest()
        if row["previous_hash"] != previous or row["event_hash"] != expected:
            return False, row["id"]
        previous = row["event_hash"]
    return True, len(rows)

def recent_events(limit=50):
    with connect() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM audit ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()]
