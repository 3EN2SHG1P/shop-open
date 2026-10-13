from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PreviewItem(BaseModel):
    goods_id: int = Field(alias="goodsId", gt=0)
    sku_id: int = Field(alias="skuId", gt=0)
    quantity: int = Field(ge=1, le=9999)

    model_config = ConfigDict(populate_by_name=True)


class PreviewReq(BaseModel):
    type: Literal["cart", "buy"]
    cart_ids: list[int] | None = Field(default=None, alias="cartIds")
    items: list[PreviewItem] | None = None
    address_id: int | None = Field(default=None, alias="addressId")
    coupon_id: int | None = Field(default=None, alias="couponId")
    points_used: int = Field(default=0, ge=0, alias="pointsUsed")

    model_config = ConfigDict(populate_by_name=True)


class OrderCreateReq(BaseModel):
    preview_token: str = Field(alias="previewToken", min_length=8)
    address_id: int = Field(alias="addressId", gt=0)
    pay_type: int = Field(alias="payType", ge=1, le=2)
    coupon_id: int | None = Field(default=None, alias="couponId")
    points_used: int = Field(default=0, ge=0, alias="pointsUsed")
    buyer_message: str = Field(default="", alias="buyerMessage", max_length=200)

    model_config = ConfigDict(populate_by_name=True)


class PayReq(BaseModel):
    pay_type: int = Field(alias="payType", ge=1, le=2)

    model_config = ConfigDict(populate_by_name=True)
