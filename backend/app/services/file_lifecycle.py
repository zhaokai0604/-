"""文件生命周期：清理无数据库引用的孤儿文件。"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.entities import Report, UploadedFile
from app.services.storage import remove_path


def collect_referenced_paths(db: Session) -> set[str]:
    paths: set[str] = set()
    for row in db.query(UploadedFile.stored_path).all():
        if row[0]:
            paths.add(str(Path(row[0]).resolve()))
    for row in db.query(Report.stored_path).all():
        if row[0]:
            paths.add(str(Path(row[0]).resolve()))
    return paths


def cleanup_orphan_files(db: Session, dry_run: bool = False) -> dict[str, int]:
    referenced = collect_referenced_paths(db)
    scanned = 0
    removed = 0
    for directory in (settings.uploads_dir, settings.extracted_dir, settings.reports_dir):
        if not directory.exists():
            continue
        for path in directory.rglob("*"):
            if not path.is_file():
                continue
            scanned += 1
            resolved = str(path.resolve())
            if resolved in referenced:
                continue
            if not dry_run:
                remove_path(path)
            removed += 1
    return {"scanned": scanned, "removed": removed, "dry_run": dry_run}
