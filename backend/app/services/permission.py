from core import audit, database
from core.common import build_tree, row_to_camel
from core.deps import AuthUser, clear_permission_cache, dept_subtree_ids, invalidate_user
from core.errors import auth_failed, duplicate, no_permission, referenced, state_error
from core.security import hash_password
from schemas.permission import AdminCreate, AdminUpdate, DeptSave, ResourceSave, RoleSave


async def _admin_scope_condition(user: AuthUser) -> tuple[str, list]:
    """管理员账号列表的数据权限条件：3=全部、2=本部门及子部门、1=仅本人。

    admin_users 表没有 created_by 字段，因此按 dept_id / id 维度收敛，
    避免持有 permission:list 但 data_scope 受限的账号通过 dept_id 参数跨部门查看。
    """
    if user.data_scope >= 3:
        return "", []
    if user.data_scope == 2 and user.dept_id:
        dept_ids = [user.dept_id] + await dept_subtree_ids(user.dept_id)
        placeholders = ",".join(["%s"] * len(dept_ids))
        return f"dept_id IN ({placeholders})", dept_ids
    return "id = %s", [user.id]


def _build_where(filters: dict) -> tuple[str, list]:
    where = ["1=1"]
    params: list = []
    keyword = filters.get("keyword")
    if keyword:
        where.append("(username LIKE %s OR real_name LIKE %s)")
        params += [f"%{keyword}%", f"%{keyword}%"]
    for col in ("status", "dept_id"):
        val = filters.get(col)
        if val is not None:
            where.append(f"{col} = %s")
            params.append(val)
    return " AND ".join(where), params


async def list_admins(page: int, page_size: int, filters: dict, user: AuthUser | None = None) -> dict:
    where, params = _build_where(filters)
    if user is not None:
        scope_sql, scope_params = await _admin_scope_condition(user)
        if scope_sql:
            where += " AND " + scope_sql
            params = params + scope_params
    total = await database.fetch_one(f"SELECT COUNT(*) AS c FROM admin_users WHERE {where}", params)
    rows = await database.fetch_all(
        f"SELECT id, username, real_name, phone, email, dept_id, status, last_login_ip, last_login_time, created_at "
        f"FROM admin_users WHERE {where} ORDER BY id DESC LIMIT %s OFFSET %s",
        params + [page_size, (page - 1) * page_size],
    )
    users = {r["id"]: r for r in rows}
    if users:
        ids = list(users)
        ph = ",".join(["%s"] * len(ids))
        roles = await database.fetch_all(
            f"SELECT ur.user_id, r.id AS role_id, r.role_name, r.role_key FROM user_roles ur "
            f"JOIN roles r ON r.id = ur.role_id WHERE ur.user_id IN ({ph})",
            ids,
        )
        for rel in roles:
            u = users[rel["user_id"]]
            u.setdefault("role_ids", []).append(rel["role_id"])
            u.setdefault("role_names", []).append(rel["role_name"])
        for u in users.values():
            u["role_ids"] = u.get("role_ids", [])
            u["role_names"] = u.get("role_names", [])
    list_rows = []
    for r in rows:
        camel = row_to_camel({k: v for k, v in r.items() if k != "created_by"})
        camel["roleIds"] = r.get("role_ids", [])
        camel["roleNames"] = r.get("role_names", [])
        camel["createdAt"] = camel.pop("createdAt", None)
        list_rows.append(camel)
    return {"list": list_rows, "total": total["c"], "page": page, "page_size": page_size}


async def get_admin(admin_id: int, user: AuthUser | None = None) -> dict:
    """读取单个管理员。

    必须套用与列表一致的数据权限：曾经这里只按 id 查，导致任何持 permission:list 的
    低权限管理员都能遍历 /admins/{id} 读走全部管理员明细，列表限权形同虚设。
    """
    sql = "SELECT * FROM admin_users WHERE id = %s"
    params: list = [admin_id]
    if user is not None:
        scope_sql, scope_params = await _admin_scope_condition(user)
        if scope_sql:
            sql += f" AND {scope_sql}"
            params += scope_params
    row = await database.fetch_one(sql, params)
    if not row:
        # 越权与不存在返回同一文案，避免借此枚举管理员 id
        auth_failed("管理员不存在")
    rels = await database.fetch_all("SELECT role_id FROM user_roles WHERE user_id = %s", (admin_id,))
    row["role_ids"] = [r["role_id"] for r in rels]
    camel = row_to_camel(row)
    camel.pop("passwordHash", None)
    camel["roleIds"] = row["role_ids"]
    return camel


async def create_admin(body: AdminCreate, operator_id: int) -> int:
    existed = await database.fetch_one("SELECT id FROM admin_users WHERE username = %s", (body.username,))
    if existed:
        duplicate("登录账号已存在")
    admin_id = await database.execute_return_id(
        "INSERT INTO admin_users (username, password_hash, real_name, phone, email, dept_id, status) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (body.username, hash_password(body.password), body.real_name, body.phone, body.email, body.dept_id, body.status),
    )
    if body.role_ids:
        for rid in set(body.role_ids):
            await database.execute("INSERT IGNORE INTO user_roles (user_id, role_id) VALUES (%s,%s)", (admin_id, rid))
    await audit.log_action(operator_id, "permission", audit.ACTION_ADD, f"admin:{body.username}", "新增管理员")
    return admin_id


async def update_admin(admin_id: int, body: AdminUpdate, operator_id: int) -> None:
    row = await database.fetch_one("SELECT id, username FROM admin_users WHERE id = %s", (admin_id,))
    if not row:
        auth_failed("管理员不存在")
    async with database.transaction() as cur:
        await cur.execute(
            "UPDATE admin_users SET real_name=%s, phone=%s, email=%s, dept_id=%s, status=%s WHERE id=%s",
            (body.real_name, body.phone, body.email, body.dept_id, body.status, admin_id),
        )
        # role_ids 为 None 表示本次不动角色：避免前端漏传字段时被静默清空
        if body.role_ids is not None:
            # 先删后插必须放在同一事务里，中途失败会让该管理员角色被清空
            await cur.execute("DELETE FROM user_roles WHERE user_id = %s", (admin_id,))
            for rid in set(body.role_ids):
                await cur.execute("INSERT IGNORE INTO user_roles (user_id, role_id) VALUES (%s,%s)", (admin_id, rid))
    await audit.log_action(operator_id, "permission", audit.ACTION_EDIT, f"admin:{row['username']}", "编辑管理员")
    invalidate_user(admin_id)


async def set_admin_status(admin_id: int, status: int, operator_id: int) -> None:
    row = await database.fetch_one("SELECT id, username FROM admin_users WHERE id = %s", (admin_id,))
    if not row:
        auth_failed("管理员不存在")
    if admin_id == operator_id and status == 0:
        state_error("不能禁用当前登录账号")
    await database.execute("UPDATE admin_users SET status = %s WHERE id = %s", (status, admin_id))
    await audit.log_action(operator_id, "permission", audit.ACTION_EDIT, f"admin:{row['username']}", "启禁用管理员")
    invalidate_user(admin_id)


async def reset_admin_password(admin_id: int, new_password: str, operator_id: int) -> None:
    row = await database.fetch_one("SELECT id, username FROM admin_users WHERE id = %s", (admin_id,))
    if not row:
        auth_failed("管理员不存在")
    await database.execute("UPDATE admin_users SET password_hash = %s WHERE id = %s", (hash_password(new_password), admin_id))
    await audit.log_action(operator_id, "permission", audit.ACTION_EDIT, f"admin:{row['username']}", "重置密码")
    invalidate_user(admin_id)


async def delete_admin(admin_id: int, operator_id: int) -> None:
    if admin_id == operator_id:
        state_error("不能删除当前登录账号")
    row = await database.fetch_one("SELECT id, username FROM admin_users WHERE id = %s", (admin_id,))
    if not row:
        auth_failed("管理员不存在")
    await database.execute("DELETE FROM user_roles WHERE user_id = %s", (admin_id,))
    await database.execute("DELETE FROM admin_users WHERE id = %s", (admin_id,))
    await audit.log_action(operator_id, "permission", audit.ACTION_DELETE, f"admin:{row['username']}", "删除管理员")
    invalidate_user(admin_id)


async def list_roles(keyword: str = "") -> list[dict]:
    where = "1=1"
    params: list = []
    if keyword:
        where += " AND (role_name LIKE %s OR role_key LIKE %s)"
        params += [f"%{keyword}%", f"%{keyword}%"]
    rows = await database.fetch_all(
        f"SELECT r.id, r.role_name, r.role_key, r.description, r.data_scope, r.status, r.created_at, "
        f"(SELECT COUNT(*) FROM user_roles ur WHERE ur.role_id = r.id) AS user_count "
        f"FROM roles r WHERE {where} ORDER BY r.id ASC",
        params,
    )
    roles = [dict(r) for r in rows]
    if roles:
        ids = [r["id"] for r in roles]
        ph = ",".join(["%s"] * len(ids))
        rels = await database.fetch_all(
            f"SELECT role_id, permission_id FROM role_permissions WHERE role_id IN ({ph})", ids
        )
        grouped: dict[int, list] = {}
        for rel in rels:
            grouped.setdefault(rel["role_id"], []).append(rel["permission_id"])
        for r in roles:
            r["permissionIds"] = grouped.get(r["id"], [])
            r["dataScope"] = r.pop("data_scope")
            r["createdAt"] = r.pop("created_at")
            r["userCount"] = r.pop("user_count")
            r["roleName"] = r.pop("role_name")
            r["roleKey"] = r.pop("role_key")
    return roles


async def create_role(body: RoleSave, operator_id: int) -> int:
    existed = await database.fetch_one("SELECT id FROM roles WHERE role_key = %s", (body.role_key,))
    if existed:
        duplicate("角色标识已存在")
    rid = await database.execute_return_id(
        "INSERT INTO roles (role_name, role_key, description, data_scope, status) VALUES (%s,%s,%s,%s,%s)",
        (body.role_name, body.role_key, body.description, body.data_scope, body.status),
    )
    if body.permission_ids:
        for pid in set(body.permission_ids):
            await database.execute("INSERT IGNORE INTO role_permissions (role_id, permission_id) VALUES (%s,%s)", (rid, pid))
    await audit.log_action(operator_id, "permission", audit.ACTION_ADD, f"role:{body.role_name}", "新增角色")
    clear_permission_cache()
    return rid


async def update_role(role_id: int, body: RoleSave, operator_id: int) -> None:
    row = await database.fetch_one("SELECT id, role_name FROM roles WHERE id = %s", (role_id,))
    if not row:
        auth_failed("角色不存在")
    conflict = await database.fetch_one("SELECT id FROM roles WHERE role_key = %s AND id <> %s", (body.role_key, role_id))
    if conflict:
        duplicate("角色标识已存在")
    await database.execute(
        "UPDATE roles SET role_name=%s, role_key=%s, description=%s, data_scope=%s, status=%s WHERE id=%s",
        (body.role_name, body.role_key, body.description, body.data_scope, body.status, role_id),
    )
    # None = 本次不动权限，避免前端漏传字段时把角色权限静默清空
    if body.permission_ids is not None:
        await database.execute("DELETE FROM role_permissions WHERE role_id = %s", (role_id,))
        for pid in set(body.permission_ids):
            await database.execute("INSERT IGNORE INTO role_permissions (role_id, permission_id) VALUES (%s,%s)", (role_id, pid))
    await audit.log_action(operator_id, "permission", audit.ACTION_EDIT, f"role:{row['role_name']}", "编辑角色/分配权限")
    clear_permission_cache()


async def copy_role(role_id: int, operator_id: int) -> int:
    src = await database.fetch_one("SELECT * FROM roles WHERE id = %s", (role_id,))
    if not src:
        auth_failed("角色不存在")
    existed = await database.fetch_one("SELECT id FROM roles WHERE role_key = %s", (src["role_key"] + "_copy",))
    if existed:
        duplicate("复制角色标识已存在")
    rid = await database.execute_return_id(
        "INSERT INTO roles (role_name, role_key, description, data_scope, status) VALUES (%s,%s,%s,%s,%s)",
        (src["role_name"] + "-副本", src["role_key"] + "_copy", src["description"], src["data_scope"], src["status"]),
    )
    rels = await database.fetch_all("SELECT permission_id FROM role_permissions WHERE role_id = %s", (role_id,))
    for rel in rels:
        await database.execute("INSERT IGNORE INTO role_permissions (role_id, permission_id) VALUES (%s,%s)", (rid, rel["permission_id"]))
    await audit.log_action(operator_id, "permission", audit.ACTION_ADD, f"role:{src['role_name']}", "复制角色")
    clear_permission_cache()
    return rid


async def delete_role(role_id: int, operator_id: int) -> None:
    row = await database.fetch_one("SELECT id, role_name FROM roles WHERE id = %s", (role_id,))
    if not row:
        auth_failed("角色不存在")
    cnt = await database.fetch_one("SELECT COUNT(*) AS c FROM user_roles WHERE role_id = %s", (role_id,))
    if cnt and cnt["c"]:
        referenced("角色已被管理员引用，不可删除")
    await database.execute("DELETE FROM role_permissions WHERE role_id = %s", (role_id,))
    await database.execute("DELETE FROM roles WHERE id = %s", (role_id,))
    await audit.log_action(operator_id, "permission", audit.ACTION_DELETE, f"role:{row['role_name']}", "删除角色")
    clear_permission_cache()


async def permission_tree() -> list[dict]:
    rows = await database.fetch_all(
        "SELECT id, parent_id, permission_type, name, code, path, method, icon, sort, status, created_at "
        "FROM permissions ORDER BY sort ASC, id ASC"
    )
    for r in rows:
        r["permissionType"] = r.pop("permission_type")
        r["createdAt"] = r.pop("created_at")
    return build_tree(rows)


async def create_resource(body: ResourceSave, operator_id: int) -> int:
    if body.code:
        existed = await database.fetch_one("SELECT id FROM permissions WHERE code = %s", (body.code,))
        if existed:
            duplicate("权限标识已存在")
    if body.parent_id:
        parent = await database.fetch_one("SELECT id FROM permissions WHERE id = %s", (body.parent_id,))
        if not parent:
            auth_failed("父节点不存在")
    rid = await database.execute_return_id(
        "INSERT INTO permissions (parent_id, permission_type, name, code, path, method, icon, sort, status) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (body.parent_id, body.permission_type, body.name, body.code or None, body.path or None,
         body.method.upper() if body.method else None, body.icon or None, body.sort, body.status),
    )
    await audit.log_action(operator_id, "permission", audit.ACTION_ADD, f"resource:{body.name}", "新增权限资源")
    clear_permission_cache()
    return rid


async def update_resource(res_id: int, body: ResourceSave, operator_id: int) -> None:
    row = await database.fetch_one("SELECT id, name FROM permissions WHERE id = %s", (res_id,))
    if not row:
        auth_failed("权限资源不存在")
    if body.code:
        conflict = await database.fetch_one("SELECT id FROM permissions WHERE code = %s AND id <> %s", (body.code, res_id))
        if conflict:
            duplicate("权限标识已存在")
    await database.execute(
        "UPDATE permissions SET parent_id=%s, permission_type=%s, name=%s, code=%s, path=%s, method=%s, "
        "icon=%s, sort=%s, status=%s WHERE id=%s",
        (body.parent_id, body.permission_type, body.name, body.code or None, body.path or None,
         body.method.upper() if body.method else None, body.icon or None, body.sort, body.status, res_id),
    )
    await audit.log_action(operator_id, "permission", audit.ACTION_EDIT, f"resource:{row['name']}", "编辑权限资源")
    clear_permission_cache()


async def delete_resource(res_id: int, operator_id: int) -> None:
    row = await database.fetch_one("SELECT id, name FROM permissions WHERE id = %s", (res_id,))
    if not row:
        auth_failed("权限资源不存在")
    child = await database.fetch_one("SELECT id FROM permissions WHERE parent_id = %s LIMIT 1", (res_id,))
    if child:
        referenced("存在子节点，不可删除")
    cnt = await database.fetch_one("SELECT COUNT(*) AS c FROM role_permissions WHERE permission_id = %s", (res_id,))
    if cnt and cnt["c"]:
        referenced("权限已被角色引用，不可删除")
    await database.execute("DELETE FROM permissions WHERE id = %s", (res_id,))
    await audit.log_action(operator_id, "permission", audit.ACTION_DELETE, f"resource:{row['name']}", "删除权限资源")
    clear_permission_cache()


async def dept_tree() -> list[dict]:
    rows = await database.fetch_all(
        "SELECT id, parent_id, dept_name, sort, status, created_at FROM dept ORDER BY sort ASC, id ASC"
    )
    for r in rows:
        r["deptName"] = r.pop("dept_name")
        r["createdAt"] = r.pop("created_at")
    return build_tree(rows)


async def create_dept(body: DeptSave, operator_id: int) -> int:
    did = await database.execute_return_id(
        "INSERT INTO dept (parent_id, dept_name, sort, status) VALUES (%s,%s,%s,%s)",
        (body.parent_id, body.dept_name, body.sort, body.status),
    )
    await audit.log_action(operator_id, "permission", audit.ACTION_ADD, f"dept:{body.dept_name}", "新增部门")
    return did


async def update_dept(dept_id: int, body: DeptSave, operator_id: int) -> None:
    row = await database.fetch_one("SELECT id, dept_name FROM dept WHERE id = %s", (dept_id,))
    if not row:
        auth_failed("部门不存在")
    await database.execute(
        "UPDATE dept SET parent_id=%s, dept_name=%s, sort=%s, status=%s WHERE id=%s",
        (body.parent_id, body.dept_name, body.sort, body.status, dept_id),
    )
    await audit.log_action(operator_id, "permission", audit.ACTION_EDIT, f"dept:{row['dept_name']}", "编辑部门")


async def delete_dept(dept_id: int, operator_id: int) -> None:
    row = await database.fetch_one("SELECT id, dept_name FROM dept WHERE id = %s", (dept_id,))
    if not row:
        auth_failed("部门不存在")
    child = await database.fetch_one("SELECT id FROM dept WHERE parent_id = %s LIMIT 1", (dept_id,))
    if child:
        referenced("存在子部门，不可删除")
    user = await database.fetch_one("SELECT id FROM admin_users WHERE dept_id = %s LIMIT 1", (dept_id,))
    if user:
        referenced("部门下存在管理员，不可删除")
    await database.execute("DELETE FROM dept WHERE id = %s", (dept_id,))
    await audit.log_action(operator_id, "permission", audit.ACTION_DELETE, f"dept:{row['dept_name']}", "删除部门")


async def list_login_logs(page: int, page_size: int, filters: dict) -> dict:
    where = "1=1"
    params: list = []
    keyword = filters.get("keyword")
    if keyword:
        where += " AND username LIKE %s"
        params.append(f"%{keyword}%")
    success = filters.get("success")
    if success is not None:
        where += " AND success = %s"
        params.append(success)
    if filters.get("start_time"):
        where += " AND created_at >= %s"
        params.append(filters["start_time"])
    if filters.get("end_time"):
        where += " AND created_at <= %s"
        params.append(filters["end_time"])
    total = await database.fetch_one(f"SELECT COUNT(*) AS c FROM admin_login_logs WHERE {where}", params)
    rows = await database.fetch_all(
        f"SELECT id, admin_id, username, ip, user_agent, success, created_at FROM admin_login_logs "
        f"WHERE {where} ORDER BY id DESC LIMIT %s OFFSET %s",
        params + [page_size, (page - 1) * page_size],
    )
    list_rows = []
    for r in rows:
        camel = row_to_camel(r)
        camel["createdAt"] = camel.pop("createdAt", None)
        list_rows.append(camel)
    return {"list": list_rows, "total": total["c"], "page": page, "page_size": page_size}


async def check_own_admin(admin_id: int, operator: object) -> None:
    if admin_id != operator.id and operator.data_scope < 3:
        no_permission("无数据权限")


def require_super_admin(operator) -> None:
    """角色与权限资源是整个系统的授权载体，写操作一律收紧到超管。

    注意判据不能用「本次有没有传 permission_ids」：RoleSave.data_scope 默认 3，
    而 update_role 会无条件把 data_scope 写回——只要省略字段就能把自己的角色
    抬成超管级，进而绕过所有闸门。所以这里无条件校验操作者身份。
    """
    if operator.data_scope < 3:
        no_permission("只有超级管理员可以修改角色与权限资源")


def strip_role_ids(body, operator) -> None:
    """普通管理员提交的 role_ids 一律丢弃（而不是 403）。

    背景是一条提权链路：check_own_admin 允许管理员改自己的资料，而更新时会把
    role_ids 全量覆盖写回，于是改资料时顺带提交 [超管角色] 就能提权。

    这里选择「丢弃」而非「拒绝」，是因为管理端编辑管理员的表单总会带上
    role_ids（哪怕一个角色都没勾）——按「传了就 403」处理的话，普通管理员
    连修改自己的手机号都会被拒，与 check_own_admin 的设计意图冲突。
    丢弃后：资料照常更新，但任何人的角色都不会被改动。
    回归用例见 tests/test_privilege_escalation.py。
    """
    if operator.data_scope < 3:
        body.role_ids = None
