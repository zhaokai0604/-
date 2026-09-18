from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings

LEGACY_DEFAULT_USER_NAME = "default_user"
GUEST_DISPLAY_NAME = "游客"


class Base(DeclarativeBase):
    pass


def _build_engine():
    url = settings.database_url
    kwargs: dict = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        if url.endswith(":memory:") or url.rstrip("/").endswith(":memory:"):
            kwargs.update(
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
    else:
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
    from app.core.config import get_settings
    from app.models.entities import User
    from app.services.auth import hash_password, normalize_username, validate_password_strength, verify_password

    cfg = get_settings()
    Base.metadata.create_all(bind=engine)
    _ensure_runtime_schema()
    with SessionLocal() as db:
        from app.services.organization import ensure_default_organization

        default_org = ensure_default_organization(db)
        ensure_guest_user(db, User, organization_id=default_org.id)
        admin_username = normalize_username(cfg.admin_username)
        if cfg.admin_password and admin_username != cfg.default_user_name:
            existing_admin = db.query(User).filter(User.username == admin_username).first()
            if existing_admin:
                changed = False
                if existing_admin.role != "admin":
                    existing_admin.role = "admin"
                    changed = True
                if existing_admin.status != "active":
                    existing_admin.status = "active"
                    changed = True
                if cfg.admin_display_name and existing_admin.display_name != cfg.admin_display_name:
                    existing_admin.display_name = cfg.admin_display_name
                    changed = True
                if not verify_password(cfg.admin_password, existing_admin.password_hash):
                    validate_password_strength(cfg.admin_password)
                    existing_admin.password_hash = hash_password(cfg.admin_password)
                    changed = True
                if changed:
                    db.commit()
            else:
                validate_password_strength(cfg.admin_password)
                admin = User(
                    username=admin_username,
                    password_hash=hash_password(cfg.admin_password),
                    display_name=cfg.admin_display_name or admin_username,
                    role="admin",
                    status="active",
                    organization_id=default_org.id,
                )
                db.add(admin)
                db.commit()
        from app.services.record_maintenance import run_startup_maintenance

        run_startup_maintenance(db)


def _ensure_runtime_schema() -> None:
    is_sqlite = engine.dialect.name == "sqlite"
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
    if "organizations" not in table_names:
        statements.extend(_create_organizations_statements(is_sqlite))

    org_tables = {
        "users": "idx_users_organization",
        "analysis_records": "idx_record_organization",
        "batch_tasks": "idx_batch_organization",
        "uploaded_files": "idx_upload_organization",
        "reports": "idx_report_organization",
        "job_profiles": "idx_job_profile_organization",
    }
    for table, index_name in org_tables.items():
        if table not in table_names:
            continue
        columns = {column["name"] for column in inspector.get_columns(table)}
        if "organization_id" not in columns:
            statements.append(_add_int_column_statement(table, "organization_id", nullable=False, default="1", is_sqlite=is_sqlite))
            statements.append(_add_index_statement(table, index_name, "organization_id", is_sqlite))

    if "job_profiles" not in table_names:
        statements.extend(_create_job_profiles_statements(is_sqlite))

    if "analysis_records" in table_names:
        record_columns = {column["name"] for column in inspector.get_columns("analysis_records")}
        if "job_profile_id" not in record_columns:
            statements.append(_add_int_column_statement("analysis_records", "job_profile_id", nullable=True, is_sqlite=is_sqlite))
            statements.append(_add_index_statement("analysis_records", "idx_record_job_profile", "job_profile_id", is_sqlite))
            if not is_sqlite:
                statements.append("ALTER TABLE analysis_records ADD CONSTRAINT fk_record_job_profile FOREIGN KEY (job_profile_id) REFERENCES job_profiles(id)")
        if "guest_session_id" not in record_columns:
            statements.append("ALTER TABLE analysis_records ADD COLUMN guest_session_id VARCHAR(64) NULL")
            statements.append(_add_index_statement("analysis_records", "idx_record_guest_session", "guest_session_id", is_sqlite))
        if "root_record_id" not in record_columns:
            statements.append(_add_int_column_statement("analysis_records", "root_record_id", nullable=True, is_sqlite=is_sqlite))
            statements.append(_add_index_statement("analysis_records", "idx_record_root", "root_record_id", is_sqlite))
        if "parent_record_id" not in record_columns:
            statements.append(_add_int_column_statement("analysis_records", "parent_record_id", nullable=True, is_sqlite=is_sqlite))
            statements.append(_add_index_statement("analysis_records", "idx_record_parent", "parent_record_id", is_sqlite))
        if "version_no" not in record_columns:
            statements.append(_add_int_column_statement("analysis_records", "version_no", nullable=False, default="1", is_sqlite=is_sqlite))

    if "batch_tasks" in table_names:
        batch_columns = {column["name"] for column in inspector.get_columns("batch_tasks")}
        if "job_profile_id" not in batch_columns:
            statements.append(_add_int_column_statement("batch_tasks", "job_profile_id", nullable=True, is_sqlite=is_sqlite))
            statements.append(_add_index_statement("batch_tasks", "idx_batch_job_profile", "job_profile_id", is_sqlite))
            if not is_sqlite:
                statements.append("ALTER TABLE batch_tasks ADD CONSTRAINT fk_batch_job_profile FOREIGN KEY (job_profile_id) REFERENCES job_profiles(id)")
        if "guest_session_id" not in batch_columns:
            statements.append("ALTER TABLE batch_tasks ADD COLUMN guest_session_id VARCHAR(64) NULL")
            statements.append(_add_index_statement("batch_tasks", "idx_batch_guest_session", "guest_session_id", is_sqlite))
        if "skipped_count" not in batch_columns:
            statements.append(_add_int_column_statement("batch_tasks", "skipped_count", nullable=False, default="0", is_sqlite=is_sqlite))
        if "enable_ai" not in batch_columns:
            statements.append(_add_bool_column_statement("batch_tasks", "enable_ai", default="1", is_sqlite=is_sqlite))

    if "uploaded_files" in table_names:
        upload_columns = {column["name"] for column in inspector.get_columns("uploaded_files")}
        if "guest_session_id" not in upload_columns:
            statements.append("ALTER TABLE uploaded_files ADD COLUMN guest_session_id VARCHAR(64) NULL")
            statements.append(_add_index_statement("uploaded_files", "idx_upload_guest_session", "guest_session_id", is_sqlite))

    if "reports" in table_names:
        report_columns = {column["name"] for column in inspector.get_columns("reports")}
        if "guest_session_id" not in report_columns:
            statements.append("ALTER TABLE reports ADD COLUMN guest_session_id VARCHAR(64) NULL")
            statements.append(_add_index_statement("reports", "idx_report_guest_session", "guest_session_id", is_sqlite))

    if "job_profiles" in table_names:
        job_columns = {column["name"] for column in inspector.get_columns("job_profiles")}
        if "guest_session_id" not in job_columns:
            statements.append("ALTER TABLE job_profiles ADD COLUMN guest_session_id VARCHAR(64) NULL")
            statements.append(_add_index_statement("job_profiles", "idx_job_profile_guest_session", "guest_session_id", is_sqlite))

    if "user_profiles" not in table_names:
        statements.extend(_create_user_profiles_statements(is_sqlite))

    if "user_profiles" in table_names:
        profile_columns = {column["name"] for column in inspector.get_columns("user_profiles")}
        if "class_name" not in profile_columns:
            statements.append("ALTER TABLE user_profiles ADD COLUMN class_name VARCHAR(120) NOT NULL DEFAULT ''")

    if statements:
        with engine.begin() as conn:
            for statement in statements:
                conn.execute(text(statement))


def _add_index_statement(table: str, index_name: str, column: str, is_sqlite: bool) -> str:
    if is_sqlite:
        return f"CREATE INDEX IF NOT EXISTS {index_name} ON {table} ({column})"
    return f"ALTER TABLE {table} ADD INDEX {index_name} ({column})"


def _add_int_column_statement(
    table: str,
    column: str,
    *,
    nullable: bool,
    is_sqlite: bool,
    default: str | None = None,
) -> str:
    column_type = "INTEGER" if is_sqlite else "INT"
    null_sql = "NULL" if nullable else "NOT NULL"
    default_sql = f" DEFAULT {default}" if default is not None else ""
    return f"ALTER TABLE {table} ADD COLUMN {column} {column_type} {null_sql}{default_sql}"


def _add_bool_column_statement(table: str, column: str, *, default: str, is_sqlite: bool) -> str:
    column_type = "BOOLEAN" if is_sqlite else "TINYINT(1)"
    return f"ALTER TABLE {table} ADD COLUMN {column} {column_type} NOT NULL DEFAULT {default}"


def _create_organizations_statements(is_sqlite: bool) -> list[str]:
    if is_sqlite:
        return [
            """
            CREATE TABLE organizations (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name VARCHAR(120) NOT NULL DEFAULT '',
              code VARCHAR(64) NOT NULL UNIQUE,
              status VARCHAR(20) NOT NULL DEFAULT 'active',
              created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_organization_code ON organizations (code)",
        ]
    return [
        """
        CREATE TABLE organizations (
          id INT AUTO_INCREMENT PRIMARY KEY,
          name VARCHAR(120) NOT NULL DEFAULT '',
          code VARCHAR(64) NOT NULL UNIQUE,
          status VARCHAR(20) NOT NULL DEFAULT 'active',
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          INDEX idx_organization_code (code)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    ]


def _create_job_profiles_statements(is_sqlite: bool) -> list[str]:
    if is_sqlite:
        return [
            """
            CREATE TABLE job_profiles (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL,
              guest_session_id VARCHAR(64) NULL,
              name VARCHAR(120) NOT NULL,
              category VARCHAR(100) NOT NULL DEFAULT '',
              target_position VARCHAR(120) NOT NULL DEFAULT '',
              description TEXT,
              requirement_summary TEXT,
              status VARCHAR(20) NOT NULL DEFAULT 'active',
              created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_job_profile_user ON job_profiles (user_id)",
            "CREATE INDEX IF NOT EXISTS idx_job_profile_guest_session ON job_profiles (guest_session_id)",
            "CREATE INDEX IF NOT EXISTS idx_job_profile_status ON job_profiles (status)",
        ]
    return [
        """
        CREATE TABLE job_profiles (
          id INT AUTO_INCREMENT PRIMARY KEY,
          user_id INT NOT NULL,
          guest_session_id VARCHAR(64) NULL,
          name VARCHAR(120) NOT NULL,
          category VARCHAR(100) NOT NULL DEFAULT '',
          target_position VARCHAR(120) NOT NULL DEFAULT '',
          description LONGTEXT,
          requirement_summary LONGTEXT,
          status VARCHAR(20) NOT NULL DEFAULT 'active',
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          INDEX idx_job_profile_user (user_id),
          INDEX idx_job_profile_guest_session (guest_session_id),
          INDEX idx_job_profile_status (status),
          CONSTRAINT fk_job_profile_user FOREIGN KEY (user_id) REFERENCES users(id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    ]


def _create_user_profiles_statements(is_sqlite: bool) -> list[str]:
    if is_sqlite:
        return [
            """
            CREATE TABLE user_profiles (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL UNIQUE,
              school VARCHAR(120) NOT NULL DEFAULT '',
              major VARCHAR(120) NOT NULL DEFAULT '',
              grade VARCHAR(50) NOT NULL DEFAULT '',
              class_name VARCHAR(120) NOT NULL DEFAULT '',
              phone VARCHAR(30) NOT NULL DEFAULT '',
              bio TEXT,
              updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_user_profile_user ON user_profiles (user_id)",
        ]
    return [
        """
        CREATE TABLE user_profiles (
          id INT AUTO_INCREMENT PRIMARY KEY,
          user_id INT NOT NULL UNIQUE,
          school VARCHAR(120) NOT NULL DEFAULT '',
          major VARCHAR(120) NOT NULL DEFAULT '',
          grade VARCHAR(50) NOT NULL DEFAULT '',
          class_name VARCHAR(120) NOT NULL DEFAULT '',
          phone VARCHAR(30) NOT NULL DEFAULT '',
          bio LONGTEXT,
          updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          INDEX idx_user_profile_user (user_id),
          CONSTRAINT fk_user_profile_user FOREIGN KEY (user_id) REFERENCES users(id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    ]


def ensure_guest_user(db: Session, user_model=None, organization_id: int | None = None):
    from app.models.entities import User

    model = user_model or User
    org_id = organization_id or settings.default_organization_id
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
        if getattr(guest_user, "organization_id", None) != org_id:
            guest_user.organization_id = org_id
            changed = True
        if changed:
            db.commit()
        return guest_user

    if legacy_user:
        legacy_user.username = settings.default_user_name
        legacy_user.display_name = GUEST_DISPLAY_NAME
        legacy_user.role = "user"
        legacy_user.status = "active"
        legacy_user.organization_id = org_id
        db.commit()
        db.refresh(legacy_user)
        return legacy_user

    guest_user = model(
        username=settings.default_user_name,
        password_hash="",
        display_name=GUEST_DISPLAY_NAME,
        role="user",
        status="active",
        organization_id=org_id,
    )
    db.add(guest_user)
    db.commit()
    db.refresh(guest_user)
    return guest_user
