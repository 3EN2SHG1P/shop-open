"""demo 模拟数据契约测试（图片本地化 + 数据量 + 幂等）。

依赖：先执行 python -m seed.runner base && python -m seed.runner demo
"""

import asyncio
from functools import partial

import pymysql
import pytest

from core.config import config
from seed import demo as seed_demo
from seed.runner import _connect, _exec, _fetch


@pytest.fixture(scope="session", autouse=True)
def _require_mysql():
    """没有可用 MySQL 时整文件 skip，而不是把「环境没准备好」报成一堆红。

    本文件验证的是 demo 种子数据的契约（幂等 / 规模 / 图片本地化），前提是数据库
    已经 seed 过；连不上库属于环境前置条件缺失，不应被判定为项目损坏。
    """
    try:
        conn = _conn()
    except Exception as e:
        pytest.skip(f"没有可用 MySQL，跳过 demo 契约测试：{type(e).__name__}: {e}")
    else:
        conn.close()

COUNT_TABLES = [
    "goods",
    "goods_images",
    "goods_sku",
    "goods_comments",
    "orders",
    "order_items",
    "members",
    "member_address",
    "member_cart",
    "points_logs",
    "member_logs",
    "coupons",
    "coupon_receive",
    "after_sales",
    "ads",
    "articles",
]


def _conn():
    return pymysql.connect(
        host=config.db_host,
        port=config.db_port,
        user=config.db_user,
        password=config.db_password,
        database=config.db_name,
        charset=config.db_charset,
        autocommit=True,
        cursorclass=pymysql.cursors.DictCursor,
    )


def _counts():
    conn = _conn()
    try:
        with conn.cursor() as cur:
            out = {}
            for t in COUNT_TABLES:
                cur.execute(f"SELECT COUNT(*) AS c FROM {t}")
                out[t] = cur.fetchone()["c"]
            return out
    finally:
        conn.close()


def _scalar(sql, args=None):
    conn = _conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, args or ())
            row = cur.fetchone()
            return list(row.values())[0] if row else None
    finally:
        conn.close()


def _run_demo_seed():
    async def _go():
        conn = await _connect()
        try:
            await seed_demo.seed(partial(_exec, conn), partial(_fetch, conn))
        finally:
            conn.close()

    asyncio.run(_go())


def test_demo_seed_is_idempotent():
    """重复执行 demo 只补齐不翻倍。"""
    _run_demo_seed()
    before = _counts()
    _run_demo_seed()
    after = _counts()
    assert before == after, f"demo 非幂等：{before} -> {after}"


def test_demo_mock_data_scale():
    """模拟数据规模：足够覆盖前后台列表/筛选/分页测试。"""
    assert _scalar("SELECT COUNT(*) FROM goods") >= 20
    assert _scalar("SELECT COUNT(*) FROM goods_images") >= 40
    assert _scalar("SELECT COUNT(*) FROM goods_sku") >= 20
    assert _scalar("SELECT COUNT(*) FROM orders") >= 15
    assert _scalar("SELECT COUNT(*) FROM members") >= 6
    assert _scalar("SELECT COUNT(*) FROM member_address") >= 8
    assert _scalar("SELECT COUNT(*) FROM member_cart") >= 3
    assert _scalar("SELECT COUNT(*) FROM goods_comments") >= 10
    assert _scalar("SELECT COUNT(*) FROM after_sales") >= 4
    status_kinds = _scalar("SELECT COUNT(DISTINCT order_status) FROM orders")
    assert status_kinds >= 5, f"订单状态覆盖不足：{status_kinds}"


def test_demo_images_use_local_uploads():
    """图片字段全部指向本地 /uploads/seed/，不再有外链占位。"""
    assert _scalar("SELECT COUNT(*) FROM goods_images WHERE url NOT LIKE %s", ("%/uploads/seed/%",)) == 0
    assert _scalar("SELECT COUNT(*) FROM goods_images WHERE url LIKE %s", ("http://img.example.com%",)) == 0
    assert _scalar(
        "SELECT COUNT(*) FROM ads WHERE image IS NOT NULL AND image<>'' AND image NOT LIKE %s",
        ("%/uploads/seed/%",),
    ) == 0
    assert _scalar(
        "SELECT COUNT(*) FROM articles WHERE cover IS NOT NULL AND cover<>'' AND cover NOT LIKE %s",
        ("%/uploads/seed/%",),
    ) == 0
    assert _scalar(
        "SELECT COUNT(*) FROM goods_sku WHERE image IS NOT NULL AND image<>'' AND image NOT LIKE %s",
        ("%/uploads/seed/%",),
    ) == 0
    with_img = _scalar("SELECT COUNT(*) FROM goods WHERE detail_html LIKE %s", ("%<img%",))
    assert with_img >= 20, f"商品详情带图数量不足：{with_img}"
