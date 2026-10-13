from fastapi import APIRouter, Depends

from core.config import config
from core.deps import AuthMember, get_current_member
from core.response import ok
from schemas.shop_order import OrderCreateReq, PreviewReq
from services import shop_order as service

router = APIRouter(prefix="/api/v1/shop", tags=["商城前台-订单"])


@router.post("/orders/preview")
async def preview(body: PreviewReq, member: AuthMember = Depends(get_current_member)):
    return ok(await service.preview_order(member.id, body))


@router.post("/orders")
async def create_order(body: OrderCreateReq, member: AuthMember = Depends(get_current_member)):
    result = await service.submit_order(member.id, body)
    return ok(result, "下单成功")


@router.get("/orders")
async def orders(
    page: int = 1,
    page_size: int = config.page_size,
    status: int | None = None,
    keyword: str = "",
    member: AuthMember = Depends(get_current_member),
):
    data = await service.list_orders(member.id, max(page, 1), max(min(page_size, 100), 1),
                                     None if status == 0 else status, keyword.strip())
    return ok(data)


@router.get("/orders/{order_key}")
async def order_detail(order_key: str, member: AuthMember = Depends(get_current_member)):
    return ok(await service.order_detail(member.id, order_key))


@router.post("/orders/{order_key}/cancel")
async def cancel(order_key: str, member: AuthMember = Depends(get_current_member)):
    await service.cancel_order(member.id, order_key)
    return ok(message="订单已取消")


@router.post("/orders/{order_key}/confirm-receipt")
async def confirm(order_key: str, member: AuthMember = Depends(get_current_member)):
    await service.confirm_order(member.id, order_key)
    return ok(message="已确认收货")


@router.post("/orders/{order_key}/again")
async def buy_again(order_key: str, member: AuthMember = Depends(get_current_member)):
    return ok(await service.buy_again(member.id, order_key))


@router.get("/orders/{order_key}/logistics")
async def logistics(order_key: str, member: AuthMember = Depends(get_current_member)):
    return ok(await service.logistics_info(member.id, order_key))
