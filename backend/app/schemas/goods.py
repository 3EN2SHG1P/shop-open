from pydantic import BaseModel, Field


class CategorySave(BaseModel):
    parent_id: int = 0
    name: str = Field(min_length=1, max_length=50)
    icon: str = Field(default="", max_length=200)
    sort: int = 0
    is_show: int = 1
    seo_title: str = Field(default="", max_length=200)
    seo_keywords: str = Field(default="", max_length=200)
    seo_desc: str = Field(default="", max_length=500)


class BrandSave(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    logo: str = Field(default="", max_length=200)
    description: str = Field(default="", max_length=500)
    sort: int = 0


class SpecAttrValueIn(BaseModel):
    id: int | None = None
    value: str = Field(min_length=1, max_length=50)


class SpecAttrSave(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    category_id: int = 0
    sort: int = 0
    values: list[SpecAttrValueIn] = []


class ImageIn(BaseModel):
    url: str = Field(min_length=1, max_length=300)
    sort: int = 0
    type: int = 1


class SkuSpecValueIn(BaseModel):
    spec_id: int
    spec_value_id: int


class SkuIn(BaseModel):
    sku_code: str = Field(default="", max_length=100)
    price: float = 0.00
    stock: int = 0
    # 编辑页打开时的库存快照，用于乐观锁校验：
    # 提交时若数据库当前库存已不等于该值，说明期间产生了订单，拒绝覆盖以免超卖。
    # 不传则退化为直接覆盖（兼容新增等无需校验的场景）。
    original_stock: int | None = None
    image: str = Field(default="", max_length=200)
    spec_values: list[SkuSpecValueIn] = []


class GoodsSave(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    subtitle: str = Field(default="", max_length=300)
    category_id: int | None = None
    brand_id: int | None = None
    spu_code: str = Field(default="", max_length=50)
    unit: str = Field(default="件", max_length=20)
    market_price: float = 0.00
    price: float = 0.00
    cost_price: float = 0.00
    warn_stock: int = 0
    status: int = Field(default=1, ge=0, le=1)
    is_recommend: int = 0
    is_hot: int = 0
    is_new: int = 0
    detail_html: str = ""
    freight_template_id: int | None = None
    seo_title: str = Field(default="", max_length=200)
    seo_keywords: str = Field(default="", max_length=300)
    seo_desc: str = Field(default="", max_length=500)
    is_presale: int = 0
    presale_start: str | None = None
    presale_end: str | None = None
    buy_limit: int = 0
    points_discount_ratio: float = 0.00
    images: list[ImageIn] = []
    skus: list[SkuIn] = []


class BatchStatus(BaseModel):
    ids: list[int] = Field(min_length=1)
    status: int = Field(ge=0, le=1)


class BatchIds(BaseModel):
    ids: list[int] = Field(min_length=1)


class AuditReq(BaseModel):
    pass_flag: bool = Field(alias="pass")
    note: str = Field(default="", max_length=500)

    class Config:
        populate_by_name = True


class CommentReply(BaseModel):
    content: str = Field(min_length=1, max_length=500)


class CommentAudit(BaseModel):
    pass_flag: bool = Field(alias="pass")

    class Config:
        populate_by_name = True
