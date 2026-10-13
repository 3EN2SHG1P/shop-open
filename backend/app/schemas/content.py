from pydantic import BaseModel, Field


class ArticleCategorySave(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    sort: int = Field(default=0, ge=0, le=9999)
    status: int = Field(default=1, ge=0, le=1)

    class Config:
        populate_by_name = True


class ArticleSave(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    category_id: int | None = Field(default=None, ge=1, alias="categoryId")
    author: str = Field(default="", max_length=50)
    cover: str = Field(default="", max_length=300)
    summary: str = Field(default="", max_length=500)
    content: str = Field(default="")
    seo_title: str = Field(default="", max_length=200, alias="seoTitle")
    seo_keywords: str = Field(default="", max_length=300, alias="seoKeywords")
    seo_desc: str = Field(default="", max_length=500, alias="seoDesc")
    status: int = Field(default=0, ge=0, le=1)
    publish_time: str | None = Field(default=None, max_length=30, alias="publishTime")

    class Config:
        populate_by_name = True


class AdPositionSave(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    size: str = Field(default="", max_length=50)
    status: int = Field(default=1, ge=0, le=1)

    class Config:
        populate_by_name = True


class AdSave(BaseModel):
    position_id: int = Field(ge=1, alias="positionId")
    type: int = Field(default=1, ge=1, le=3)
    image: str = Field(default="", max_length=300)
    video: str = Field(default="", max_length=300)
    link: str = Field(default="", max_length=300)
    text: str = Field(default="", max_length=200)
    sort: int = Field(default=0, ge=0, le=9999)
    start_time: str | None = Field(default=None, max_length=30, alias="startTime")
    end_time: str | None = Field(default=None, max_length=30, alias="endTime")
    status: int = Field(default=1, ge=0, le=1)

    class Config:
        populate_by_name = True


class NoticeSave(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(default="")
    target: int = Field(default=0, ge=0, le=1)
    target_level_id: int | None = Field(default=None, ge=1, alias="targetLevelId")
    publish_time: str | None = Field(default=None, max_length=30, alias="publishTime")
    status: int = Field(default=0, ge=0, le=1)

    class Config:
        populate_by_name = True
