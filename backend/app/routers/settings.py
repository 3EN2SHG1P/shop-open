from fastapi import APIRouter, Depends, Query

from core.deps import require_permission
from core.response import ok
from schemas.settings import ConfigSave, FreightTemplateSave
from services import settings as svc

router = APIRouter(prefix="/api/v1", tags=["settings"])

P = require_permission


# ==================== 系统配置 ====================


@router.get("/settings/{group}")
async def get_configs(group: str, _user=Depends(P("settings:list"))):
    return ok(await svc.get_configs(group))


@router.put("/settings/{group}")
async def save_configs(group: str, body: ConfigSave, user=Depends(P("settings:edit"))):
    await svc.save_configs(group, body.items, user)
    return ok()


# ==================== 运费模板 ====================


@router.get("/freight-templates")
async def list_freight_templates(_user=Depends(P("settings:list"))):
    return ok(await svc.list_freight_templates())


@router.post("/freight-templates")
async def create_freight_template(body: FreightTemplateSave, user=Depends(P("settings:add"))):
    return ok({"id": await svc.save_freight_template(None, body, user)})


@router.put("/freight-templates/{template_id}")
async def update_freight_template(template_id: int, body: FreightTemplateSave, user=Depends(P("settings:edit"))):
    return ok({"id": await svc.save_freight_template(template_id, body, user)})


@router.delete("/freight-templates/{template_id}")
async def delete_freight_template(template_id: int, user=Depends(P("settings:delete"))):
    await svc.delete_freight_template(template_id, user)
    return ok()
