import shutil
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.core.config import settings

ALLOWED_SINGLE_EXTENSIONS = {".docx", ".pdf"}
ALLOWED_ZIP_EXTENSIONS = {".zip"}


def safe_suffix(filename: str) -> str:
    return Path(filename).suffix.lower()


def validate_upload(filename: str, size: int, allow_zip: bool = False) -> None:
    suffix = safe_suffix(filename)
    allowed = ALLOWED_SINGLE_EXTENSIONS | (ALLOWED_ZIP_EXTENSIONS if allow_zip else set())
    if suffix == ".doc":
        raise HTTPException(status_code=400, detail="暂不支持 .doc 老格式，请转换为 .docx 后上传。")
    if suffix not in allowed:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型：{suffix}")
    max_mb = settings.max_zip_total_size_mb if allow_zip and suffix == ".zip" else settings.max_upload_size_mb
    max_bytes = max_mb * 1024 * 1024
    if size > max_bytes:
        raise HTTPException(status_code=400, detail=f"文件超过 {max_mb}MB 限制。")


def save_upload_bytes(content: bytes, filename: str, directory: Path | None = None) -> Path:
    suffix = safe_suffix(filename)
    validate_upload(filename, len(content), allow_zip=suffix == ".zip")
    if directory is None:
        from app.services.blob_store import get_blob_store

        category = "uploads"
        stored_ref = get_blob_store().put_bytes(content, filename, category=category)
        return Path(stored_ref)
    directory.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}{suffix}"
    stored_path = directory / stored_name
    stored_path.write_bytes(content)
    return stored_path


async def save_upload(file: UploadFile, directory: Path | None = None) -> Path:
    content = await file.read()
    return save_upload_bytes(content, file.filename or "", directory)


def remove_path(path_value: str | Path | None) -> None:
    if not path_value:
        return
    path = Path(path_value)
    try:
        resolved = path.resolve()
        allowed_roots = _allowed_data_roots()
        if not _path_under_allowed_roots(resolved, allowed_roots):
            return
        if resolved.is_dir():
            shutil.rmtree(resolved, ignore_errors=True)
        elif resolved.exists():
            resolved.unlink()
    except OSError:
        return


def _allowed_data_roots() -> list[Path]:
    return [
        settings.uploads_dir.resolve(),
        settings.extracted_dir.resolve(),
        settings.reports_dir.resolve(),
    ]


def _path_under_allowed_roots(resolved: Path, allowed_roots: list[Path] | None = None) -> bool:
    roots = allowed_roots or _allowed_data_roots()
    return any(resolved == root or resolved.is_relative_to(root) for root in roots)


def resolve_allowed_data_path(path_value: str | Path) -> Path:
    """Resolve a stored file path and ensure it stays under data/ roots."""
    path = Path(path_value)
    try:
        resolved = path.resolve()
    except OSError as exc:
        raise HTTPException(status_code=404, detail="文件不存在。") from exc
    if not _path_under_allowed_roots(resolved):
        raise HTTPException(status_code=404, detail="文件不存在。")
    if not resolved.is_file():
        raise HTTPException(status_code=404, detail="文件不存在。")
    return resolved


def safe_download_filename(name: str, fallback: str = "download") -> str:
    cleaned = Path(str(name or "")).name.strip() or fallback
    return cleaned.replace('"', "").replace("\r", "").replace("\n", "")[:200]
