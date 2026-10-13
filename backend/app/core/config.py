import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BASE_DIR.parent


def _clean(value: str) -> str:
    return value.strip().strip('"').strip("'")


def _load_env():
    """读取 backend/.env，已存在的系统环境变量优先（setdefault）。

    用 utf-8-sig 解码：Windows 记事本另存为 UTF-8 会写入 BOM，直接用 utf-8 读会把
    BOM 粘到第一个变量名上（变成 "\\ufeffAPP_NAME"），配置静默失效且极难排查。
    """
    env_file = BASE_DIR / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip().lstrip("\ufeff")
        value = _clean(value)
        if key:
            os.environ.setdefault(key, value)


_load_env()


def _int(key: str, default: int) -> int:
    raw = os.getenv(key, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        raise RuntimeError(
            f"环境变量 {key} 需要是整数，当前值：{raw!r}。请检查 backend/.env"
        )


_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off"}


def _bool(key: str, default: bool = False) -> bool:
    raw = os.getenv(key, "").strip().lower()
    if not raw:
        return default
    if raw in _TRUE:
        return True
    if raw in _FALSE:
        return False
    # 拼错的值（如 ture）不能静默当成 False：那会把短信等开关悄悄关掉且极难排查
    raise RuntimeError(
        f"环境变量 {key} 只接受 true/false（或 1/0、yes/no、on/off），当前值：{raw!r}。请检查 backend/.env"
    )


def _required(key: str, default: str = "") -> str:
    value = os.getenv(key, default).strip()
    if not value:
        raise RuntimeError(
            f"缺少必填环境变量 {key}。请复制 backend/.env.example 为 backend/.env 后填写，"
            f"生成随机密钥可执行：python -c \"import secrets;print(secrets.token_urlsafe(48))\""
        )
    return value


class Config:
    app_name = os.getenv("APP_NAME", "shop-open")
    db_host = os.getenv("DB_HOST", "127.0.0.1")
    db_port = _int("DB_PORT", 3306)
    db_user = os.getenv("DB_USER", "root")
    db_password = os.getenv("DB_PASSWORD", "")
    db_name = os.getenv("DB_NAME", "aaashop")
    db_charset = "utf8mb4"
    db_pool_min = _int("DB_POOL_MIN", 2)
    db_pool_max = _int("DB_POOL_MAX", 10)
    jwt_secret = _required("JWT_SECRET")
    jwt_algorithm = "HS256"
    jwt_expire_minutes = _int("JWT_EXPIRE_MINUTES", 120)
    member_jwt_secret = os.getenv("MEMBER_JWT_SECRET", "")
    # 默认关闭：开启时验证码为回显式演示通道，任何知道开关的人都能自助注册，
    # 属于必须显式选择的非安全行为，绝不能是开箱默认值。
    sms_mock = _bool("SMS_MOCK", False)
    # 验证码一律 CSPRNG 随机生成、BCrypt 哈希落库比对，历史上曾存在的
    # SMS_MOCK_CODE 固定码（'123456'）等同于公开注册后门，已从配置中彻底移除。
    sms_code_expire_seconds = _int("SMS_CODE_EXPIRE_SECONDS", 300)
    sms_interval_seconds = _int("SMS_INTERVAL_SECONDS", 60)
    order_pay_timeout_minutes = _int("ORDER_PAY_TIMEOUT_MINUTES", 14)
    upload_dir = os.getenv("UPLOAD_DIR", "uploads")
    upload_max_mb = _int("UPLOAD_MAX_MB", 5)
    upload_public_base = os.getenv("UPLOAD_PUBLIC_BASE", "").rstrip("/")
    goods_audit_enabled = _bool("GOODS_AUDIT_ENABLED", False)
    cors_origins = [
        o.strip()
        for o in os.getenv(
            "CORS_ORIGINS",
            "http://127.0.0.1:8000,http://127.0.0.1:8001,http://localhost:8000,http://localhost:8001",
        ).split(",")
        if o.strip()
    ]
    login_fail_limit = _int("LOGIN_FAIL_LIMIT", 5)
    login_fail_lock_minutes = _int("LOGIN_FAIL_LOCK_MINUTES", 15)
    page_size = _int("PAGE_SIZE", 20)
    manager_dir = os.getenv("STATIC_MANAGER_DIR", str(PROJECT_ROOT / "manager"))
    front_dir = os.getenv("STATIC_FRONT_DIR", str(PROJECT_ROOT / "front"))
    # 启动参数由 run.py 读取（不放默认值到别处），收在这里便于测试与单一口径
    port = _int("PORT", 8001)
    reload = _bool("RELOAD", False)


config = Config()
