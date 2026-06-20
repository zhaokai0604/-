from typing import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


LEGACY_DEFAULT_USER_NAME = "default_user"
GUEST_DISPLAY_NAME = "游客"


class Base(DeclarativeBase):
    pass


def _build_engine():
    url = settings.database_url
    kwargs: dict = {"pool_pre_ping": True}
    if not url.startswith("sqlite"):
        kwargs.update(
            pool_size=20,
            max_overflow=30,
            pool_timeout=60,
            pool_recycle=1800,
        )
    return create_engine(url, **kwargs)


engine = _build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app.models.entities import User
    from app.services.auth import hash_password, normalize_username, validate_password_strength, verify_password

    Base.metadata.create_all(bind=engine)
    _ensure_runtime_schema()
    with SessionLocal() as db:
        ensure_guest_user(db, User)
        admin_username = normalize_username(settings.admin_username)
        if settings.admin_password and admin_username != settings.default_user_name:
            existing_admin = db.query(User).filter(User.username == admin_username).first()
            if existing_admin:
                changed = False
                if existing_admin.role != "admin":
                    existing_admin.role = "admin"
                    changed = True
                if existing_admin.status != "active":
                    existing_admin.status = "active"
                    changed = True
                if settings.admin_display_name and existing_admin.display_name != settings.admin_display_name:
                    existing_admin.display_name = settings.admin_display_name
                    changed = True
                if not verify_password(settings.admin_password, existing_admin.password_hash):
                    validate_password_strength(settings.admin_password)
                    existing_admin.password_hash = hash_password(settings.admin_password)
                    changed = True
                if changed:
                    db.commit()
            else:
                validate_password_strength(settings.admin_password)
                admin = User(
                    username=admin_username,
                    password_hash=hash_password(settings.admin_password),
                    display_name=settings.admin_display_name or admin_username,
                    role="admin",
                    status="active",
                )
                db.add(admin)
                db.commit()


def _ensure_runtime_schema() -> None:
    inspector = inspect(engine)
    if "users" in inspector.get_table_names():
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        statements = []
        if "role" not in user_columns:
            statements.append("ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'user'")
        if "status" not in user_columns:
            statements.append("ALTER TABLE users ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'active'")
        if "last_login_at" not in user_columns:
            statements.append("ALTER TABLE users ADD COLUMN last_login_at DATETIME NULL")
        if statements:
            with engine.begin() as conn:
                for statement in statements:
                    conn.execute(text(statement))

    table_names = set(inspector.get_table_names())
    statements: list[str] = []
    if "job_profiles" not in table_names:
        statements.append(
            """
            CREATE TABLE job_profiles (
              id INT AUTO_INCREMENT PRIMARY KEY,
              user_id INT NOT NULL,
              name VARCHAR(120) NOT NULL,
              category VARCHAR(100) NOT NULL DEFAULT '',
              target_position VARCHAR(120) NOT NULL DEFAULT '',
              description LONGTEXT,
              requirement_summary LONGTEXT,
              status VARCHAR(20) NOT NULL DEFAULT 'active',
              created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
              INDEX idx_job_profile_user (user_id),
              INDEX idx_job_profile_status (status),
              CONSTRAINT fk_job_profile_user FOREIGN KEY (user_id) REFERENCES users(id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )

    if "analysis_records" in table_names:
        record_columns = {column["name"] for column in inspector.get_columns("analysis_records")}
        if "job_profile_id" not in record_columns:
            statements.append("ALTER TABLE analysis_records ADD COLUMN job_profile_id INT NULL")
            statements.append("ALTER TABLE analysis_records ADD INDEX idx_record_job_profile (job_profile_id)")
            statements.append("ALTER TABLE analysis_records ADD CONSTRAINT fk_record_job_profile FOREIGN KEY (job_profile_id) REFERENCES job_profiles(id)")
        if "guest_session_id" not in record_columns:
            statements.append("ALTER TABLE analysis_records ADD COLUMN guest_session_id VARCHAR(64) NULL")
            statements.append("ALTER TABLE analysis_records ADD INDEX idx_record_guest_session (guest_session_id)")
        if "root_record_id" not in record_columns:
            statements.append("ALTER TABLE analysis_records ADD COLUMN root_record_id INT NULL")
            statements.append("ALTER TABLE analysis_records ADD INDEX idx_record_root (root_record_id)")
        if "parent_record_id" not in record_columns:
            statements.append("ALTER TABLE analysis_records ADD COLUMN parent_record_id INT NULL")
            statements.append("ALTER TABLE analysis_records ADD INDEX idx_record_parent (parent_record_id)")
        if "version_no" not in record_columns:
            statements.append("ALTER TABLE analysis_records ADD COLUMN version_no INT NOT NULL DEFAULT 1")

    if "batch_tasks" in table_names:
        batch_columns = {column["name"] for column in inspector.get_columns("batch_tasks")}
        if "job_profile_id" not in batch_columns:
            statements.append("ALTER TABLE batch_tasks ADD COLUMN job_profile_id INT NULL")
            statements.append("ALTER TABLE batch_tasks ADD INDEX idx_batch_job_profile (job_profile_id)")
            statements.append("ALTER TABLE batch_tasks ADD CONSTRAINT fk_batch_job_profile FOREIGN KEY (job_profile_id) REFERENCES job_profiles(id)")
        if "guest_session_id" not in batch_columns:
            statements.append("ALTER TABLE batch_tasks ADD COLUMN guest_session_id VARCHAR(64) NULL")
            statements.append("ALTER TABLE batch_tasks ADD INDEX idx_batch_guest_session (guest_session_id)")

    if "uploaded_files" in table_names:
        upload_columns = {column["name"] for column in inspector.get_columns("uploaded_files")}
        if "guest_session_id" not in upload_columns:
            statements.append("ALTER TABLE uploaded_files ADD COLUMN guest_session_id VARCHAR(64) NULL")
            statements.append("ALTER TABLE uploaded_files ADD INDEX idx_upload_guest_session (guest_session_id)")

    if "reports" in table_names:
        report_columns = {column["name"] for column in inspector.get_columns("reports")}
        if "guest_session_id" not in report_columns:
            statements.append("ALTER TABLE reports ADD COLUMN guest_session_id VARCHAR(64) NULL")
            statements.append("ALTER TABLE reports ADD INDEX idx_report_guest_session (guest_session_id)")

    if "job_profiles" in table_names:
        job_columns = {column["name"] for column in inspector.get_columns("job_profiles")}
        if "guest_session_id" not in job_columns:
            statements.append("ALTER TABLE job_profiles ADD COLUMN guest_session_id VARCHAR(64) NULL")
            statements.append("ALTER TABLE job_profiles ADD INDEX idx_job_profile_guest_session (guest_session_id)")

    if "user_profiles" not in table_names:
        statements.append(
            """
            CREATE TABLE user_profiles (
              id INT AUTO_INCREMENT PRIMARY KEY,
              user_id INT NOT NULL UNIQUE,
              school VARCHAR(120) NOT NULL DEFAULT '',
              major VARCHAR(120) NOT NULL DEFAULT '',
              grade VARCHAR(50) NOT NULL DEFAULT '',
              phone VARCHAR(30) NOT NULL DEFAULT '',
              bio LONGTEXT,
              updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
              INDEX idx_user_profile_user (user_id),
              CONSTRAINT fk_user_profile_user FOREIGN KEY (user_id) REFERENCES users(id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )

    if statements:
        with engine.begin() as conn:
            for statement in statements:
                conn.execute(text(statement))


def ensure_guest_user(db: Session, user_model=None):
    from app.models.entities import User

    model = user_model or User
    guest_user = db.query(model).filter(model.username == settings.default_user_name).first()
    legacy_user = db.query(model).filter(model.username == LEGACY_DEFAULT_USER_NAME).first()

    if guest_user:
        changed = False
        if guest_user.display_name != GUEST_DISPLAY_NAME:
            guest_user.display_name = GUEST_DISPLAY_NAME
            changed = True
        if getattr(guest_user, "role", "user") != "user":
            guest_user.role = "user"
            changed = True
        if getattr(guest_user, "status", "active") != "active":
            guest_user.status = "active"
            changed = True
        if changed:
            db.commit()
        return guest_user

    if legacy_user:
        legacy_user.username = settings.default_user_name
        legacy_user.display_name = GUEST_DISPLAY_NAME
        legacy_user.role = "user"
        legacy_user.status = "active"
        db.commit()
        db.refresh(legacy_user)
        return legacy_user

    guest_user = model(username=settings.default_user_name, password_hash="", display_name=GUEST_DISPLAY_NAME, role="user", status="active")
    db.add(guest_user)
    db.commit()
    db.refresh(guest_user)
    return guest_user
