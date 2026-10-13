from pydantic import BaseModel, Field


class MemberProfileUpdate(BaseModel):
    nickname: str = Field(min_length=1, max_length=50)
    phone: str = Field(default="", max_length=20)
    email: str = Field(default="", max_length=100)
    level_id: int | None = Field(default=None, alias="levelId")

    class Config:
        populate_by_name = True


class MemberStatusUpdate(BaseModel):
    status: int = Field(ge=0, le=1)


class MemberResetPassword(BaseModel):
    password: str = Field(default="", min_length=6, max_length=72)


class LevelSave(BaseModel):
    level_name: str = Field(min_length=1, max_length=50, alias="levelName")
    upgrade_amount: float = Field(default=0, ge=0, le=99999999, alias="upgradeAmount")
    upgrade_points: int = Field(default=0, ge=0, le=100000000, alias="upgradePoints")
    discount_rate: float = Field(default=10.0, ge=0, le=10, alias="discountRate")
    benefits: str = Field(default="", max_length=500)
    status: int = Field(default=1, ge=0, le=1)

    class Config:
        populate_by_name = True


class PointsAdjust(BaseModel):
    member_id: int = Field(alias="memberId")
    change: int = Field(ge=-100000000, le=100000000)
    reason: str = Field(min_length=1, max_length=200)

    class Config:
        populate_by_name = True
