import asyncio
import re
import sys
from functools import partial
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

import aiomysql

from core.config import config
from seed import base as seed_base
from seed import demo as seed_demo
from seed.schema import TABLES, ensure_content_updated_at


async def _connect() -> aiomysql.Connection:
    try:
        return await aiomysql.connect(
            host=config.db_host,
            port=config.db_port,
            user=config.db_user,
            password=config.db_password,
            db=config.db_name,
            charset=config.db_charset,
            autocommit=True,
            cursorclass=aiomysql.cursors.DictCursor,
        )
    except Exception as exc:
        raise SystemExit(_conn_help(exc)) from exc


async def _exec(conn: aiomysql.Connection, sql: str, params=None):
    async with conn.cursor() as cur:
        await cur.execute(sql, params or ())
        return cur.lastrowid


async def _fetch(conn: aiomysql.Connection, sql: str, params=None):
    async with conn.cursor() as cur:
        await cur.execute(sql, params or ())
        return await cur.fetchall()


async def create_tables(conn: aiomysql.Connection):
    for sql in TABLES:
        await _exec(conn, sql)
    await ensure_content_updated_at(conn)


async def _run_base():
    conn = await _connect()
    try:
        await create_tables(conn)
        exec_ = partial(_exec, conn)
        fetch_ = partial(_fetch, conn)
        await seed_base.seed(exec_, fetch_)
        print("base 数据完成")
    finally:
        conn.close()


async def _run_demo():
    conn = await _connect()
    try:
        exec_ = partial(_exec, conn)
        fetch_ = partial(_fetch, conn)
        await seed_demo.seed(exec_, fetch_)
        print("demo 数据完成")
    finally:
        conn.close()


async def _clean_base():
    conn = await _connect()
    try:
        for sql in seed_base.CLEAN_SQL:
            await _exec(conn, sql)
        print("base 数据已清空")
    finally:
        conn.close()


async def _clean_demo():
    conn = await _connect()
    try:
        for sql in seed_demo.CLEAN_SQL:
            await _exec(conn, sql)
        print("demo 数据已清空")
    finally:
        conn.close()


_IDENT_RE = re.compile(r"^[A-Za-z0-9_]+$")


def _conn_help(exc: Exception) -> str:
    """把 pymysql 原始异常翻译成新手看得懂的排查步骤。"""
    code = exc.args[0] if getattr(exc, "args", None) else None
    target = f"{config.db_user}@{config.db_host}:{config.db_port}"
    base = f"[seed] 无法连接 MySQL {target}\n  原因：{exc}\n"
    if code == 2003:
        return base + (
            "  处理：① MySQL 没启动 —— Docker 方式执行 docker compose up -d 并等 30 秒；"
            "本机方式到服务管理器启动 MySQL\n"
            "        ② 端口不对 —— 检查 backend/.env 的 DB_HOST / DB_PORT"
        )
    if code == 1045:
        return base + (
            "  处理：账号或密码不对。打开 backend/.env，核对 DB_USER / DB_PASSWORD：\n"
            "        Docker 方式默认 root / DEV_ONLY_123456；本机 root 无密码时 DB_PASSWORD 必须留空"
        )
    return base + "  处理：确认 MySQL 已启动，且 backend/.env 的 DB_HOST / DB_PORT / DB_USER / DB_PASSWORD 正确"


async def _check_version(version: str):
    """MySQL < 5.7 会在建表时报看不懂的 SQL 语法错，这里提前拦住并给结论。"""
    if not version:
        raise SystemExit(
            "[seed] 无法读取 MySQL 版本，已中止。请确认 MySQL 服务正常启动后重试。"
        )
    # MariaDB 握手串形如 "5.5.5-10.0.38-MariaDB"，前半段是伪装版本，不能拿来判定
    if "mariadb" in version.lower():
        return
    try:
        parts = [int(x) for x in re.split(r"[.\-]", version)[:2]]
    except (ValueError, IndexError):
        return
    if len(parts) >= 2 and (parts[0], parts[1]) < (5, 7):
        raise SystemExit(
            f"[seed] MySQL 版本过低：{version}。本项目要求 5.7 及以上（推荐 8.0），请升级后重试。"
        )


async def ensure_database():
    """库不存在时自动创建，免去克隆后手工建库；账号无 CREATE 权限时给出明确指引而非静默失败。"""
    if not _IDENT_RE.match(config.db_name or ""):
        raise SystemExit(f"[seed] DB_NAME 非法，仅允许字母/数字/下划线：{config.db_name!r}")
    try:
        conn = await aiomysql.connect(
            host=config.db_host,
            port=config.db_port,
            user=config.db_user,
            password=config.db_password,
            charset=config.db_charset,
            autocommit=True,
        )
    except Exception as exc:
        raise SystemExit(_conn_help(exc))
    try:
        # 此处连接未指定 cursorclass，fetchone 返回 tuple（不是 dict），按位置取版本号
        async with conn.cursor() as cur:
            await cur.execute("SELECT VERSION()")
            row = await cur.fetchone()
            await _check_version(row[0] if row else "")
            await cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{config.db_name}` "
                "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci"
            )
            await cur.execute(f"USE `{config.db_name}`")
    except SystemExit:
        raise
    except Exception as exc:
        code = exc.args[0] if getattr(exc, "args", None) else None
        # 1044/1142 = 无库级/CREATE 权限，其余原因（磁盘满、连接断开等）不该谎报权限问题
        reason = "账号无建库权限" if code in (1044, 1142) else "建库失败"
        raise SystemExit(
            f"[seed] {reason}：{exc}\n"
            f"请手动执行：CREATE DATABASE IF NOT EXISTS `{config.db_name}` "
            "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;"
        )
    finally:
        conn.close()


async def main(cmd: str):
    if cmd not in {"base", "demo", "clean-base", "clean-demo"}:
        print("用法: python -m seed.runner <base|demo|clean-base|clean-demo>")
        return
    await ensure_database()
    if cmd == "base":
        await _run_base()
    elif cmd == "demo":
        await _run_demo()
    elif cmd == "clean-base":
        await _clean_base()
    elif cmd == "clean-demo":
        await _clean_demo()


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "base"
    asyncio.run(main(command))
