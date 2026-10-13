from fastapi import APIRouter, Depends

from core.deps import AuthMember, get_current_member
from core.response import ok
from schemas.shop_cart import CartAddReq, CartMergeReq, CartQuantityReq, CartSelectedReq
from services import shop_cart as service

router = APIRouter(prefix="/api/v1/shop", tags=["商城前台-购物车"])


@router.get("/cart")
async def cart_list(member: AuthMember = Depends(get_current_member)):
    return ok(await service.cart_list(member.id))


@router.post("/cart")
async def add_cart(body: CartAddReq, member: AuthMember = Depends(get_current_member)):
    await service.add_cart(member.id, body.goods_id, body.sku_id, body.quantity)
    return ok(message="已加入购物车")


@router.put("/cart/selected")
async def update_selected(body: CartSelectedReq, member: AuthMember = Depends(get_current_member)):
    await service.update_selected(member.id, body.ids, body.selected)
    return ok()


@router.put("/cart/{cart_id}")
async def update_quantity(cart_id: int, body: CartQuantityReq, member: AuthMember = Depends(get_current_member)):
    await service.update_quantity(member.id, cart_id, body.quantity)
    return ok()


@router.delete("/cart/{cart_id}")
async def delete_cart(cart_id: int, member: AuthMember = Depends(get_current_member)):
    await service.delete_cart(member.id, cart_id)
    return ok()


@router.post("/cart/merge")
async def merge_cart(body: CartMergeReq, member: AuthMember = Depends(get_current_member)):
    await service.merge_cart(member.id, [i.model_dump(by_alias=True) for i in body.items])
    return ok()


@router.delete("/cart")
async def clear_cart(member: AuthMember = Depends(get_current_member)):
    await service.clear_cart(member.id)
    return ok()
