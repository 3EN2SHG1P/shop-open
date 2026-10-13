from pydantic import BaseModel, Field


class CouponSave(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    type: int = Field(ge=1, le=2)
    amount: float = Field(default=0, ge=0, le=99999999)
    rate: float | None = Field(default=None, ge=0, le=10)
    min_amount: float = Field(default=0, ge=0, le=99999999, alias="minAmount")
    scope: int = Field(default=1, ge=1, le=3)
    scope_ids: str = Field(default="", max_length=500, alias="scopeIds")
    total_count: int = Field(default=0, ge=0, le=100000000, alias="totalCount")
    per_limit: int = Field(default=1, ge=1, le=1000, alias="perLimit")
    start_time: str = Field(min_length=1, max_length=30, alias="startTime")
    end_time: str = Field(min_length=1, max_length=30, alias="endTime")
    status: int = Field(default=1, ge=0, le=1)

    class Config:
        populate_by_name = True


class SeckillSave(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    goods_id: int = Field(ge=1, alias="goodsId")
    sku_id: int | None = Field(default=None, ge=1, alias="skuId")
    seckill_price: float = Field(default=0, ge=0, le=99999999, alias="seckillPrice")
    seckill_stock: int = Field(default=0, ge=0, le=100000000, alias="seckillStock")
    per_limit: int = Field(default=1, ge=1, le=1000, alias="perLimit")
    start_time: str = Field(min_length=1, max_length=30, alias="startTime")
    end_time: str = Field(min_length=1, max_length=30, alias="endTime")
    status: int = Field(default=1, ge=0, le=1)
    is_stackable: int = Field(default=0, ge=0, le=1, alias="isStackable")

    class Config:
        populate_by_name = True


class FullDiscountSave(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    type: int = Field(ge=1, le=2)
    threshold: float = Field(default=0, ge=0, le=99999999)
    discount_value: float = Field(default=0, ge=0, le=99999999, alias="discountValue")
    scope: int = Field(default=1, ge=1, le=3)
    scope_ids: str = Field(default="", max_length=500, alias="scopeIds")
    start_time: str = Field(min_length=1, max_length=30, alias="startTime")
    end_time: str = Field(min_length=1, max_length=30, alias="endTime")
    is_stackable: int = Field(default=0, ge=0, le=1, alias="isStackable")

    class Config:
        populate_by_name = True


class GroupBuySave(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    goods_id: int = Field(ge=1, alias="goodsId")
    leader_price: float = Field(default=0, ge=0, le=99999999, alias="leaderPrice")
    member_price: float = Field(default=0, ge=0, le=99999999, alias="memberPrice")
    group_size: int = Field(default=2, ge=2, le=100, alias="groupSize")
    valid_hours: int = Field(default=24, ge=1, le=720, alias="validHours")
    start_time: str = Field(min_length=1, max_length=30, alias="startTime")
    end_time: str = Field(min_length=1, max_length=30, alias="endTime")
    status: int = Field(default=1, ge=0, le=1)

    class Config:
        populate_by_name = True


class DistributorSave(BaseModel):
    member_id: int = Field(ge=1, alias="memberId")
    level: int = Field(default=1, ge=1, le=3)
    commission_rate: float = Field(default=5.0, ge=0, le=100, alias="commissionRate")
    status: int = Field(default=1, ge=0, le=3)
    invited_by: int | None = Field(default=None, alias="invitedBy")

    class Config:
        populate_by_name = True
