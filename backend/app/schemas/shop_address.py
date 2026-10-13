from pydantic import BaseModel, ConfigDict, Field


class AddressSaveReq(BaseModel):
    receiver_name: str = Field(alias="receiverName", min_length=1, max_length=50)
    receiver_phone: str = Field(alias="receiverPhone", min_length=11, max_length=20)
    province: str = Field(default="", max_length=50)
    city: str = Field(default="", max_length=50)
    district: str = Field(default="", max_length=50)
    detail: str = Field(min_length=1, max_length=200)
    is_default: int | bool = Field(default=0, alias="isDefault")

    model_config = ConfigDict(populate_by_name=True)


class AddressDefaultReq(BaseModel):
    is_default: int | bool = Field(alias="isDefault", default=1)

    model_config = ConfigDict(populate_by_name=True)
