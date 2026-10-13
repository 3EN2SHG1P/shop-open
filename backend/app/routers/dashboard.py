from fastapi import APIRouter, Depends, Query

from core.deps import require_permission
from core.response import ok
from services import dashboard as svc

router = APIRouter(prefix="/api/v1", tags=["dashboard"])

P = require_permission


@router.get("/dashboard/overview")
async def overview(days: int = Query(1, ge=1, le=30), _user=Depends(P("dashboard:view"))):
    return ok(await svc.overview(days))


@router.get("/dashboard/trend")
async def trend(days: int = Query(7, ge=7, le=30), _user=Depends(P("dashboard:view"))):
    return ok(await svc.trend(days))


@router.get("/dashboard/hot-goods")
async def hot_goods(days: int = Query(30, ge=7, le=90), _user=Depends(P("dashboard:view"))):
    return ok(await svc.hot_goods(days))
