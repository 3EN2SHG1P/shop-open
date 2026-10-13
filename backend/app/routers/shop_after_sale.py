from fastapi import APIRouter, Depends

from core.config import config
from core.deps import AuthMember, get_current_member
from core.response import ok
from schemas.shop_after_sale import AfterSaleCreateReq, AfterSaleLogisticsReq
from services import shop_after_sale as service

router = APIRouter(prefix="/api/v1/shop", tags=["商城前台-售后"])


@router.get("/after-sales")
async def after_sales(
    page: int = 1,
    page_size: int = config.page_size,
    status: int | None = None,
    member: AuthMember = Depends(get_current_member),
):
    return ok(await service.list_after_sales(member.id, max(page, 1), max(min(page_size, 100), 1), status))


@router.get("/after-sales/{after_sale_id}")
async def after_sale_detail(after_sale_id: int, member: AuthMember = Depends(get_current_member)):
    return ok(await service.after_sale_detail(member.id, after_sale_id))


@router.post("/after-sales")
async def create_after_sale(body: AfterSaleCreateReq, member: AuthMember = Depends(get_current_member)):
    aid = await service.apply_after_sale(member.id, body)
    return ok({"id": aid}, "售后申请已提交")


@router.post("/after-sales/{after_sale_id}/logistics")
async def fill_logistics(after_sale_id: int, body: AfterSaleLogisticsReq, member: AuthMember = Depends(get_current_member)):
    await service.fill_logistics(member.id, after_sale_id, body.return_logistics_company, body.return_logistics_no)
    return ok(message="退货运单已填写")


@router.post("/after-sales/{after_sale_id}/cancel")
async def cancel_after_sale(after_sale_id: int, member: AuthMember = Depends(get_current_member)):
    await service.cancel_after_sale(member.id, after_sale_id)
    return ok(message="已撤销售后申请")
