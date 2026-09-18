"""API 层兼容入口：平台编排逻辑已下沉至 services.platform_service。"""

from app.services import platform_service
from app.services.ai import enhance_with_deepseek

# 导出 platform_service.__all__ 中的公开符号
for _name in platform_service.__all__:
    globals()[_name] = getattr(platform_service, _name)

# 路由与测试额外依赖（未列入 __all__ 但仍需经 api.platform 访问）
record_status_response = platform_service.record_status_response
download_record_report_file = platform_service.download_record_report_file
_run_analysis_pipeline = platform_service._run_analysis_pipeline

__all__ = [
    *platform_service.__all__,
    "record_status_response",
    "download_record_report_file",
    "_run_analysis_pipeline",
    "enhance_with_deepseek",
]
