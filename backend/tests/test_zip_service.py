import zipfile

import pytest
from fastapi import HTTPException

from app.services.zip_service import safe_extract_zip


def test_safe_extract_zip_reports_skipped_files(tmp_path, monkeypatch):
    class _TestSettings:
        extracted_dir = tmp_path / "extracted"
        max_zip_total_size_mb = 50

    monkeypatch.setattr("app.services.zip_service.settings", _TestSettings())

    zip_path = tmp_path / "batch.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("resume.docx", b"fake docx")
        archive.writestr("notes.txt", b"ignore me")
        archive.writestr("photo.jpg", b"ignore me too")

    result = safe_extract_zip(zip_path)
    assert len(result.files) == 1
    assert result.files[0].name == "resume.docx"
    assert len(result.skipped) == 2
    assert all(item["reason"] for item in result.skipped)


def test_safe_extract_zip_raises_when_only_unsupported_files(tmp_path, monkeypatch):
    class _TestSettings:
        extracted_dir = tmp_path / "extracted"
        max_zip_total_size_mb = 50

    monkeypatch.setattr("app.services.zip_service.settings", _TestSettings())

    zip_path = tmp_path / "empty.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("readme.txt", b"no resume")

    with pytest.raises(HTTPException) as exc:
        safe_extract_zip(zip_path)
    assert exc.value.status_code == 400
    assert "未找到" in exc.value.detail
