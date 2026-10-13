from fastapi import APIRouter, Depends, Query, Response

from core import audit
from core.deps import require_permission
from core.response import ok
from schemas.order import AfterSaleAudit, BatchShipReq, ExpressSave, PriceReq, ShipReq
from services import order as svc

router = APIRouter(prefix="/api/v1", tags=["order"])

P = require_permission


@router.get("/orders")
async def list_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    order_no: str = "",
    member: str = "",
    receiver: str = "",
    pay_status: int | None = None,
    order_status: int | None = None,
    order_source: str = "",
    start_date: str = "",
    end_date: str = "",
    _user=Depends(P("order:list")),
):
    filters = {
        "order_no": order_no, "member": member, "receiver": receiver, "pay_status": pay_status,
        "order_status": order_status, "order_source": order_source, "start_date": start_date, "end_date": end_date,
    }
    return ok(await svc.list_orders(page, page_size, filters))


@router.get("/orders/export")
async def export_orders(
    order_no: str = "",
    member: str = "",
    receiver: str = "",
    pay_status: int | None = None,
    order_status: int | None = None,
    order_source: str = "",
    start_date: str = "",
    end_date: str = "",
    user=Depends(P("order:export")),
):
    filters = {
        "order_no": order_no, "member": member, "receiver": receiver, "pay_status": pay_status,
        "order_status": order_status, "order_source": order_source, "start_date": start_date, "end_date": end_date,
    }
    content = await svc.export_orders(filters)
    await audit.log_action(user.id, "order", audit.ACTION_EXPORT, "order:export", "导出订单")
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="orders.csv"'},
    )


@router.post("/orders/batch/ship")
async def batch_ship(body: BatchShipReq, user=Depends(P("order:ship"))):
    await svc.batch_ship(body, user)
    return ok()


@router.get("/orders/{oid}")
async def get_order(oid: int, _user=Depends(P("order:list"))):
    return ok(await svc.order_detail(oid))


@router.put("/orders/{oid}/price")
async def update_price(oid: int, body: PriceReq, user=Depends(P("order:edit"))):
    await svc.update_price(oid, body, user)
    return ok()


@router.post("/orders/{oid}/ship")
async def ship_order(oid: int, body: ShipReq, user=Depends(P("order:ship"))):
    await svc.ship_order(oid, body, user)
    return ok()


@router.post("/orders/{oid}/cancel")
async def cancel_order(oid: int, user=Depends(P("order:cancel"))):
    await svc.cancel_order(oid, user)
    return ok()


@router.get("/after-sales")
async def list_after_sales(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str = "",
    type: int | None = None,
    status: int | None = None,
    _user=Depends(P("order:list")),
):
    filters = {"keyword": keyword, "type": type, "status": status}
    return ok(await svc.list_after_sales(page, page_size, filters))


@router.post("/after-sales/{aid}/audit")
async def audit_after_sale(aid: int, body: AfterSaleAudit, user=Depends(P("order:audit"))):
    await svc.audit_after_sale(aid, body, user)
    return ok()


@router.post("/after-sales/{aid}/confirm-receipt")
async def confirm_receipt(aid: int, user=Depends(P("order:audit"))):
    await svc.confirm_after_sale_receipt(aid, user)
    return ok()


@router.get("/express-companies")
async def list_express(status: int | None = None, _user=Depends(P("order:list"))):
    return ok(await svc.list_express(status))


@router.post("/express-companies")
async def create_express(body: ExpressSave, user=Depends(P("order:add"))):
    return ok({"id": await svc.create_express(body, user)})
