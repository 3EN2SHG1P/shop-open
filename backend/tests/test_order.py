import asyncio
import uuid

import pytest

import aiomysql
from aiomysql.cursors import DictCursor

from core.config import config


def _tag():
    return uuid.uuid4().hex[:10].upper()


async def _conn():
    return await aiomysql.connect(
        host=config.db_host, port=config.db_port, user=config.db_user,
        password=config.db_password, db=config.db_name, charset=config.db_charset,
        autocommit=True, cursorclass=DictCursor,
    )


def _run(sqls: list[tuple[str, tuple]]):
    async def run():
        conn = await _conn()
        try:
            cur = await conn.cursor()
            for sql, params in sqls:
                await cur.execute(sql, params)
        finally:
            conn.close()

    asyncio.run(run())


def _q1(sql: str, params: tuple = ()):
    async def run():
        conn = await _conn()
        try:
            cur = await conn.cursor()
            await cur.execute(sql, params)
            return await cur.fetchone()
        finally:
            conn.close()

    return asyncio.run(run())


def _find(datas, key, value):
    return next((x for x in datas if x.get(key) == value), None)


def _make_order(order_no: str, status: int, paid: int = 0):
    paid_sql = "NOW()" if paid else "NULL"
    return (
        f"INSERT INTO orders (order_no,member_id,total_amount,freight_amount,pay_amount,pay_type,pay_status,"
        f"order_status,receiver_name,receiver_phone,receiver_address,order_source,paid_at) "
        f"VALUES (%s,1,100.00,0.00,100.00,1,{paid},{status},'测试收货人','10000000001','示例省测试市测试路1号','h5',{paid_sql})",
        (order_no,),
    )


def _make_item(order_id: int, goods_id: int, sku_id: int, goods_name: str, qty: int = 1):
    return (
        "INSERT INTO order_items (order_id,goods_id,sku_id,goods_name,quantity,price,subtotal) VALUES (%s,%s,%s,%s,%s,100.00,100.00)",
        (order_id, goods_id, sku_id, goods_name, qty),
    )


def test_orders_list_and_detail(client, admin_headers):
    r = client.get("/api/v1/orders", headers=admin_headers)
    assert r.status_code == 200 and r.json()["code"] == 0, r.text
    data = r.json()["data"]
    assert data["orderStatusCounts"]["all"] == data["total"]
    assert set(str(i) for i in range(1, 7)) <= set(data["orderStatusCounts"].keys())
    for item in data["list"]:
        assert item.get("orderNo") and item.get("orderStatusText")

    r = client.get("/api/v1/orders?order_status=1", headers=admin_headers)
    assert r.json()["code"] == 0
    assert all(x["orderStatus"] == 1 for x in r.json()["data"]["list"])

    r = client.get("/api/v1/orders?order_status=2", headers=admin_headers)
    assert r.json()["code"] == 0
    assert all(x["orderStatus"] == 2 for x in r.json()["data"]["list"])

    page = client.get("/api/v1/orders?page=1&page_size=2", headers=admin_headers).json()["data"]
    assert len(page["list"]) <= 2

    if page["list"]:
        oid = page["list"][0]["id"]
        d = client.get(f"/api/v1/orders/{oid}", headers=admin_headers).json()["data"]
        assert d["id"] == oid and d["orderNo"]
        assert isinstance(d["items"], list) and isinstance(d["logs"], list)
        assert isinstance(d["afterSales"], list)
        assert d["receiver"]["name"]
    else:
        # 列表为空时上面的断言会整段跳过，静默变绿；这里显式标记出来
        pytest.skip("没有订单数据：请先执行 uv run python -m seed.runner demo")


def test_order_price_ship_cancel_batch(client, admin_headers):
    tag = _tag()
    sku = _q1(
        "SELECT s.id AS sku_id, s.goods_id, g.name AS goods_name, s.stock AS sstock, g.stock AS gstock "
        "FROM goods_sku s JOIN goods g ON g.id=s.goods_id ORDER BY s.id LIMIT 1"
    )
    assert sku, "依赖商品种子数据"
    sku_id, goods_id = sku["sku_id"], sku["goods_id"]
    goods_name = sku["goods_name"]
    no1, no2, no3, no4 = f"T1{tag}", f"T2{tag}", f"T3{tag}", f"T4{tag}"
    _run([
        _make_order(no1, 1, paid=0),
        _make_order(no2, 2, paid=1),
        _make_order(no3, 2, paid=1),
        _make_order(no4, 2, paid=1),
    ])
    id1 = _q1("SELECT id FROM orders WHERE order_no=%s", (no1,))["id"]
    id2 = _q1("SELECT id FROM orders WHERE order_no=%s", (no2,))["id"]
    id3 = _q1("SELECT id FROM orders WHERE order_no=%s", (no3,))["id"]
    id4 = _q1("SELECT id FROM orders WHERE order_no=%s", (no4,))["id"]
    _run([
        _make_item(id1, goods_id, sku_id, goods_name),
        _make_item(id2, goods_id, sku_id, goods_name),
        _make_item(id3, goods_id, sku_id, goods_name),
        _make_item(id4, goods_id, sku_id, goods_name),
    ])
    cancelled_stock = False
    try:
        r = client.put(f"/api/v1/orders/{id1}/price", json={"amount": 88.00, "reason": "促销改价"}, headers=admin_headers)
        assert r.json()["code"] == 0, r.text
        d = client.get(f"/api/v1/orders/{id1}", headers=admin_headers).json()["data"]
        assert float(d["payAmount"]) == 88.0
        assert any(x["action"] == "修改价格" for x in d["logs"])

        r = client.put(f"/api/v1/orders/{id2}/price", json={"amount": 1.00}, headers=admin_headers)
        assert r.json()["code"] != 0

        r = client.post(f"/api/v1/orders/{id2}/ship", json={"logisticsCompany": "速达速运", "logisticsNo": f"EX{tag}"}, headers=admin_headers)
        assert r.json()["code"] == 0, r.text
        d = client.get(f"/api/v1/orders/{id2}", headers=admin_headers).json()["data"]
        assert d["orderStatus"] == 3 and d["shippedAt"]

        r = client.post(f"/api/v1/orders/{id1}/ship", json={"logisticsCompany": "速达速运", "logisticsNo": f"EX{tag}"}, headers=admin_headers)
        assert r.json()["code"] != 0

        before_s = _q1("SELECT stock FROM goods_sku WHERE id=%s", (sku_id,))["stock"]
        before_g = _q1("SELECT stock FROM goods WHERE id=%s", (goods_id,))["stock"]
        r = client.post(f"/api/v1/orders/{id1}/cancel", headers=admin_headers)
        assert r.json()["code"] == 0, r.text
        d = client.get(f"/api/v1/orders/{id1}", headers=admin_headers).json()["data"]
        assert d["orderStatus"] == 5 and d["canceledAt"]
        assert any(x["action"] == "取消订单" for x in d["logs"])
        assert _q1("SELECT stock FROM goods_sku WHERE id=%s", (sku_id,))["stock"] == before_s + 1
        assert _q1("SELECT stock FROM goods WHERE id=%s", (goods_id,))["stock"] == before_g + 1
        cancelled_stock = True

        r = client.post("/api/v1/orders/batch/ship", json={
            "orders": [
                {"orderId": id3, "logisticsCompany": "众通快递", "logisticsNo": f"ZT1{tag}"},
                {"orderId": id4, "logisticsCompany": "众通快递", "logisticsNo": f"ZT2{tag}"},
            ]
        }, headers=admin_headers)
        assert r.json()["code"] == 0, r.text
        for iid in (id3, id4):
            assert client.get(f"/api/v1/orders/{iid}", headers=admin_headers).json()["data"]["orderStatus"] == 3
    finally:
        cleanup = [
            ("DELETE FROM order_items WHERE order_id=%s", (id1,)),
            ("DELETE FROM order_items WHERE order_id=%s", (id2,)),
            ("DELETE FROM order_items WHERE order_id=%s", (id3,)),
            ("DELETE FROM order_items WHERE order_id=%s", (id4,)),
            ("DELETE FROM order_logs WHERE order_id=%s", (id1,)),
            ("DELETE FROM order_logs WHERE order_id=%s", (id2,)),
            ("DELETE FROM order_logs WHERE order_id=%s", (id3,)),
            ("DELETE FROM order_logs WHERE order_id=%s", (id4,)),
            ("DELETE FROM orders WHERE id=%s", (id1,)),
            ("DELETE FROM orders WHERE id=%s", (id2,)),
            ("DELETE FROM orders WHERE id=%s", (id3,)),
            ("DELETE FROM orders WHERE id=%s", (id4,)),
        ]
        if cancelled_stock:
            cleanup.insert(0, ("UPDATE goods_sku SET stock=stock-1,version=version-1 WHERE id=%s", (sku_id,)))
            cleanup.insert(1, ("UPDATE goods SET stock=stock-1 WHERE id=%s", (goods_id,)))
        _run(cleanup)


def test_after_sale_audit_confirm(client, admin_headers):
    tag = _tag()
    no_a, no_b, no_c = f"TA{tag}", f"TB{tag}", f"TC{tag}"
    sqls = [
        _make_order(no_a, 6, paid=1),
        _make_order(no_b, 6, paid=1),
        _make_order(no_c, 6, paid=1),
    ]
    _run(sqls)
    id_a = _q1("SELECT id FROM orders WHERE order_no=%s", (no_a,))["id"]
    id_b = _q1("SELECT id FROM orders WHERE order_no=%s", (no_b,))["id"]
    id_c = _q1("SELECT id FROM orders WHERE order_no=%s", (no_c,))["id"]
    _run([
        ("UPDATE orders SET shipped_at=NOW() WHERE id=%s", (id_b,)),
        (
            "INSERT INTO after_sales (after_sale_no,order_id,member_id,type,reason,amount,status) VALUES (%s,%s,1,2,'外包装破损',50.00,1)",
            (f"AS1{tag}", id_a),
        ),
        (
            "INSERT INTO after_sales (after_sale_no,order_id,member_id,type,reason,amount,status) VALUES (%s,%s,1,2,'少发一件',50.00,1)",
            (f"AS2{tag}", id_b),
        ),
        (
            "INSERT INTO after_sales (after_sale_no,order_id,member_id,type,reason,amount,status) VALUES (%s,%s,1,1,'不想要了',100.00,1)",
            (f"AS3{tag}", id_c),
        ),
    ])
    aid1 = _q1("SELECT id FROM after_sales WHERE after_sale_no=%s", (f"AS1{tag}",))["id"]
    aid2 = _q1("SELECT id FROM after_sales WHERE after_sale_no=%s", (f"AS2{tag}",))["id"]
    aid3 = _q1("SELECT id FROM after_sales WHERE after_sale_no=%s", (f"AS3{tag}",))["id"]
    try:
        r = client.post(f"/api/v1/after-sales/{aid1}/audit", json={"agree": True, "handleNote": "同意退货"}, headers=admin_headers)
        assert r.json()["code"] == 0, r.text
        arow = _q1("SELECT status,handle_note,handle_by FROM after_sales WHERE id=%s", (aid1,))
        assert arow["status"] == 2 and arow["handle_note"] == "同意退货" and arow["handle_by"]
        assert _q1("SELECT order_status FROM orders WHERE id=%s", (id_a,))["order_status"] == 6

        r = client.post(f"/api/v1/after-sales/{aid1}/confirm-receipt", headers=admin_headers)
        assert r.json()["code"] == 0, r.text
        assert _q1("SELECT status FROM after_sales WHERE id=%s", (aid1,))["status"] == 3
        assert _q1("SELECT order_status FROM orders WHERE id=%s", (id_a,))["order_status"] == 5

        r = client.post(f"/api/v1/after-sales/{aid2}/audit", json={"agree": False, "handleNote": "证据不足"}, headers=admin_headers)
        assert r.json()["code"] == 0, r.text
        assert _q1("SELECT status FROM after_sales WHERE id=%s", (aid2,))["status"] == 4
        assert _q1("SELECT order_status FROM orders WHERE id=%s", (id_b,))["order_status"] == 3

        r = client.post(f"/api/v1/after-sales/{aid3}/audit", json={"agree": True}, headers=admin_headers)
        assert r.json()["code"] == 0, r.text
        assert _q1("SELECT status FROM after_sales WHERE id=%s", (aid3,))["status"] == 3
        assert _q1("SELECT order_status FROM orders WHERE id=%s", (id_c,))["order_status"] == 5

        list_data = client.get("/api/v1/after-sales?keyword=" + tag, headers=admin_headers).json()["data"]
        assert list_data["total"] >= 1
    finally:
        _run([
            ("DELETE FROM after_sales WHERE id=%s", (aid1,)),
            ("DELETE FROM after_sales WHERE id=%s", (aid2,)),
            ("DELETE FROM after_sales WHERE id=%s", (aid3,)),
            ("DELETE FROM order_logs WHERE order_id=%s", (id_a,)),
            ("DELETE FROM order_logs WHERE order_id=%s", (id_b,)),
            ("DELETE FROM order_logs WHERE order_id=%s", (id_c,)),
            ("DELETE FROM orders WHERE id=%s", (id_a,)),
            ("DELETE FROM orders WHERE id=%s", (id_b,)),
            ("DELETE FROM orders WHERE id=%s", (id_c,)),
        ])


def test_express_companies(client, admin_headers):
    tag = _tag()
    rid = None
    try:
        rows = client.get("/api/v1/express-companies", headers=admin_headers).json()["data"]
        assert isinstance(rows, list)

        r = client.post("/api/v1/express-companies", json={"name": f"测试快递{tag}", "code": f"TEST{tag}"}, headers=admin_headers)
        assert r.json()["code"] == 0, r.text
        rid = r.json()["data"]["id"]

        r = client.post("/api/v1/express-companies", json={"name": f"重复快递{tag}", "code": f"TEST{tag}"}, headers=admin_headers)
        assert r.json()["code"] != 0

        rows = client.get("/api/v1/express-companies", headers=admin_headers).json()["data"]
        assert any(x["code"] == f"TEST{tag}" for x in rows)
    finally:
        if rid:
            _run([("DELETE FROM express_companies WHERE id=%s", (rid,))])


def test_orders_export(client, admin_headers):
    r = client.get("/api/v1/orders/export", headers=admin_headers)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert r.content.startswith(b"\xef\xbb\xbf")


def test_after_sale_status_counts_not_follow_status_filter(client, admin_headers):
    tag = _tag()
    sqls = [_make_order(f"TSA1{tag}", 6, paid=1), _make_order(f"TSA2{tag}", 6, paid=1)]
    _run(sqls)
    id1 = _q1("SELECT id FROM orders WHERE order_no=%s", (f"TSA1{tag}",))["id"]
    id2 = _q1("SELECT id FROM orders WHERE order_no=%s", (f"TSA2{tag}",))["id"]
    _run([
        (
            "INSERT INTO after_sales (after_sale_no,order_id,member_id,type,reason,amount,status) VALUES (%s,%s,1,1,'测试A',10.00,1)",
            (f"ASA{tag}", id1),
        ),
        (
            "INSERT INTO after_sales (after_sale_no,order_id,member_id,type,reason,amount,status) VALUES (%s,%s,1,1,'测试B',20.00,2)",
            (f"ASB{tag}", id2),
        ),
    ])
    aid1 = _q1("SELECT id FROM after_sales WHERE after_sale_no=%s", (f"ASA{tag}",))["id"]
    aid2 = _q1("SELECT id FROM after_sales WHERE after_sale_no=%s", (f"ASB{tag}",))["id"]
    try:
        kw = {"keyword": tag}
        all_data = client.get("/api/v1/after-sales", params=kw, headers=admin_headers).json()["data"]
        assert all_data["total"] >= 2
        base_counts = all_data["statusCounts"]
        assert base_counts["1"] >= 1 and base_counts["2"] >= 1
        for st in ("1", "2", "3", "4"):
            d = client.get("/api/v1/after-sales", params={**kw, "status": st}, headers=admin_headers).json()["data"]
            assert all(x["status"] == int(st) for x in d["list"])
            assert d["statusCounts"] == base_counts, f"status={st} 时统计不应随 status 联动"
    finally:
        _run([
            ("DELETE FROM after_sales WHERE id=%s", (aid1,)),
            ("DELETE FROM after_sales WHERE id=%s", (aid2,)),
            ("DELETE FROM order_logs WHERE order_id=%s", (id1,)),
            ("DELETE FROM order_logs WHERE order_id=%s", (id2,)),
            ("DELETE FROM orders WHERE id=%s", (id1,)),
            ("DELETE FROM orders WHERE id=%s", (id2,)),
        ])
