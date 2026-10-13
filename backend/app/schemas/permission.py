from pydantic import BaseModel, Field


class AdminCreate(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    password: str = Field(min_length=6, max_length=72)
    real_name: str = Field(default="", max_length=50)
    phone: str = Field(default="", max_length=20)
    email: str = Field(default="", max_length=100)
    dept_id: int | None = None
    status: int = 1
    # None = 不分配角色。建号与授权分离：普通管理员可建号，但无权直接授予角色
    role_ids: list[int] | None = None


class AdminResetPassword(BaseModel):
    new_password: str = Field(min_length=6, max_length=72)


class AdminUpdate(BaseModel):
    real_name: str = Field(default="", max_length=50)
    phone: str = Field(default="", max_length=20)
    email: str = Field(default="", max_length=100)
    dept_id: int | None = None
    status: int = 1
    # None = 本次不修改角色（区别于「传空数组 = 清空角色」）。
    # 这样即使前端漏传该字段，也不会把管理员的角色静默清掉。
    role_ids: list[int] | None = None


class RoleSave(BaseModel):
    role_name: str = Field(min_length=1, max_length=50)
    role_key: str = Field(min_length=1, max_length=50)
    description: str = Field(default="", max_length=255)
    # 默认取最小范围：漏传时不会意外获得全量数据权限（角色写操作已收紧到超管）
    data_scope: int = Field(default=1, ge=1, le=3)
    status: int = 1
    # None = 本次不修改权限；传空数组 = 清空该角色的全部权限
    permission_ids: list[int] | None = None


class ResourceSave(BaseModel):
    parent_id: int = 0
    permission_type: str = Field(default="menu", pattern="^(menu|button|api|data)$")
    name: str = Field(min_length=1, max_length=50)
    code: str = Field(default="", max_length=100)
    path: str = Field(default="", max_length=200)
    method: str = Field(default="", max_length=10)
    icon: str = Field(default="", max_length=100)
    sort: int = 0
    status: int = 1


class DeptSave(BaseModel):
    parent_id: int = 0
    dept_name: str = Field(min_length=1, max_length=50)
    sort: int = 0
    status: int = 1
