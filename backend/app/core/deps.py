import time
from dataclasses import dataclass, field

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core import database
from core.errors import auth_failed, no_permission, not_logged_in
from core.security import decode_member_token, decode_token

_bearer = HTTPBearer(auto_error=False)
_permission_cache: dict[int, tuple[float, frozenset]] = {}
CACHE_TTL = 300


@dataclass
class AuthUser:
    id: int
    username: str
    real_name: str = ""
    dept_id: int | None = None
    roles: list = field(default_factory=list)
    role_keys: list = field(default_factory=list)
    data_scope: int = 3


def clear_permission_cache():
    _permission_cache.clear()


def invalidate_user(user_id: int):
    _permission_cache.pop(user_id, None)


def client_ip(request: Request) -> str:
    return request.client.host if request.client else ""


@dataclass
class AuthMember:
    id: int
    nickname: str
    phone: str = ""


async def get_current_member(request: Request, creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> AuthMember:
    if creds is None:
        not_logged_in()
    try:
        payload = decode_member_token(creds.credentials)
    except jwt.PyJWTError:
        auth_failed()
    member_id = int(payload.get("sub") or 0)
    row = await database.fetch_one(
        "SELECT id, nickname, phone, status FROM members WHERE id=%s", (member_id,)
    )
    if not row or row["status"] != 1:
        auth_failed()
    member = AuthMember(id=row["id"], nickname=row["nickname"] or "", phone=row["phone"] or "")
    request.state.member = member
    return member


async def get_current_user(request: Request, creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> AuthUser:
    if creds is None:
        not_logged_in()
    try:
        payload = decode_token(creds.credentials)
    except jwt.PyJWTError:
        auth_failed()
    user_id = int(payload.get("sub") or 0)
    row = await database.fetch_one(
        "SELECT id, username, real_name, dept_id, status FROM admin_users WHERE id=%s", (user_id,)
    )
    if not row or row["status"] != 1:
        auth_failed()
    roles = await database.fetch_all(
        "SELECT r.id, r.role_name, r.role_key, r.data_scope FROM roles r "
        "JOIN user_roles ur ON ur.role_id=r.id WHERE ur.user_id=%s AND r.status=1",
        (user_id,),
    )
    data_scope = max([r["data_scope"] for r in roles] or [1])
    user = AuthUser(
        id=row["id"],
        username=row["username"],
        real_name=row["real_name"] or "",
        dept_id=row["dept_id"],
        roles=list(roles),
        role_keys=[r["role_key"] for r in roles],
        data_scope=data_scope,
    )
    request.state.user = user
    return user


async def get_user_codes(user_id: int) -> frozenset:
    now = time.time()
    cached = _permission_cache.get(user_id)
    if cached and cached[0] > now:
        return cached[1]
    rows = await database.fetch_all(
        "SELECT DISTINCT p.code FROM permissions p "
        "JOIN role_permissions rp ON rp.permission_id=p.id "
        "JOIN user_roles ur ON ur.role_id=rp.role_id "
        "JOIN roles r ON r.id=ur.role_id "
        "WHERE ur.user_id=%s AND r.status=1 AND p.status=1 AND p.code IS NOT NULL AND p.code<>''",
        (user_id,),
    )
    codes = frozenset(r["code"] for r in rows)
    _permission_cache[user_id] = (now + CACHE_TTL, codes)
    return codes


def require_permission(code: str):
    async def checker(user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if code not in await get_user_codes(user.id):
            no_permission()
        return user

    return checker


async def dept_subtree_ids(dept_id: int | None) -> list[int]:
    if not dept_id:
        return []
    result: list[int] = []
    frontier = [dept_id]
    while frontier:
        placeholders = ",".join(["%s"] * len(frontier))
        rows = await database.fetch_all(
            f"SELECT id FROM dept WHERE parent_id IN ({placeholders}) AND status=1", tuple(frontier)
        )
        frontier = [r["id"] for r in rows]
        result.extend(frontier)
    return result


async def created_by_scope_condition(user: AuthUser, alias: str = "") -> tuple[str, list]:
    prefix = f"{alias}." if alias else ""
    if user.data_scope >= 3:
        return "", []
    if user.data_scope == 2:
        if user.dept_id:
            dept_ids = [user.dept_id] + await dept_subtree_ids(user.dept_id)
            placeholders = ",".join(["%s"] * len(dept_ids))
            admins = await database.fetch_all(
                f"SELECT id FROM admin_users WHERE dept_id IN ({placeholders})", tuple(dept_ids)
            )
        else:
            admins = []
        admin_ids = [a["id"] for a in admins] or [user.id]
        placeholders = ",".join(["%s"] * len(admin_ids))
        return f"{prefix}created_by IN ({placeholders})", admin_ids
    return f"{prefix}created_by = %s", [user.id]
