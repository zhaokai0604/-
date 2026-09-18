from pydantic import BaseModel, Field


class BulkDeleteHistoryRequest(BaseModel):
    record_ids: list[int] = Field(default_factory=list)
    delete_all: bool = False


class DirectResumeAnalyzeRequest(BaseModel):
    filename: str
    content_base64: str
    target_position: str = ""
    job_description: str = ""
    job_profile_id: int = 0
    target_match_enabled: bool = False
    enable_ai: bool = True
    parent_record_id: int = 0
    stream: bool = False


class ApplyRecommendedJobRequest(BaseModel):
    job_id: str = ""
    source_url: str = ""
    target_position: str = ""


class RegisterRequest(BaseModel):
    username: str
    display_name: str = ""
    password: str
    confirm_password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class UserStatusRequest(BaseModel):
    status: str


class UserRoleRequest(BaseModel):
    role: str


class ResetPasswordRequest(BaseModel):
    password: str = ""
    confirm_password: str = ""


class AdminAiConfigRequest(BaseModel):
    provider: str = "deepseek"
    api_url: str
    model: str
    api_key: str = ""
    clear_api_key: bool = False


class AdminScoreConfigRequest(BaseModel):
    active_template: str = "default"


class StorageCleanupRequest(BaseModel):
    dry_run: bool = False


class JobProfileRequest(BaseModel):
    name: str
    category: str = ""
    target_position: str = ""
    description: str = ""
    requirement_summary: str = ""
    status: str = "active"


class UserProfileRequest(BaseModel):
    display_name: str | None = None
    school: str | None = None
    major: str | None = None
    grade: str | None = None
    class_name: str | None = None
    phone: str | None = None
    bio: str | None = None


class TeacherTrainingTaskRequest(BaseModel):
    issue: str
    class_name: str = ""


class ClassRosterRow(BaseModel):
    username: str
    display_name: str = ""
    class_name: str = ""
    major: str = ""
    grade: str = ""
    school: str = ""


class ClassRosterImportRequest(BaseModel):
    rows: list[ClassRosterRow] = Field(default_factory=list)
    create_missing: bool = True
