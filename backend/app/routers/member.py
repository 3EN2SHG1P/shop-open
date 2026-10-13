from fastapi import APIRouter, Depends, Query

from core.deps import require_permission
from core.response import ok
from schemas.member import (
    LevelSave,
    MemberProfileUpdate,
    MemberResetPassword,
    MemberStatusUpdate,
    PointsAdjust,
)
from services import member as svc

router = APIRouter(prefix="/api/v1", tags=["member"])

P = require_permission


@router.get("/members")
async def list_members(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str = "",
    level_id: int | None = None,
    status: int | None = None,
    start_date: str = "",
    end_date: str = "",
    _user=Depends(P("member:list")),
):
    filters = {
        "keyword": keyword, "level_id": level_id, "status": status,
        "start_date": start_date, "end_date": end_date,
    }
    return ok(await svc.list_members(page, page_size, filters))


@router.get("/members/{member_id}")
async def get_member(member_id: int, _user=Depends(P("member:list"))):
    return ok(await svc.member_detail(member_id))


@router.put("/members/{member_id}")
async def update_member(member_id: int, body: MemberProfileUpdate, user=Depends(P("member:edit"))):
    await svc.update_member_profile(member_id, body, user)
    return ok()


@router.put("/members/{member_id}/status")
async def set_member_status(member_id: int, body: MemberStatusUpdate, user=Depends(P("member:edit"))):
    await svc.set_member_status(member_id, body, user)
    return ok()


@router.put("/members/{member_id}/reset-password")
async def reset_member_password(member_id: int, body: MemberResetPassword, user=Depends(P("member:edit"))):
    await svc.reset_member_password(member_id, body, user)
    return ok()


@router.get("/member-levels")
async def list_levels(_user=Depends(P("member:list"))):
    return ok(await svc.list_levels())


@router.post("/member-levels")
async def create_level(body: LevelSave, user=Depends(P("member:add"))):
    return ok({"id": await svc.create_level(body, user)})


@router.put("/member-levels/{level_id}")
async def update_level(level_id: int, body: LevelSave, user=Depends(P("member:edit"))):
    await svc.update_level(level_id, body, user)
    return ok()


@router.get("/points/logs")
async def list_points_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    member: str = "",
    type: int | None = None,
    start_date: str = "",
    end_date: str = "",
    _user=Depends(P("member:list")),
):
    filters = {"member": member, "type": type, "start_date": start_date, "end_date": end_date}
    return ok(await svc.list_points_logs(page, page_size, filters))


@router.post("/points/adjust")
async def adjust_points(body: PointsAdjust, user=Depends(P("member:edit"))):
    return ok({"points": await svc.adjust_points(body, user)})


@router.get("/member-logs")
async def list_member_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str = "",
    action_type: str = "",
    start_date: str = "",
    end_date: str = "",
    _user=Depends(P("member:list")),
):
    filters = {"keyword": keyword, "action_type": action_type, "start_date": start_date, "end_date": end_date}
    return ok(await svc.list_member_logs(page, page_size, filters))
