from fastapi import APIRouter, Depends

from core.deps import AuthMember, get_current_member
from core.response import ok
from schemas.shop_order import PayReq
from services import shop_order as service

router = APIRouter(prefix="/api/v1/shop", tags=["商城前台-支付"])


@router.post("/pay/{order_key}")
async def pay(order_key: str, body: PayReq, member: AuthMember = Depends(get_current_member)):
    data = await service.pay_order(member.id, order_key, body.pay_type)
    return ok(data, "支付成功（演示环境模拟支付）")


@router.get("/pay/{order_key}/status")
async def pay_status(order_key: str, member: AuthMember = Depends(get_current_member)):
    return ok(await service.pay_status(member.id, order_key))
