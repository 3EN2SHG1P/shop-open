from fastapi import APIRouter, Depends

from core.deps import AuthMember, get_current_member
from core.response import ok
from schemas.shop_address import AddressSaveReq
from services import shop_address as service

router = APIRouter(prefix="/api/v1/shop", tags=["商城前台-地址与区域"])


@router.get("/addresses")
async def list_addresses(member: AuthMember = Depends(get_current_member)):
    return ok(await service.list_addresses(member.id))


@router.post("/addresses")
async def create_address(body: AddressSaveReq, member: AuthMember = Depends(get_current_member)):
    aid = await service.create_address(member.id, body.model_dump(by_alias=True))
    return ok({"id": aid}, "地址已保存")


@router.put("/addresses/{address_id}")
async def update_address(address_id: int, body: AddressSaveReq, member: AuthMember = Depends(get_current_member)):
    await service.update_address(member.id, address_id, body.model_dump(by_alias=True))
    return ok(message="地址已更新")


@router.put("/addresses/{address_id}/default")
async def set_default(address_id: int, member: AuthMember = Depends(get_current_member)):
    await service.set_default(member.id, address_id)
    return ok()


@router.delete("/addresses/{address_id}")
async def delete_address(address_id: int, member: AuthMember = Depends(get_current_member)):
    await service.delete_address(member.id, address_id)
    return ok()


@router.get("/regions")
async def list_regions(parent_code: str = ""):
    return ok(await service.list_regions(parent_code))
