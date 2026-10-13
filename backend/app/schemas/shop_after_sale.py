from pydantic import BaseModel, ConfigDict, Field


class AfterSaleCreateReq(BaseModel):
    order_id: int = Field(alias="orderId", gt=0)
    type: int = Field(ge=1, le=2)
    reason: str = Field(min_length=1, max_length=200)
    amount: float | None = Field(default=None, gt=0)

    model_config = ConfigDict(populate_by_name=True)


class AfterSaleLogisticsReq(BaseModel):
    return_logistics_company: str = Field(alias="returnLogisticsCompany", min_length=1, max_length=50)
    return_logistics_no: str = Field(alias="returnLogisticsNo", min_length=1, max_length=50)

    model_config = ConfigDict(populate_by_name=True)
