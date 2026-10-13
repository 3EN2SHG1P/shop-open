from core import audit, database
from core.config import config
from core.errors import account_locked, auth_failed, bad_request
from core.security import create_token, hash_password, verify_password
from datetime import timedelta

from core.timezone import now as _now, to_naive


async def _load_user_roles(user_id: int) -> list[dict]:
    return await database.fetch_all(
        "SELECT r.id, r.role_name, r.role_key, r.data_scope FROM roles r "
        "JOIN user_roles ur ON ur.role_id = r.id WHERE ur.user_id = %s AND r.status = 1",
        (user_id,),
    )


async def login(username: str, password: str, ip: str, user_agent: str) -> dict:
    row = await database.fetch_one("SELECT * FROM admin_users WHERE username = %s", (username,))
    if not row or row["status"] != 1:
        await audit.log_login(0, ip, user_agent, 0, username)
        auth_failed("用户名或密码错误")
    if row["locked_until"] and row["locked_until"] > to_naive(_now()):
        account_locked()
    if not verify_password(password, row["password_hash"]):
        fails = (row["login_fail_count"] or 0) + 1
        locked = None
        if fails >= config.login_fail_limit:
            locked = to_naive(_now() + timedelta(minutes=config.login_fail_lock_minutes))
            fails = 0
        await database.execute(
            "UPDATE admin_users SET login_fail_count = %s, locked_until = %s WHERE id = %s",
            (fails, locked, row["id"]),
        )
        await audit.log_login(row["id"], ip, user_agent, 0, username)
        auth_failed("用户名或密码错误")
    await database.execute(
        "UPDATE admin_users SET login_fail_count = 0, locked_until = NULL, "
        "last_login_time = %s, last_login_ip = %s WHERE id = %s",
        (to_naive(_now()), ip, row["id"]),
    )
    await audit.log_login(row["id"], ip, user_agent, 1, username)
    roles = await _load_user_roles(row["id"])
    await audit.log_action(row["id"], "auth", audit.ACTION_LOGIN, "login", f"用户 {username} 登录系统", ip)
    return {
        "token": create_token(row["id"], row["username"], [r["role_key"] for r in roles]),
        "user": {
            "id": row["id"],
            "username": row["username"],
            "realName": row["real_name"] or "",
            "roles": [{"id": r["id"], "roleName": r["role_name"], "roleKey": r["role_key"]} for r in roles],
        },
    }


async def logout(user, ip: str) -> None:
    await audit.log_action(user.id, "auth", audit.ACTION_LOGOUT, "logout", f"用户 {user.username} 退出系统", ip)


async def me(user_id: int) -> dict:
    row = await database.fetch_one(
        "SELECT id, username, real_name, phone, email, dept_id, status, last_login_time, created_at "
        "FROM admin_users WHERE id = %s",
        (user_id,),
    )
    if not row:
        auth_failed()
    from core.deps import get_user_codes

    codes = await get_user_codes(user_id)
    roles = await _load_user_roles(user_id)
    return {
        "id": row["id"],
        "username": row["username"],
        "realName": row["real_name"] or "",
        "phone": row["phone"],
        "email": row["email"],
        "deptId": row["dept_id"],
        "dataScope": max([r["data_scope"] for r in roles] or [1]),
        "roles": [{"id": r["id"], "roleName": r["role_name"], "roleKey": r["role_key"]} for r in roles],
        "permissions": sorted(codes),
    }


async def change_password(user_id: int, old_password: str, new_password: str) -> None:
    row = await database.fetch_one("SELECT password_hash FROM admin_users WHERE id = %s", (user_id,))
    if not row or not verify_password(old_password, row["password_hash"]):
        bad_request("原密码错误")
    await database.execute("UPDATE admin_users SET password_hash = %s WHERE id = %s", (hash_password(new_password), user_id))
    await audit.log_action(user_id, "auth", audit.ACTION_EDIT, "password", "修改登录密码")
