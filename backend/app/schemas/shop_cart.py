from pydantic import BaseModel, ConfigDict, Field


class CartAddReq(BaseModel):
    goods_id: int = Field(alias="goodsId", gt=0)
    sku_id: int = Field(alias="skuId", gt=0)
    quantity: int = Field(default=1, ge=1, le=9999)

    model_config = ConfigDict(populate_by_name=True)


class CartQuantityReq(BaseModel):
    quantity: int = Field(ge=1, le=9999)

    model_config = ConfigDict(populate_by_name=True)


class CartSelectedReq(BaseModel):
    ids: list[int] = Field(default_factory=list)
    selected: bool = True

    model_config = ConfigDict(populate_by_name=True)


class CartMergeItem(BaseModel):
    goods_id: int = Field(alias="goodsId", gt=0)
    sku_id: int = Field(alias="skuId", gt=0)
    quantity: int = Field(default=1, ge=1, le=9999)
    selected: int | bool | None = None

    model_config = ConfigDict(populate_by_name=True)


class CartMergeReq(BaseModel):
    items: list[CartMergeItem] = Field(default_factory=list, max_length=200)

    model_config = ConfigDict(populate_by_name=True)
