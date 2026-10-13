from fastapi import APIRouter, Depends, Query

from core.deps import get_current_user, require_permission
from core.response import ok
from schemas.permission import AdminCreate, AdminResetPassword, AdminUpdate, DeptSave, ResourceSave, RoleSave
from services import permission as svc

router = APIRouter(prefix="/api/v1/permission", tags=["permission"])

P = require_permission


@router.get("/admins")
async def list_admins(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str = "",
    status: int | None = None,
    dept_id: int | None = None,
    user=Depends(P("permission:list")),
):
    filters = {"keyword": keyword, "status": status, "dept_id": dept_id}
    return ok(await svc.list_admins(page, page_size, filters, user))


@router.get("/admins/{admin_id}")
async def get_admin(admin_id: int, user=Depends(P("permission:list"))):
    return ok(await svc.get_admin(admin_id, user))


@router.post("/admins")
async def create_admin(body: AdminCreate, user=Depends(P("permission:add"))):
    # 建号与授权分离：普通管理员可以建号，但附带的 role_ids 会被丢弃，须由超管另行授权
    svc.strip_role_ids(body, user)
    return ok({"id": await svc.create_admin(body, user.id)})


@router.put("/admins/{admin_id}")
async def update_admin(admin_id: int, body: AdminUpdate, user=Depends(P("permission:edit"))):
    await svc.check_own_admin(admin_id, user)
    # 普通管理员改自己资料时携带的 role_ids 会被丢弃，堵住「改资料顺手给自己挂超管角色」
    svc.strip_role_ids(body, user)
    await svc.update_admin(admin_id, body, user.id)
    return ok()


@router.put("/admins/{admin_id}/status")
async def set_admin_status(admin_id: int, status: int = Query(..., ge=0, le=1), user=Depends(P("permission:edit"))):
    await svc.check_own_admin(admin_id, user)
    await svc.set_admin_status(admin_id, status, user.id)
    return ok()


@router.put("/admins/{admin_id}/reset-password")
async def reset_admin_password(
    admin_id: int,
    body: AdminResetPassword,
    user=Depends(P("permission:edit")),
):
    # 非超管（data_scope<3）不得重置他人密码，否则可越权改超管口令提权
    await svc.check_own_admin(admin_id, user)
    await svc.reset_admin_password(admin_id, body.new_password, user.id)
    return ok()


@router.delete("/admins/{admin_id}")
async def delete_admin(admin_id: int, user=Depends(P("permission:delete"))):
    await svc.check_own_admin(admin_id, user)
    await svc.delete_admin(admin_id, user.id)
    return ok()


@router.get("/roles")
async def list_roles(keyword: str = "", _user=Depends(P("permission:list"))):
    return ok(await svc.list_roles(keyword))


@router.post("/roles")
async def create_role(body: RoleSave, user=Depends(P("permission:add"))):
    # 角色即权限集合（含 data_scope，默认就是超管级），只有超管能新建
    svc.require_super_admin(user)
    return ok({"id": await svc.create_role(body, user.id)})


@router.put("/roles/{role_id}")
async def update_role(role_id: int, body: RoleSave, user=Depends(P("permission:edit"))):
    # 改角色 = 改权限体系（data_scope 与 permission_ids 都会被写回），只有超管能操作
    svc.require_super_admin(user)
    await svc.update_role(role_id, body, user.id)
    return ok()


@router.post("/roles/{role_id}/copy")
async def copy_role(role_id: int, user=Depends(P("permission:add"))):
    # 复制角色等价于克隆一份权限，同样只有超管能操作
    svc.require_super_admin(user)
    return ok({"id": await svc.copy_role(role_id, user.id)})


@router.delete("/roles/{role_id}")
async def delete_role(role_id: int, user=Depends(P("permission:delete"))):
    svc.require_super_admin(user)
    await svc.delete_role(role_id, user.id)
    return ok()


@router.get("/tree")
async def permission_tree(_user=Depends(P("permission:list"))):
    return ok(await svc.permission_tree())


@router.post("/resources")
async def create_resource(body: ResourceSave, user=Depends(P("permission:add"))):
    # 权限资源的 code 会被实时读进鉴权白名单，改它就等于改权限定义
    svc.require_super_admin(user)
    return ok({"id": await svc.create_resource(body, user.id)})


@router.put("/resources/{res_id}")
async def update_resource(res_id: int, body: ResourceSave, user=Depends(P("permission:edit"))):
    # 同上：把某条资源的 code 改成别的权限码，即可绕过授权直接获得该权限
    svc.require_super_admin(user)
    await svc.update_resource(res_id, body, user.id)
    return ok()


@router.delete("/resources/{res_id}")
async def delete_resource(res_id: int, user=Depends(P("permission:delete"))):
    svc.require_super_admin(user)
    await svc.delete_resource(res_id, user.id)
    return ok()


@router.get("/depts")
async def dept_tree(_user=Depends(P("permission:list"))):
    return ok(await svc.dept_tree())


@router.post("/depts")
async def create_dept(body: DeptSave, user=Depends(P("permission:add"))):
    return ok({"id": await svc.create_dept(body, user.id)})


@router.put("/depts/{dept_id}")
async def update_dept(dept_id: int, body: DeptSave, user=Depends(P("permission:edit"))):
    await svc.update_dept(dept_id, body, user.id)
    return ok()


@router.delete("/depts/{dept_id}")
async def delete_dept(dept_id: int, user=Depends(P("permission:delete"))):
    await svc.delete_dept(dept_id, user.id)
    return ok()


@router.get("/login-logs")
async def login_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str = "",
    success: int | None = None,
    start_time: str = "",
    end_time: str = "",
    _user=Depends(P("permission:list")),
):
    filters = {"keyword": keyword, "success": success, "start_time": start_time, "end_time": end_time}
    return ok(await svc.list_login_logs(page, page_size, filters))
