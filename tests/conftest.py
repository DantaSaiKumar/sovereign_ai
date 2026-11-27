import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

@pytest.fixture(autouse=True)
def isolated_data(tmp_path, monkeypatch):
    import sovereign.config as config
    import sovereign.db as db
    import sovereign.ingestion as ingestion
    import sovereign.reports as reports
    data = tmp_path / "data"
    monkeypatch.setattr(config, "DATA_DIR", data)
    monkeypatch.setattr(config, "UPLOAD_DIR", data / "uploads")
    monkeypatch.setattr(config, "REPORT_DIR", data / "reports")
    monkeypatch.setattr(config, "DB_PATH", data / "test.db")
    monkeypatch.setattr(db, "DB_PATH", data / "test.db")
    monkeypatch.setattr(ingestion, "UPLOAD_DIR", data / "uploads")
    monkeypatch.setattr(reports, "REPORT_DIR", data / "reports")
    config.ensure_dirs()
    db.init_db()
    yield
