import datetime
from typing import Any

import bcrypt
import jwt

from core.config import config
from core.errors import bad_request


# bcrypt 只取前 72 字节，超长部分会被静默丢弃；这里显式拒绝，避免"改了但没完全改"
# 注意 72 是**字节**数，中文密码按 UTF-8 计 3 字节/字
MAX_PASSWORD_BYTES = 72


def hash_password(raw: str) -> str:
    if len(raw.encode("utf-8")) > MAX_PASSWORD_BYTES:
        bad_request(f"密码过长：最多 {MAX_PASSWORD_BYTES} 字节（约 {MAX_PASSWORD_BYTES // 3} 个汉字）")
    return bcrypt.hashpw(raw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(raw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(raw.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def hash_code(raw: str) -> str:
    """验证码也要哈希存储，不允许明文/可比对的固定值落库。

    复用密码哈希：验证码本质是短口令，一旦明文存储，任何能读库的人（或一次日志泄漏）
    就能直接接管任意手机号。
    """
    return bcrypt.hashpw(raw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_code(raw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(raw.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def random_code(length: int = 6) -> str:
    """生成随机数字验证码。必须用 secrets 而非 random：
    random 是梅森旋转，观测少量输出即可预测后续。"""
    import secrets

    return "".join(str(secrets.randbelow(10)) for _ in range(length))


def create_token(user_id: int, username: str, role_keys: list[str]) -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "sub": str(user_id),
        "username": username,
        "role_keys": role_keys,
        "typ": "admin",
        "iat": now,
        "exp": now + datetime.timedelta(minutes=config.jwt_expire_minutes),
    }
    return jwt.encode(payload, config.jwt_secret, algorithm=config.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    payload = jwt.decode(token, config.jwt_secret, algorithms=[config.jwt_algorithm])
    # 后台与会员主键各自从 1 自增，仅按 sub 查库会串身份：必须校验令牌类型
    if payload.get("typ") != "admin":
        raise jwt.InvalidTokenError("not an admin token")
    return payload


def _member_secret() -> str:
    return config.member_jwt_secret or config.jwt_secret


def create_member_token(member_id: int, phone: str) -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "sub": str(member_id),
        "phone": phone,
        "typ": "member",
        "iat": now,
        "exp": now + datetime.timedelta(minutes=config.jwt_expire_minutes),
    }
    return jwt.encode(payload, _member_secret(), algorithm=config.jwt_algorithm)


def decode_member_token(token: str) -> dict[str, Any]:
    payload = jwt.decode(token, _member_secret(), algorithms=[config.jwt_algorithm])
    if payload.get("typ") != "member":
        raise jwt.InvalidTokenError("not a member token")
    return payload
