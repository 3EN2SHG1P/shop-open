from fastapi import APIRouter, Depends, Query, Response

from core import audit
from core.deps import require_permission
from core.response import ok, page_data
from schemas.goods import (AuditReq, BatchIds, BatchStatus, BrandSave, CategorySave,
                           CommentAudit, CommentReply, GoodsSave, SpecAttrSave)
from services import goods as svc

router = APIRouter(prefix="/api/v1", tags=["goods"])

P = require_permission


@router.get("/categories")
async def category_tree(_user=Depends(P("goods:list"))):
    return ok(await svc.category_tree())


@router.post("/categories")
async def create_category(body: CategorySave, user=Depends(P("goods:add"))):
    return ok({"id": await svc.create_category(body, user)})


@router.put("/categories/{cid}")
async def update_category(cid: int, body: CategorySave, user=Depends(P("goods:edit"))):
    await svc.update_category(cid, body, user)
    return ok()


@router.delete("/categories/{cid}")
async def delete_category(cid: int, user=Depends(P("goods:delete"))):
    await svc.delete_category(cid, user)
    return ok()


@router.get("/brands")
async def list_brands(
    keyword: str = "",
    status: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _user=Depends(P("goods:list")),
):
    return ok(await svc.list_brands(keyword, status, page, page_size))


@router.post("/brands")
async def create_brand(body: BrandSave, user=Depends(P("goods:add"))):
    return ok({"id": await svc.create_brand(body, user)})


@router.put("/brands/{bid}")
async def update_brand(bid: int, body: BrandSave, user=Depends(P("goods:edit"))):
    await svc.update_brand(bid, body, user)
    return ok()


@router.put("/brands/{bid}/status")
async def set_brand_status(bid: int, status: int = Query(..., ge=0, le=1), user=Depends(P("goods:edit"))):
    await svc.set_brand_status(bid, status, user)
    return ok()


@router.delete("/brands/{bid}")
async def delete_brand(bid: int, user=Depends(P("goods:delete"))):
    await svc.delete_brand(bid, user)
    return ok()


@router.get("/goods/specs")
async def list_specs(category_id: int | None = None, _user=Depends(P("goods:list"))):
    return ok(await svc.list_specs(category_id))


@router.post("/goods/specs")
async def create_spec(body: SpecAttrSave, user=Depends(P("goods:add"))):
    return ok({"id": await svc.create_spec(body, user)})


@router.put("/goods/specs/{sid}")
async def update_spec(sid: int, body: SpecAttrSave, user=Depends(P("goods:edit"))):
    await svc.update_spec(sid, body, user)
    return ok()


@router.delete("/goods/specs/{sid}")
async def delete_spec(sid: int, user=Depends(P("goods:delete"))):
    await svc.delete_spec(sid, user)
    return ok()


@router.get("/goods/attrs")
async def list_attrs(category_id: int | None = None, _user=Depends(P("goods:list"))):
    return ok(await svc.list_attrs(category_id))


@router.post("/goods/attrs")
async def create_attr(body: SpecAttrSave, user=Depends(P("goods:add"))):
    return ok({"id": await svc.create_attr(body, user)})


@router.put("/goods/attrs/{aid}")
async def update_attr(aid: int, body: SpecAttrSave, user=Depends(P("goods:edit"))):
    await svc.update_attr(aid, body, user)
    return ok()


@router.delete("/goods/attrs/{aid}")
async def delete_attr(aid: int, user=Depends(P("goods:delete"))):
    await svc.delete_attr(aid, user)
    return ok()


@router.get("/goods/comments")
async def list_comments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    goods_id: int | None = None,
    member_id: int | None = None,
    status: int | None = None,
    score: int | None = None,
    keyword: str = "",
    _user=Depends(P("goods:list")),
):
    filters = {"goods_id": goods_id, "member_id": member_id, "status": status, "score": score, "keyword": keyword}
    return ok(await svc.list_comments(page, page_size, filters))


@router.put("/goods/comments/{cid}/audit")
async def audit_comment(cid: int, body: CommentAudit, user=Depends(P("goods:audit"))):
    await svc.audit_comment(cid, body, user)
    return ok()


@router.post("/goods/comments/{cid}/reply")
async def reply_comment(cid: int, body: CommentReply, user=Depends(P("goods:edit"))):
    await svc.reply_comment(cid, body, user)
    return ok()


@router.delete("/goods/comments/{cid}")
async def delete_comment(cid: int, user=Depends(P("goods:delete"))):
    await svc.delete_comment(cid, user)
    return ok()


@router.get("/goods/export")
async def export_goods(
    keyword: str = "",
    category_id: int | None = None,
    brand_id: int | None = None,
    status: int | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    start_date: str = "",
    end_date: str = "",
    user=Depends(P("goods:export")),
):
    filters = {
        "keyword": keyword, "category_id": category_id, "brand_id": brand_id, "status": status,
        "min_price": min_price, "max_price": max_price, "start_date": start_date, "end_date": end_date,
    }
    content = await svc.export_goods(filters, user)
    await audit.log_action(user.id, "goods", audit.ACTION_EXPORT, "goods:export", "导出商品")
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="goods.csv"'},
    )


@router.get("/goods")
async def list_goods(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str = "",
    category_id: int | None = None,
    brand_id: int | None = None,
    status: int | None = None,
    audit_status: int | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    start_date: str = "",
    end_date: str = "",
    user=Depends(P("goods:list")),
):
    filters = {
        "keyword": keyword, "category_id": category_id, "brand_id": brand_id, "status": status,
        "audit_status": audit_status, "min_price": min_price, "max_price": max_price,
        "start_date": start_date, "end_date": end_date,
    }
    data = await svc.list_goods(page, page_size, filters, user)
    return ok(page_data(data["list"], data["total"], page, page_size))


@router.post("/goods")
async def create_goods(body: GoodsSave, user=Depends(P("goods:add"))):
    return ok({"id": await svc.create_goods(body, user)})


@router.put("/goods/batch/status")
async def batch_status(body: BatchStatus, user=Depends(P("goods:edit"))):
    await svc.batch_operate(body.ids, "status", body.status, user)
    return ok()


@router.delete("/goods/batch")
async def batch_delete(body: BatchIds, user=Depends(P("goods:delete"))):
    await svc.batch_operate(body.ids, "delete", None, user)
    return ok()


@router.post("/goods/{gid}/audit")
async def audit_goods(gid: int, body: AuditReq, user=Depends(P("goods:audit"))):
    await svc.audit_goods(gid, body, user)
    return ok()


@router.get("/goods/{gid}")
async def get_goods(gid: int, user=Depends(P("goods:list"))):
    return ok(await svc.get_goods(gid, user))


@router.put("/goods/{gid}")
async def update_goods(gid: int, body: GoodsSave, user=Depends(P("goods:edit"))):
    await svc.update_goods(gid, body, user)
    return ok()


@router.delete("/goods/{gid}")
async def delete_goods(gid: int, user=Depends(P("goods:delete"))):
    await svc.delete_goods(gid, user)
    return ok()
