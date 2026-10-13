from fastapi import APIRouter, Depends

from core.config import config
from core.deps import AuthMember, get_current_member
from core.response import ok
from schemas.shop_catalog import CommentReq
from services import shop_catalog as service

router = APIRouter(prefix="/api/v1/shop", tags=["商城前台-首页与商品"])


@router.get("/home")
async def home():
    return ok(await service.home())


@router.get("/notices")
async def notices():
    return ok(await service.list_notices())


@router.get("/ads")
async def ads(position_id: int | None = None):
    return ok(await service.list_ads(position_id))


@router.get("/goods")
async def goods(
    page: int = 1,
    page_size: int = config.page_size,
    keyword: str = "",
    category_id: int | None = None,
    brand_id: int | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    is_hot: int | None = None,
    is_new: int | None = None,
    is_recommend: int | None = None,
    in_stock: bool = False,
    sort_field: str = "default",
    sort_order: str = "desc",
):
    filters = {
        "keyword": keyword.strip(),
        "category_id": category_id,
        "brand_id": brand_id,
        "min_price": min_price,
        "max_price": max_price,
        "is_hot": is_hot,
        "is_new": is_new,
        "is_recommend": is_recommend,
        "in_stock": in_stock,
        "sort_field": sort_field,
        "sort_order": sort_order,
    }
    data = await service.list_goods(max(page, 1), max(min(page_size, 100), 1), filters)
    return ok(data)


@router.get("/goods/{goods_id}")
async def goods_detail(goods_id: int):
    return ok(await service.goods_detail(goods_id))


@router.get("/goods/{goods_id}/comments")
async def comments(goods_id: int, page: int = 1, page_size: int = config.page_size):
    return ok(await service.list_comments(goods_id, max(page, 1), max(min(page_size, 100), 1)))


@router.post("/goods/{goods_id}/comments")
async def post_comment(goods_id: int, body: CommentReq, member: AuthMember = Depends(get_current_member)):
    cid = await service.post_comment(member.id, goods_id, body.score, body.content)
    return ok({"id": cid}, "评价成功，待商家审核后展示")


@router.post("/goods/{goods_id}/visit")
async def visit(goods_id: int):
    await service.visit(goods_id)
    return ok()


@router.get("/categories")
async def categories():
    return ok(await service.list_categories())


@router.get("/brands")
async def brands():
    return ok(await service.list_brands())


@router.get("/specs")
async def specs():
    return ok(await service.list_specs())
