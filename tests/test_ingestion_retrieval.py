from sovereign.ingestion import ingest_bytes, split_chunks
from sovereign.retrieval import search

def test_chunk_overlap_and_empty():
    assert split_chunks("") == []
    chunks = split_chunks("A " * 1000, size=100, overlap=20)
    assert len(chunks) > 1

def test_ingest_and_search():
    doc, count = ingest_bytes("pump_sop.txt", b"Pump P-101 vibration must be reviewed every month.")
    assert count >= 1
    results = search("P-101 vibration review")
    assert results
    assert results[0]["filename"] == "pump_sop.txt"
