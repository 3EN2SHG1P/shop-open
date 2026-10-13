from fastapi import APIRouter, Depends, Query, Response

from core import audit
from core.deps import require_permission
from core.response import ok
from services import admin_logs as svc

router = APIRouter(prefix="/api/v1", tags=["logs"])

P = require_permission


@router.get("/admin-logs")
async def list_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin_name: str = "",
    module: str = "",
    action_type: int | None = None,
    start_date: str = "",
    end_date: str = "",
    _user=Depends(P("logs:list")),
):
    filters = {
        "admin_name": admin_name, "module": module, "action_type": action_type,
        "start_date": start_date, "end_date": end_date,
    }
    return ok(await svc.list_logs(page, page_size, filters))


@router.get("/admin-logs/export")
async def export_logs(
    admin_name: str = "",
    module: str = "",
    action_type: int | None = None,
    start_date: str = "",
    end_date: str = "",
    user=Depends(P("logs:export")),
):
    filters = {
        "admin_name": admin_name, "module": module, "action_type": action_type,
        "start_date": start_date, "end_date": end_date,
    }
    content = await svc.export_logs(filters)
    await audit.log_action(user.id, "settings", audit.ACTION_EXPORT, "logs:export", "导出操作日志")
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="admin_logs.csv"'},
    )
