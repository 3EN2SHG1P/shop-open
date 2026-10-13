from fastapi import APIRouter, Depends

from core.config import config
from core.deps import AuthMember, get_current_member
from core.response import ok
from services import shop_coupon as service

router = APIRouter(prefix="/api/v1/shop", tags=["商城前台-优惠券"])


@router.get("/coupons")
async def my_coupons(
    page: int = 1,
    page_size: int = config.page_size,
    status: int | None = None,
    member: AuthMember = Depends(get_current_member),
):
    return ok(await service.list_mine(member.id, max(page, 1), max(min(page_size, 100), 1), status))


@router.get("/coupons/available")
async def available_coupons(member: AuthMember = Depends(get_current_member)):
    return ok(await service.available_list(member.id))


@router.post("/coupons/{coupon_id}/receive")
async def receive_coupon(coupon_id: int, member: AuthMember = Depends(get_current_member)):
    return ok(await service.receive(member.id, coupon_id), "领取成功")
