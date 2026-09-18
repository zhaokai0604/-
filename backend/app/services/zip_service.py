import shutil
import uuid
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from fastapi import HTTPException

from app.core.config import settings
from app.services.storage import ALLOWED_SINGLE_EXTENSIONS

UTF8_FILENAME_FLAG = 0x800
WINDOWS_ZIP_ENCODINGS = ("gb18030", "gbk")


@dataclass
class ZipExtractResult:
    files: list[Path] = field(default_factory=list)
    skipped: list[dict[str, str]] = field(default_factory=list)


def safe_extract_zip(zip_path: Path) -> ZipExtractResult:
    target_dir = settings.extracted_dir / uuid.uuid4().hex
    target_dir.mkdir(parents=True, exist_ok=True)
    extracted: list[Path] = []
    skipped: list[dict[str, str]] = []
    total_size = 0
    max_total = settings.max_zip_total_size_mb * 1024 * 1024
    try:
        with zipfile.ZipFile(zip_path) as archive:
            for member in archive.infolist():
                if member.is_dir():
                    continue
                member_name = decode_zip_member_name(member).replace("\\", "/")
                if member_name.startswith("/") or ".." in Path(member_name).parts:
                    raise HTTPException(status_code=400, detail="ZIP 包含非法路径。")
                total_size += member.file_size
                if total_size > max_total:
                    raise HTTPException(status_code=400, detail=f"ZIP 解压后超过 {settings.max_zip_total_size_mb}MB 限制。")
                suffix = Path(member_name).suffix.lower()
                if suffix not in ALLOWED_SINGLE_EXTENSIONS:
                    skipped.append(
                        {
                            "filename": Path(member_name).name or member_name,
                            "reason": f"不支持的文件类型{suffix or '（无后缀）'}，仅支持 .docx / .pdf",
                        }
                    )
                    continue
                destination = _unique_destination(target_dir, Path(member_name).name)
                with archive.open(member) as source, destination.open("wb") as output:
                    shutil.copyfileobj(source, output)
                extracted.append(destination)
    except zipfile.BadZipFile as exc:
        raise HTTPException(status_code=400, detail="ZIP 文件损坏或格式不正确。") from exc
    if not extracted:
        detail = "ZIP 中未找到支持的 .docx 或 .pdf 简历。"
        if skipped:
            detail = f"{detail}（已跳过 {len(skipped)} 个不支持的文件）"
        raise HTTPException(status_code=400, detail=detail)
    return ZipExtractResult(files=extracted, skipped=skipped)


def decode_zip_member_name(member: zipfile.ZipInfo) -> str:
    """Recover Chinese filenames from Windows-created ZIP files.

    ZIP entries without the UTF-8 flag are decoded by Python as CP437. Many
    Windows ZIP tools actually stored those names as GBK/GB18030 bytes, so we
    re-encode the mojibake back to CP437 bytes and decode with Chinese codecs.
    """
    filename = member.filename
    try:
        raw_name = filename.encode("cp437")
    except UnicodeEncodeError:
        return filename
    for encoding in WINDOWS_ZIP_ENCODINGS:
        try:
            decoded = raw_name.decode(encoding)
        except UnicodeDecodeError:
            continue
        if decoded and (not member.flag_bits & UTF8_FILENAME_FLAG or _looks_like_cp437_mojibake(filename)):
            return decoded
    return filename


def _looks_like_cp437_mojibake(filename: str) -> bool:
    return any(
        "\u2500" <= char <= "\u257f"
        or "\u0370" <= char <= "\u03ff"
        or char in {"╬", "╧", "╨", "╩", "╠", "╡", "╢", "╣", "║", "╗", "╝", "╜", "╛", "┐", "└", "┘", "┼"}
        for char in filename
    )


def _unique_destination(target_dir: Path, filename: str) -> Path:
    safe_name = filename.strip() or f"resume_{uuid.uuid4().hex}.docx"
    destination = target_dir / safe_name
    if not destination.exists():
        return destination
    stem = destination.stem
    suffix = destination.suffix
    for index in range(1, 1000):
        candidate = target_dir / f"{stem}_{index}{suffix}"
        if not candidate.exists():
            return candidate
    return target_dir / f"{stem}_{uuid.uuid4().hex}{suffix}"
