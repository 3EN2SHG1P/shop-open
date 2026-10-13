from fastapi import APIRouter, Depends

from core.config import config
from core.deps import AuthMember, get_current_member
from core.response import ok
from services import shop_member as service

router = APIRouter(prefix="/api/v1/shop", tags=["商城前台-积分"])


@router.get("/points")
async def points_summary(member: AuthMember = Depends(get_current_member)):
    return ok(await service.points_summary(member.id))


@router.get("/points/logs")
async def points_logs(
    page: int = 1,
    page_size: int = config.page_size,
    member: AuthMember = Depends(get_current_member),
):
    return ok(await service.points_logs(member.id, max(page, 1), max(min(page_size, 100), 1)))
