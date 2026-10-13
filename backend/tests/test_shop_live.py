"""前台实时更新指纹接口测试（specs/商城前台V1.2.spec.md §9.5）"""
import asyncio

import pytest

import aiomysql
from aiomysql.cursors import DictCursor

from core.config import config


async def _conn():
    return await aiomysql.connect(
        host=config.db_host, port=config.db_port, user=config.db_user,
        password=config.db_password, db=config.db_name, charset=config.db_charset,
        autocommit=True, cursorclass=DictCursor,
    )


def _q(sql, params=()):
    async def run():
        conn = await _conn()
        try:
            async with conn.cursor() as cur:
                await cur.execute(sql, params)
                if cur.description:
                    return await cur.fetchall()
                return None
        finally:
            conn.close()
    return asyncio.run(run())


_EMPTY_SHA = "e3b0c44298fc1c149afbf4c8996fb924"  # sha256("")[:32]


def test_live_version_shape(client):
    r = client.get("/api/v1/shop/live/version")
    body = r.json()
    assert r.status_code == 200 and body["code"] == 0, body
    data = body["data"]
    assert data["version"] and len(data["version"]) == 32
    assert set(data["assets"]) == {"css", "html", "js"}
    for v in data["assets"].values():
        assert len(v) == 32 and v != _EMPTY_SHA, f"资产指纹为空拼接: {v}"
    assert data["data"] and len(data["data"]) == 32


def test_live_version_changes_when_data_updated(client):
    # 直接改库会命中 2s 缓存，先拿到基线
    v1 = client.get("/api/v1/shop/live/version").json()["data"]["data"]
    row = _q("SELECT id, updated_at FROM goods ORDER BY id DESC LIMIT 1")
    if not row:
        # 用 pytest.skip 而非 return：直接 return 会让这条用例在空库时「静默变绿」
        pytest.skip("库内没有商品：请先执行 uv run python -m seed.runner demo")
    gid, prev = row[0]["id"], row[0]["updated_at"]
    try:
        _q("UPDATE goods SET updated_at = DATE_ADD(NOW(), INTERVAL 1 DAY) WHERE id=%s", (gid,))
        # 绕过接口缓存
        import services.shop_live as svc

        svc._cache["data"] = None
        svc._cache["ts"] = 0.0
        v2 = client.get("/api/v1/shop/live/version").json()["data"]["data"]
        assert v1 != v2
    finally:
        _q("UPDATE goods SET updated_at=%s WHERE id=%s", (prev, gid))
        import services.shop_live as svc

        svc._cache["data"] = None
        svc._cache["ts"] = 0.0
