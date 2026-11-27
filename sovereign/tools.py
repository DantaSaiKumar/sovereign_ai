import csv, io, statistics
from .security import safe_calculate

def calculate(expression):
    return {"expression": expression, "result": safe_calculate(expression)}

def summarize_csv_bytes(data: bytes):
    rows = list(csv.DictReader(io.StringIO(data.decode("utf-8-sig", errors="replace"))))
    if not rows:
        return {"rows": 0, "columns": [], "numeric_summary": {}}
    result = {}
    for key in rows[0].keys():
        vals = []
        for row in rows:
            try:
                vals.append(float(row.get(key, "")))
            except (TypeError, ValueError):
                pass
        if vals:
            result[key] = {
                "count": len(vals), "min": min(vals), "max": max(vals),
                "mean": round(statistics.mean(vals), 4)
            }
    return {"rows": len(rows), "columns": list(rows[0].keys()), "numeric_summary": result}
