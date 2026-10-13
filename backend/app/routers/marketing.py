from fastapi import APIRouter, Depends, Query

from core.deps import require_permission
from core.response import ok
from schemas.marketing import (
    CouponSave,
    DistributorSave,
    FullDiscountSave,
    GroupBuySave,
    SeckillSave,
)
from services import marketing as svc

router = APIRouter(prefix="/api/v1", tags=["marketing"])

P = require_permission


# ==================== 优惠券 ====================


@router.get("/coupons")
async def list_coupons(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str = "",
    type: int | None = None,
    scope: int | None = None,
    status: int | None = None,
    start_date: str = "",
    end_date: str = "",
    _user=Depends(P("marketing:list")),
):
    filters = {
        "keyword": keyword, "type": type, "scope": scope, "status": status,
        "start_date": start_date, "end_date": end_date,
    }
    return ok(await svc.list_coupons(page, page_size, filters))


@router.post("/coupons")
async def create_coupon(body: CouponSave, user=Depends(P("marketing:add"))):
    return ok({"id": await svc.create_coupon(body, user)})


@router.put("/coupons/{coupon_id}")
async def update_coupon(coupon_id: int, body: CouponSave, user=Depends(P("marketing:edit"))):
    await svc.update_coupon(coupon_id, body, user)
    return ok()


@router.delete("/coupons/{coupon_id}")
async def delete_coupon(coupon_id: int, user=Depends(P("marketing:delete"))):
    await svc.delete_coupon(coupon_id, user)
    return ok()


@router.get("/coupons/{coupon_id}/records")
async def list_coupon_records(
    coupon_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str = "",
    status: int | None = None,
    _user=Depends(P("marketing:list")),
):
    filters = {"keyword": keyword, "status": status}
    return ok(await svc.list_coupon_records(coupon_id, page, page_size, filters))


# ==================== 秒杀 ====================


@router.get("/seckills")
async def list_seckills(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str = "",
    _user=Depends(P("marketing:list")),
):
    filters = {"keyword": keyword}
    return ok(await svc.list_seckills(page, page_size, filters))


@router.get("/seckills/{activity_id}")
async def get_seckill(activity_id: int, _user=Depends(P("marketing:list"))):
    return ok(await svc.seckill_detail(activity_id))


@router.post("/seckills")
async def create_seckill(body: SeckillSave, user=Depends(P("marketing:add"))):
    return ok({"id": await svc.save_seckill(None, body, user)})


@router.put("/seckills/{activity_id}")
async def update_seckill(activity_id: int, body: SeckillSave, user=Depends(P("marketing:edit"))):
    return ok({"id": await svc.save_seckill(activity_id, body, user)})


# ==================== 满减满折 ====================


@router.get("/full-discounts")
async def list_full_discounts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str = "",
    type: int | None = None,
    _user=Depends(P("marketing:list")),
):
    filters = {"keyword": keyword, "type": type}
    return ok(await svc.list_full_discounts(page, page_size, filters))


@router.post("/full-discounts")
async def create_full_discount(body: FullDiscountSave, user=Depends(P("marketing:add"))):
    return ok({"id": await svc.save_full_discount(None, body, user)})


@router.put("/full-discounts/{activity_id}")
async def update_full_discount(activity_id: int, body: FullDiscountSave, user=Depends(P("marketing:edit"))):
    return ok({"id": await svc.save_full_discount(activity_id, body, user)})


# ==================== 拼团 ====================


@router.get("/group-buys")
async def list_group_buys(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str = "",
    _user=Depends(P("marketing:list")),
):
    filters = {"keyword": keyword}
    return ok(await svc.list_group_buys(page, page_size, filters))


@router.post("/group-buys")
async def create_group_buy(body: GroupBuySave, user=Depends(P("marketing:add"))):
    return ok({"id": await svc.save_group_buy(None, body, user)})


@router.put("/group-buys/{activity_id}")
async def update_group_buy(activity_id: int, body: GroupBuySave, user=Depends(P("marketing:edit"))):
    return ok({"id": await svc.save_group_buy(activity_id, body, user)})


# ==================== 分销 ====================


@router.get("/distributors")
async def list_distributors(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str = "",
    level: int | None = None,
    status: int | None = None,
    _user=Depends(P("marketing:list")),
):
    filters = {"keyword": keyword, "level": level, "status": status}
    return ok(await svc.list_distributors(page, page_size, filters))


@router.post("/distributors")
async def create_distributor(body: DistributorSave, user=Depends(P("marketing:add"))):
    return ok({"id": await svc.save_distributor(None, body, user)})


@router.put("/distributors/{dist_id}")
async def update_distributor(dist_id: int, body: DistributorSave, user=Depends(P("marketing:edit"))):
    return ok({"id": await svc.save_distributor(dist_id, body, user)})


@router.get("/distributors/{dist_id}/commissions")
async def list_commission_logs(
    dist_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _user=Depends(P("marketing:list")),
):
    return ok(await svc.list_commission_logs(dist_id, page, page_size))


# ==================== 下拉选项 ====================


@router.get("/marketing/goods-options")
async def goods_options(_user=Depends(P("marketing:list"))):
    return ok(await svc.goods_options())


@router.get("/marketing/goods/{goods_id}/skus")
async def sku_options(goods_id: int, _user=Depends(P("marketing:list"))):
    return ok(await svc.sku_options(goods_id))


@router.get("/marketing/member-options")
async def member_options(_user=Depends(P("marketing:list"))):
    return ok(await svc.member_options())
