from contextlib import asynccontextmanager

import aiomysql

from core.config import config

pool: aiomysql.Pool | None = None


def _hint(exc: Exception) -> str:
    """把 pymysql 原始异常翻译成人话，按错误码给出对应的排查动作。"""
    code = getattr(exc, "args", (None,))[0] if getattr(exc, "args", None) else None
    if code == 2003:
        return (
            "MySQL 服务没启动，或地址/端口不对。\n"
            "  处理：① 确认 MySQL 已启动（Windows 看服务管理器，Docker 看容器是否在跑）"
            "② 检查 backend/.env 的 DB_HOST / DB_PORT"
        )
    if code == 1045:
        return (
            "账号或密码不对。\n"
            "  处理：打开 backend/.env，核对 DB_USER / DB_PASSWORD 与你的 MySQL 实际账号一致"
            "（本地 root 无密码时 DB_PASSWORD 必须留空）"
        )
    if code == 1049:
        return (
            f"数据库 {config.db_name} 不存在。\n"
            "  处理：执行 uv run python -m seed.runner base 会自动建库"
        )
    if code == 1044:
        return (
            "账号无权限访问该库。\n"
            "  处理：换用有权限的 MySQL 账号，或给该账号授权"
        )
    return "处理：检查 MySQL 是否启动，以及 backend/.env 里 DB_HOST / DB_PORT / DB_USER / DB_PASSWORD / DB_NAME 是否正确"


async def init_pool():
    global pool
    if pool is None:
        try:
            pool = await aiomysql.create_pool(
                host=config.db_host,
                port=config.db_port,
                user=config.db_user,
                password=config.db_password,
                db=config.db_name,
                charset=config.db_charset,
                autocommit=True,
                minsize=config.db_pool_min,
                maxsize=config.db_pool_max,
                cursorclass=aiomysql.DictCursor,
                # 业务统一东八区；init_command 在每个新建连接建立时执行一次，session 级别生效
                init_command="SET time_zone='+08:00'",
            )
        except Exception as exc:
            raise RuntimeError(
                "[数据库] 连接失败\n"
                f"  目标：{config.db_user}@{config.db_host}:{config.db_port}/{config.db_name}"
                "（密码不打印）\n"
                f"  原因：{exc}\n"
                f"  {_hint(exc)}"
            ) from exc


def _conn():
    """统一取连接入口：池未初始化时给出明确提示，避免抛 NoneType 的 AttributeError。"""
    if pool is None:
        raise RuntimeError(
            "[数据库] 连接池尚未初始化。请先确认 MySQL 已启动且已执行 seed.runner base 建库建表，然后重启后端。"
        )
    return pool.acquire()


async def close_pool():
    global pool
    if pool is not None:
        pool.close()
        await pool.wait_closed()
        pool = None


async def _ensure_tz(conn):
    """Guard: re-apply session time_zone in case the connection is reused elsewhere."""
    import logging as _logging
    try:
        async with conn.cursor() as cur:
            await cur.execute("SET time_zone='+08:00'")
    except Exception as e:
        _logging.getLogger('tz').warning('failed to set session time_zone: %r', e)


async def fetch_all(sql: str, params=None) -> list[dict]:
    async with _conn() as conn:
        await _ensure_tz(conn)
        async with conn.cursor() as cur:
            await cur.execute(sql, params or ())
            return await cur.fetchall()


async def fetch_one(sql: str, params=None) -> dict | None:
    async with _conn() as conn:
        await _ensure_tz(conn)
        async with conn.cursor() as cur:
            await cur.execute(sql, params or ())
            return await cur.fetchone()


async def execute(sql: str, params=None) -> int:
    async with _conn() as conn:
        await _ensure_tz(conn)
        async with conn.cursor() as cur:
            await cur.execute(sql, params or ())
            return cur.rowcount


async def execute_return_id(sql: str, params=None) -> int:
    async with _conn() as conn:
        await _ensure_tz(conn)
        async with conn.cursor() as cur:
            await cur.execute(sql, params or ())
            return cur.lastrowid


@asynccontextmanager
async def transaction():
    async with _conn() as conn:
        await _ensure_tz(conn)
        try:
            await conn.begin()
            async with conn.cursor() as cur:
                yield cur
            await conn.commit()
        except BaseException:
            await conn.rollback()
            raise
