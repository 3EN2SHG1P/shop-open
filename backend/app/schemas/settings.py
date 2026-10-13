from pydantic import BaseModel, Field


class ConfigSave(BaseModel):
    items: dict[str, str] = Field(default_factory=dict)


class FreightTemplateSave(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    type: int = Field(default=1, ge=1, le=3)
    is_free_shipping: int = Field(default=0, ge=0, le=1, alias="isFreeShipping")
    regions_json: str = Field(default="[]", alias="regionsJson")

    class Config:
        populate_by_name = True
