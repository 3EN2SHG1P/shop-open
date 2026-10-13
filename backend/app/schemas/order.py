from pydantic import BaseModel, Field


class PriceReq(BaseModel):
    amount: float = Field(ge=0)
    reason: str = Field(default="", max_length=200)


class ShipReq(BaseModel):
    logistics_company: str = Field(alias="logisticsCompany", min_length=1, max_length=50)
    logistics_no: str = Field(alias="logisticsNo", min_length=1, max_length=100)

    class Config:
        populate_by_name = True


class BatchShipItem(BaseModel):
    order_id: int = Field(alias="orderId")
    logistics_company: str = Field(alias="logisticsCompany", min_length=1, max_length=50)
    logistics_no: str = Field(alias="logisticsNo", min_length=1, max_length=100)

    class Config:
        populate_by_name = True


class BatchShipReq(BaseModel):
    orders: list[BatchShipItem] = Field(min_length=1, max_length=200)


class AfterSaleAudit(BaseModel):
    agree: bool
    handle_note: str = Field(default="", max_length=500, alias="handleNote")

    class Config:
        populate_by_name = True


class ExpressSave(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    code: str = Field(min_length=1, max_length=30)
