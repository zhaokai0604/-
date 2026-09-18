
import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.services.storage import resolve_allowed_data_path, safe_download_filename


def test_resolve_allowed_data_path_accepts_uploaded_file(tmp_path, monkeypatch):
    (tmp_path / "data" / "uploads").mkdir(parents=True)
    sample = tmp_path / "data" / "uploads" / "sample.docx"
    sample.write_bytes(b"demo")
    monkeypatch.setattr(settings, "project_root", tmp_path)

    resolved = resolve_allowed_data_path(sample)
    assert resolved == sample.resolve()


def test_resolve_allowed_data_path_rejects_outside_roots(tmp_path, monkeypatch):
    (tmp_path / "data" / "uploads").mkdir(parents=True)
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    monkeypatch.setattr(settings, "project_root", tmp_path)

    with pytest.raises(HTTPException) as exc:
        resolve_allowed_data_path(outside)
    assert exc.value.status_code == 404


def test_safe_download_filename_strips_path_and_quotes():
    assert safe_download_filename('../../evil".docx', "fallback.docx") == "evil.docx"
