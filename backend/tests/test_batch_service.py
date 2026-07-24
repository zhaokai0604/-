from datetime import datetime
from types import SimpleNamespace

from app.models.entities import BatchTask
from app.services.batch_service import _finalize_batch_status, batch_to_response
from app.utils.json_tools import dumps


class _FakeQuery:
    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return None


class _FakeSession:
    def query(self, model):
        return _FakeQuery()


def test_finalize_batch_status():
    assert _finalize_batch_status(2, 1) == "partial_success"
    assert _finalize_batch_status(0, 2) == "failed"
    assert _finalize_batch_status(3, 0) == "success"


def test_batch_to_response_includes_skipped_count():
    batch = BatchTask(
        user_id=1,
        zip_filename="demo.zip",
        total_files=2,
        success_count=1,
        failed_count=0,
        skipped_count=1,
        summary_json=dumps(
            [
                {"filename": "a.docx", "status": "success", "record_id": 1, "total_score": 80},
                {"filename": "notes.txt", "status": "skipped", "error": "unsupported"},
            ]
        ),
        status="success",
        enable_ai=False,
        created_at=datetime.utcnow(),
    )
    batch.id = 99

    payload = batch_to_response(batch, include_results=True, db=_FakeSession())
    assert payload["skipped_count"] == 1
    assert payload["processed_files"] == 2
    assert payload["enable_ai"] is False
    assert len(payload["results"]) == 2
