from fastapi import APIRouter

from core.response import ok
from services import shop_live

router = APIRouter(prefix="/api/v1/shop", tags=["前台-实时更新"])


@router.get("/live/version")
async def live_version():
    return ok(await shop_live.version())
