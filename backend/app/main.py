import logging
import secrets
import time
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.routes import router
from app.core.config import settings
from app.core.database import init_db
from app.core.env import is_production_like
from app.services.auth import parse_session_token

logger = logging.getLogger("resume_ai.access")


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or secrets.token_hex(8)
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        if not request.url.path.endswith("/health"):
            request_id = getattr(request.state, "request_id", "-")
            logger.info(
                "request_id=%s %s %s -> %s (%.1fms)",
                request_id,
                request.method,
                request.url.path,
                response.status_code,
                elapsed_ms,
            )
        return response


class GuestSessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        session_id = request.cookies.get(settings.guest_session_cookie_name)
        new_session = False
        if not session_id:
            session_id = secrets.token_hex(16)
            new_session = True
        request.state.guest_session_id = session_id

        response = await call_next(request)
        if new_session:
            logged_in = False
            token = request.cookies.get(settings.session_cookie_name)
            if token:
                payload = parse_session_token(token)
                logged_in = bool(payload and isinstance(payload.get("user_id"), int))
            if not logged_in:
                response.set_cookie(
                    key=settings.guest_session_cookie_name,
                    value=session_id,
                    max_age=settings.guest_session_expire_days * 86400,
                    httponly=True,
                    samesite="lax",
                    secure=settings.session_cookie_secure,
                    path="/",
                )
        return response


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="简析智评——大学生简历诊断与求职成长平台",
    description="高校学生求职简历分析与优化平台",
    version=settings.app_version,
    lifespan=lifespan,
)


@app.exception_handler(PermissionError)
async def permission_error_handler(_request: Request, exc: PermissionError) -> JSONResponse:
    return JSONResponse(status_code=403, content={"detail": str(exc) or "没有权限执行此操作"})


@app.exception_handler(ValueError)
async def value_error_handler(_request: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc) or "请求参数无效"})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "-")
    logger.error("request_id=%s unhandled error: %s\n%s", request_id, exc, traceback.format_exc())
    detail = "服务器内部错误，请稍后重试。" if is_production_like() else str(exc) or "服务器内部错误"
    return JSONResponse(status_code=500, content={"detail": detail, "request_id": request_id})

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GuestSessionMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RequestIdMiddleware)

settings.ensure_directories()
app.include_router(router, prefix="/api")
