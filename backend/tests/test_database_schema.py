from sqlalchemy import inspect, text

from app.core.database import Base, engine, init_db
from app.models.entities import User


def test_init_db_sqlite_runtime_schema_is_idempotent():
    Base.metadata.drop_all(bind=engine)
    try:
        init_db()
        init_db()

        inspector = inspect(engine)
        assert "user_profiles" in inspector.get_table_names()
        assert "job_profiles" in inspector.get_table_names()
        assert "job_profile_id" in {column["name"] for column in inspector.get_columns("analysis_records")}
    finally:
        Base.metadata.drop_all(bind=engine)


def test_sqlite_legacy_analysis_records_adds_columns_and_indexes():
    Base.metadata.drop_all(bind=engine)
    try:
        User.__table__.create(bind=engine)
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE analysis_records (
                      id INTEGER PRIMARY KEY,
                      user_id INTEGER NOT NULL,
                      batch_task_id INTEGER NULL,
                      original_filename VARCHAR(255) NOT NULL,
                      target_position VARCHAR(255) DEFAULT '',
                      job_description TEXT DEFAULT '',
                      total_score FLOAT DEFAULT 0,
                      scores_json TEXT DEFAULT '{}',
                      sections_json TEXT DEFAULT '{}',
                      diagnosis_json TEXT DEFAULT '[]',
                      suggestions_json TEXT DEFAULT '[]',
                      match_result_json TEXT DEFAULT '{}',
                      analysis_mode VARCHAR(50) DEFAULT 'offline',
                      status VARCHAR(50) DEFAULT 'success',
                      error_message TEXT DEFAULT '',
                      created_at DATETIME
                    )
                    """
                )
            )

        init_db()

        inspector = inspect(engine)
        columns = {column["name"] for column in inspector.get_columns("analysis_records")}
        indexes = {index["name"] for index in inspector.get_indexes("analysis_records")}

        assert {"job_profile_id", "guest_session_id", "root_record_id", "parent_record_id", "version_no"} <= columns
        assert {"idx_record_job_profile", "idx_record_guest_session", "idx_record_root", "idx_record_parent"} <= indexes
    finally:
        Base.metadata.drop_all(bind=engine)
