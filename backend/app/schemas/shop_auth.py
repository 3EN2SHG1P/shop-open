from pydantic import BaseModel, ConfigDict, Field


class SendCodeReq(BaseModel):
    phone: str = Field(min_length=11, max_length=11, pattern=r"^1\d{10}$")
    scene: str = Field(default="register", max_length=20)

    model_config = ConfigDict(populate_by_name=True)


class RegisterReq(BaseModel):
    phone: str = Field(min_length=11, max_length=11, pattern=r"^1\d{10}$")
    code: str = Field(min_length=1, max_length=10)
    password: str = Field(min_length=6, max_length=64)

    model_config = ConfigDict(populate_by_name=True)


class LoginReq(BaseModel):
    phone: str = Field(min_length=11, max_length=11, pattern=r"^1\d{10}$")
    password: str = Field(min_length=1, max_length=64)

    model_config = ConfigDict(populate_by_name=True)


class ProfileUpdateReq(BaseModel):
    nickname: str = Field(min_length=1, max_length=50)
    avatar: str = Field(default="", max_length=300)

    model_config = ConfigDict(populate_by_name=True)


class PasswordChangeReq(BaseModel):
    old_password: str = Field(alias="oldPassword", min_length=6, max_length=64)
    new_password: str = Field(alias="newPassword", min_length=6, max_length=64)

    model_config = ConfigDict(populate_by_name=True)
