from fastapi import APIRouter

from app.api.admin_routes import router as admin_router
from app.api.analysis_routes import router as analysis_router
from app.api.auth_routes import router as auth_router
from app.api.job_routes import router as job_router
from app.api.teacher_routes import router as teacher_router
from app.api.users_routes import router as users_router
from app.api.workspace_routes import router as workspace_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(users_router)
router.include_router(admin_router)
router.include_router(teacher_router)
router.include_router(job_router)
router.include_router(analysis_router)
router.include_router(workspace_router)
