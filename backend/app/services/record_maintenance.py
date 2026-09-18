"""记录维护：启动时与定时任务中执行，避免 GET 详情接口产生写库副作用。"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.models.entities import AnalysisRecord

logger = logging.getLogger(__name__)


def repair_legacy_records_batch(db: Session, limit: int = 100) -> int:
    from app.services.platform_service import _repair_legacy_detected_target

    rows = (
        db.query(AnalysisRecord)
        .filter(AnalysisRecord.status == "success")
        .order_by(AnalysisRecord.id.asc())
        .limit(limit)
        .all()
    )
    repaired = 0
    for record in rows:
        before = record.sections_json
        _repair_legacy_detected_target(record, db)
        db.refresh(record)
        if record.sections_json != before:
            repaired += 1
    if repaired:
        logger.info("record_maintenance repaired %s legacy target records", repaired)
    return repaired


def recover_stale_records_batch(db: Session, limit: int = 50) -> int:
    from app.services.platform_service import recover_stale_ai_enhancement

    rows = (
        db.query(AnalysisRecord)
        .filter(AnalysisRecord.status == "success")
        .order_by(AnalysisRecord.id.desc())
        .limit(limit)
        .all()
    )
    recovered = 0
    for record in rows:
        before = record.sections_json
        recover_stale_ai_enhancement(record, db)
        db.refresh(record)
        if record.sections_json != before:
            recovered += 1
    if recovered:
        logger.info("record_maintenance recovered %s stale AI enhancement records", recovered)
    return recovered


def run_startup_maintenance(db: Session) -> dict[str, int]:
    return {
        "legacy_repaired": repair_legacy_records_batch(db, limit=200),
        "stale_recovered": recover_stale_records_batch(db, limit=100),
    }
