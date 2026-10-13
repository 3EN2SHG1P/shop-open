import asyncio
import re
import uuid

import aiomysql
from aiomysql.cursors import DictCursor

from core.config import config


def _tag():
    return "T" + re.sub(r"\D", "", uuid.uuid4().hex)[:9]


def _phone():
    digits = re.sub(r"\D", "", uuid.uuid4().hex)
    return "13" + digits[:9]


def _pwd_hash():
    import bcrypt

    return bcrypt.hashpw(b"123456", bcrypt.gensalt()).decode("utf-8")


def _conn():
    return aiomysql.connect(
        host=config.db_host, port=config.db_port, user=config.db_user,
        password=config.db_password, db=config.db_name, charset=config.db_charset,
        autocommit=True, cursorclass=DictCursor,
    )


def _run(sqls):
    async def run():
        conn = await _conn()
        try:
            cur = await conn.cursor()
            for sql, params in sqls:
                await cur.execute(sql, params)
        finally:
            conn.close()

    asyncio.run(run())


def _q1(sql, params=()):
    async def run():
        conn = await _conn()
        try:
            cur = await conn.cursor()
            await cur.execute(sql, params)
            return await cur.fetchone()
        finally:
            conn.close()

    return asyncio.run(run())


def _qall(sql, params=()):
    async def run():
        conn = await _conn()
        try:
            cur = await conn.cursor()
            await cur.execute(sql, params)
            return await cur.fetchall()
        finally:
            conn.close()

    return asyncio.run(run())


def _create_member(points: int = 0):
    phone = _phone()
    _run([
        ("INSERT INTO members (nickname,phone,password_hash,points,status,registered_at) "
         "VALUES (%s,%s,%s,%s,1,'2026-01-01 00:00:00')", (f"前台用户{phone[-4:]}", phone, _pwd_hash(), points)),
    ])
    return _q1("SELECT id FROM members WHERE phone=%s", (phone,))["id"]


def _login(client, mid: int):
    phone = _q1("SELECT phone FROM members WHERE id=%s", (mid,))["phone"]
    r = client.post("/api/v1/shop/auth/login", json={"phone": phone, "password": "123456"})
    assert r.status_code == 200 and r.json()["code"] == 0, r.text
    token = r.json()["data"]["token"]
    return {"Authorization": f"Bearer {token}"}


def _stock_snapshot(gid: int):
    sku = _q1("SELECT id,stock FROM goods_sku WHERE goods_id=%s ORDER BY id LIMIT 1", (gid,))
    g = _q1("SELECT stock FROM goods WHERE id=%s", (gid,))
    return {"goods_id": gid, "sku_id": sku["id"], "sku_stock": sku["stock"], "goods_stock": g["stock"]}


def _restore_snapshot(snap):
    _run([
        ("UPDATE goods_sku SET stock=%s WHERE id=%s", (snap["sku_stock"], snap["sku_id"])),
        ("UPDATE goods SET stock=%s WHERE id=%s", (snap["goods_stock"], snap["goods_id"])),
    ])


def _cleanup_member(mid: int):
    oids = [r["id"] for r in _qall("SELECT id FROM orders WHERE member_id=%s", (mid,))]
    sqls = []
    for oid in oids:
        sqls += [
            ("DELETE FROM after_sales WHERE order_id=%s", (oid,)),
            ("DELETE FROM order_logs WHERE order_id=%s", (oid,)),
            ("DELETE FROM order_items WHERE order_id=%s", (oid,)),
        ]
    sqls += [
        ("DELETE FROM after_sales WHERE member_id=%s", (mid,)),
        ("DELETE FROM goods_comments WHERE member_id=%s", (mid,)),
        ("DELETE FROM coupon_receive WHERE member_id=%s", (mid,)),
        ("DELETE FROM member_address WHERE member_id=%s", (mid,)),
        ("DELETE FROM member_cart WHERE member_id=%s", (mid,)),
        ("DELETE FROM member_logs WHERE member_id=%s", (mid,)),
        ("DELETE FROM points_logs WHERE member_id=%s", (mid,)),
        ("DELETE FROM orders WHERE member_id=%s", (mid,)),
        ("DELETE FROM members WHERE id=%s", (mid,)),
    ]
    _run(sqls)


def _create_address(client, headers, mid: int) -> int:
    r = client.post("/api/v1/shop/addresses", headers=headers, json={
        "receiverName": f"收货人{mid}",
        "receiverPhone": _q1("SELECT phone FROM members WHERE id=%s", (mid,))["phone"],
        "province": "示例市", "city": "示例市", "district": "示例区",
        "detail": "测试路1号院2号楼",
        "isDefault": 1,
    })
    assert r.json()["code"] == 0, r.text
    return r.json()["data"]["id"]


def _create_paid_order(client, headers, sku_id: int, goods_id: int, addr_id: int):
    preview = client.post("/api/v1/shop/orders/preview", headers=headers, json={
        "type": "buy", "items": [{"goodsId": goods_id, "skuId": sku_id, "quantity": 1}],
        "addressId": addr_id,
    })
    assert preview.json()["code"] == 0, preview.text
    pdata = preview.json()["data"]
    r = client.post("/api/v1/shop/orders", headers=headers, json={
        "previewToken": pdata["previewToken"], "addressId": addr_id, "payType": 1,
        "couponId": None, "pointsUsed": 0, "buyerMessage": "",
    })
    assert r.json()["code"] == 0, r.text
    oid = r.json()["data"]["id"]
    pay = client.post(f"/api/v1/shop/pay/{oid}", headers=headers, json={"payType": 1})
    assert pay.json()["code"] == 0, pay.text
    return oid


def test_shop_auth_address_cart(client):
    mid = _create_member()
    headers = _login(client, mid)
    try:
        r = client.get("/api/v1/shop/auth/me", headers=headers)
        assert r.json()["code"] == 0 and r.json()["data"]["id"] == mid
        r = client.put("/api/v1/shop/auth/profile", headers=headers, json={"nickname": "新昵称" + _tag(), "avatar": ""})
        assert r.json()["code"] == 0, r.text
        assert r.json()["data"]["nickname"].startswith("新昵称")

        aid = _create_address(client, headers, mid)
        r = client.get("/api/v1/shop/addresses", headers=headers)
        rows = r.json()["data"]["list"]
        assert rows and rows[0]["id"] == aid and rows[0]["isDefault"] == 1

        r = client.get("/api/v1/shop/cart", headers=headers)
        assert r.json()["code"] == 0
    finally:
        _cleanup_member(mid)


def test_shop_checkout_pay_comment_flow(client, admin_headers):
    gid = 1
    sku_id = _q1("SELECT id FROM goods_sku WHERE goods_id=%s ORDER BY id LIMIT 1", (gid,))["id"]
    price = float(_q1("SELECT price FROM goods_sku WHERE id=%s", (sku_id,))["price"])
    snap = _stock_snapshot(gid)
    mid = _create_member(points=2000)
    headers = _login(client, mid)
    try:
        aid = _create_address(client, headers, mid)

        avail = client.get("/api/v1/shop/coupons/available", headers=headers)
        assert avail.json()["code"] == 0
        ids = {x["id"] for x in avail.json()["data"]["list"]}
        assert 1 in ids and 2 in ids
        r = client.post("/api/v1/shop/coupons/2/receive", headers=headers)
        assert r.json()["code"] == 0, r.text
        r = client.post("/api/v1/shop/coupons/2/receive", headers=headers)
        assert r.json()["code"] != 0
        mine = client.get("/api/v1/shop/coupons?status=1", headers=headers)
        assert mine.json()["code"] == 0 and mine.json()["data"]["total"] >= 1

        r = client.get("/api/v1/shop/points", headers=headers)
        assert r.json()["code"] == 0 and r.json()["data"]["points"] == 2000
        r = client.get("/api/v1/shop/points/logs", headers=headers)
        assert r.json()["code"] == 0

        body = {"type": "buy", "items": [{"goodsId": gid, "skuId": sku_id, "quantity": 1}], "addressId": aid}
        r = client.post("/api/v1/shop/orders/preview", headers=headers, json=body)
        assert r.json()["code"] == 0, r.text
        p = r.json()["data"]
        assert abs(p["totalAmount"] - price) < 0.001 and p["couponAmount"] == 0 and p["payAmount"] == price

        r = client.post("/api/v1/shop/orders/preview", headers=headers,
                        json=body | {"couponId": 2, "pointsUsed": 500})
        assert r.json()["code"] == 0, r.text
        p2 = r.json()["data"]
        assert p2["couponAmount"] == 100 and p2["pointsAmount"] == 5
        assert abs(p2["payAmount"] - (price - 105)) < 0.001

        r = client.post("/api/v1/shop/orders", headers=headers, json={
            "previewToken": p2["previewToken"], "addressId": aid, "payType": 1,
            "couponId": 2, "pointsUsed": 500, "buyerMessage": "发货前联系我",
        })
        assert r.json()["code"] == 0, r.text
        oid = r.json()["data"]["id"]

        stock = _q1("SELECT stock FROM goods_sku WHERE id=%s", (sku_id,))["stock"]
        assert stock == snap["sku_stock"] - 1
        row = _q1("SELECT coupon_amount,points_amount,pay_amount,pay_status,order_status,order_no FROM orders WHERE id=%s", (oid,))
        assert float(row["coupon_amount"]) == 100 and float(row["points_amount"]) == 5
        assert float(row["pay_amount"]) == round(price - 105, 2) and row["pay_status"] == 0 and row["order_status"] == 1
        cr = _q1("SELECT status FROM coupon_receive WHERE coupon_id=2 AND member_id=%s", (mid,))
        assert cr["status"] == 2
        assert _q1("SELECT points FROM members WHERE id=%s", (mid,))["points"] == 1500

        d = client.get(f"/api/v1/shop/orders/{oid}", headers=headers)
        detail = d.json()["data"]
        assert detail["payAmount"] == round(price - 105, 2) and detail["items"][0]["goodsId"] == gid
        assert "pay" in detail["actions"] and "cancel" in detail["actions"]
        assert detail["receiverPhone"]

        lst = client.get("/api/v1/shop/orders?status=0", headers=headers)
        data = lst.json()["data"]
        assert any(x["id"] == oid for x in data["list"])
        assert data["orderStatusCounts"]["1"] >= 1

        r = client.post(f"/api/v1/shop/pay/{oid}", headers=headers, json={"payType": 1})
        assert r.json()["code"] == 0, r.text
        st = client.get(f"/api/v1/shop/pay/{oid}/status", headers=headers).json()["data"]
        assert st["payStatus"] == 1 and st["orderStatus"] == 2

        ship = client.post(f"/api/v1/orders/{oid}/ship", headers=admin_headers,
                           json={"logisticsCompany": "速达速运", "logisticsNo": f"EX{_tag()}"})
        assert ship.json()["code"] == 0, ship.text
        r = client.post(f"/api/v1/shop/orders/{oid}/confirm-receipt", headers=headers)
        assert r.json()["code"] == 0, r.text
        detail = client.get(f"/api/v1/shop/orders/{oid}", headers=headers).json()["data"]
        assert detail["orderStatus"] == 4 and "afterSale" in detail["actions"] and "again" in detail["actions"]

        lg = client.get(f"/api/v1/shop/orders/{oid}/logistics", headers=headers).json()["data"]
        assert lg["logisticsCompany"] == "速达速运" and lg["logisticsNo"].startswith("EX")
        ag = client.post(f"/api/v1/shop/orders/{oid}/again", headers=headers)
        assert ag.json()["code"] == 0, ag.text

        cm = client.post(f"/api/v1/shop/goods/{gid}/comments", headers=headers,
                         json={"orderId": oid, "score": 5, "content": "商品体验很好"})
        assert cm.json()["code"] == 0, cm.text

        used = client.get("/api/v1/shop/coupons?status=2", headers=headers).json()["data"]
        assert any(x["id"] == 2 for x in used["list"])
        logs = client.get("/api/v1/shop/points/logs", headers=headers).json()["data"]
        assert logs["total"] >= 1 and any(x["changeValue"] == -500 for x in logs["list"])
    finally:
        _cleanup_member(mid)
        _restore_snapshot(snap)


def test_shop_order_timeout_auto_cancel(client):
    gid = 1
    sku_id = _q1("SELECT id FROM goods_sku WHERE goods_id=%s ORDER BY id LIMIT 1", (gid,))["id"]
    snap = _stock_snapshot(gid)
    mid = _create_member()
    headers = _login(client, mid)
    try:
        aid = _create_address(client, headers, mid)
        oid = _create_paid_order(client, headers, sku_id, gid, aid)
        _run([("UPDATE orders SET pay_status=0,order_status=1,paid_at=NULL,created_at=NOW()-INTERVAL 15 MINUTE "
               "WHERE id=%s", (oid,))])
        r = client.post(f"/api/v1/shop/pay/{oid}", headers=headers, json={"payType": 1})
        assert r.json()["code"] == 3006, r.text
        row = _q1("SELECT order_status,canceled_at FROM orders WHERE id=%s", (oid,))
        assert row["order_status"] == 5 and row["canceled_at"]
        assert _q1("SELECT stock FROM goods_sku WHERE id=%s", (sku_id,))["stock"] == snap["sku_stock"]
        logs = _qall("SELECT action FROM order_logs WHERE order_id=%s", (oid,))
        assert any(x["action"] == "取消订单" for x in logs)
    finally:
        _cleanup_member(mid)
        _restore_snapshot(snap)


def test_shop_after_sale_flow(client):
    gid = 1
    sku_id = _q1("SELECT id FROM goods_sku WHERE goods_id=%s ORDER BY id LIMIT 1", (gid,))["id"]
    price = float(_q1("SELECT price FROM goods_sku WHERE id=%s", (sku_id,))["price"])
    snap = _stock_snapshot(gid)
    mid = _create_member()
    headers = _login(client, mid)
    try:
        aid = _create_address(client, headers, mid)
        oid = _create_paid_order(client, headers, sku_id, gid, aid)

        r = client.post("/api/v1/shop/after-sales", headers=headers,
                        json={"orderId": oid, "type": 2, "reason": "想退货", "amount": price})
        assert r.json()["code"] != 0
        r = client.post("/api/v1/shop/after-sales", headers=headers,
                        json={"orderId": oid, "type": 1, "reason": "拍错了不想要", "amount": price})
        assert r.json()["code"] == 0, r.text
        asid = r.json()["data"]["id"]

        od = client.get(f"/api/v1/shop/orders/{oid}", headers=headers).json()["data"]
        assert od["orderStatus"] == 6
        lst = client.get("/api/v1/shop/after-sales", headers=headers).json()["data"]
        assert any(x["id"] == asid for x in lst["list"])

        r = client.post("/api/v1/shop/after-sales", headers=headers,
                        json={"orderId": oid, "type": 1, "reason": "重复申请", "amount": price})
        assert r.json()["code"] != 0

        r = client.post(f"/api/v1/shop/after-sales/{asid}/cancel", headers=headers)
        assert r.json()["code"] == 0, r.text
        asd = client.get(f"/api/v1/shop/after-sales/{asid}", headers=headers).json()["data"]
        assert asd["status"] == 4
        od = client.get(f"/api/v1/shop/orders/{oid}", headers=headers).json()["data"]
        assert od["orderStatus"] == 2

        r = client.post(f"/api/v1/shop/after-sales/{asid}/cancel", headers=headers)
        assert r.json()["code"] != 0
    finally:
        _cleanup_member(mid)
        _restore_snapshot(snap)


def test_shop_checkout_cart_preview_and_token_guards(client):
    """C 端结算页依赖的三条服务端契约：①购物车模式只结算已勾选行 ②快照不一致 3002 ③previewToken 一次性"""
    gid = 1
    skus = _qall("SELECT id FROM goods_sku WHERE goods_id=%s ORDER BY id LIMIT 2", (gid,))
    assert len(skus) >= 2, "演示商品需至少 2 个 SKU 才能覆盖部分勾选场景"
    snap = _stock_snapshot(gid)
    mid = _create_member()
    headers = _login(client, mid)
    try:
        aid = _create_address(client, headers, mid)
        aid2 = client.post("/api/v1/shop/addresses", headers=headers, json={
            "receiverName": f"备用{mid}",
            "receiverPhone": _q1("SELECT phone FROM members WHERE id=%s", (mid,))["phone"],
            "province": "示例市", "city": "示例市", "district": "示例区",
            "detail": "备用路9号", "isDefault": 0,
        })
        assert aid2.json()["code"] == 0, aid2.text
        aid2 = aid2.json()["data"]["id"]

        for sku in skus:
            r = client.post("/api/v1/shop/cart", headers=headers,
                            json={"goodsId": gid, "skuId": sku["id"], "quantity": 1})
            assert r.json()["code"] == 0, r.text
        cart = client.get("/api/v1/shop/cart", headers=headers).json()["data"]
        assert len(cart["list"]) == 2 and cart["selectedCount"] == 2
        keep_id, off_id = cart["list"][0]["id"], cart["list"][1]["id"]
        r = client.put("/api/v1/shop/cart/selected", headers=headers, json={"ids": [off_id], "selected": 0})
        assert r.json()["code"] == 0, r.text

        # ① 购物车结算不带 cartIds → 只取服务端 selected=1 的行
        p = client.post("/api/v1/shop/orders/preview", headers=headers,
                        json={"type": "cart", "addressId": aid})
        assert p.json()["code"] == 0, p.text
        data = p.json()["data"]
        assert len(data["items"]) == 1 and data["items"][0]["skuId"] == cart["list"][0]["skuId"]
        assert data["addressId"] == aid and data["previewToken"]
        token = data["previewToken"]

        # ② 提交时改地址（与快照不一致）→ 3002，且 token 未被消耗
        bad = client.post("/api/v1/shop/orders", headers=headers, json={
            "previewToken": token, "addressId": aid2, "payType": 1,
            "couponId": None, "pointsUsed": 0, "buyerMessage": "",
        })
        assert bad.json()["code"] == 3002, bad.text

        # ③ 快照校验失败会消耗该 token → 重新 preview 换票后正常下单，再重复提交同一票 → 3006
        p2 = client.post("/api/v1/shop/orders/preview", headers=headers,
                         json={"type": "cart", "addressId": aid})
        assert p2.json()["code"] == 0, p2.text
        token = p2.json()["data"]["previewToken"]
        ok = client.post("/api/v1/shop/orders", headers=headers, json={
            "previewToken": token, "addressId": aid, "payType": 2,
            "couponId": None, "pointsUsed": 0, "buyerMessage": "S3 结算冒烟",
        })
        assert ok.json()["code"] == 0, ok.text
        oid = ok.json()["data"]["id"]
        again = client.post("/api/v1/shop/orders", headers=headers, json={
            "previewToken": token, "addressId": aid, "payType": 2,
            "couponId": None, "pointsUsed": 0, "buyerMessage": "重复提交",
        })
        assert again.json()["code"] == 3006, again.text

        row = _q1("SELECT pay_type,buyer_message,order_source,receiver_address FROM orders WHERE id=%s", (oid,))
        assert row["pay_type"] == 2 and row["buyer_message"] == "S3 结算冒烟"
        assert row["order_source"] == "h5" and row["receiver_address"].startswith("示例市")

        # ④ 下单成功后仅清除被结算的车行，未勾选项仍在
        after = client.get("/api/v1/shop/cart", headers=headers).json()["data"]
        left = [c["id"] for c in after["list"]]
        assert off_id in left and keep_id not in left
    finally:
        _cleanup_member(mid)
        _restore_snapshot(snap)


def test_shop_after_sale_return_logistics(client, admin_headers):
    gid = 2
    sku_id = _q1("SELECT id FROM goods_sku WHERE goods_id=%s ORDER BY id LIMIT 1", (gid,))["id"]
    price = float(_q1("SELECT price FROM goods_sku WHERE id=%s", (sku_id,))["price"])
    snap = _stock_snapshot(gid)
    mid = _create_member()
    headers = _login(client, mid)
    try:
        aid = _create_address(client, headers, mid)
        oid = _create_paid_order(client, headers, sku_id, gid, aid)
        ship = client.post(f"/api/v1/orders/{oid}/ship", headers=admin_headers,
                           json={"logisticsCompany": "众通快递", "logisticsNo": f"ZT{_tag()}"})
        assert ship.json()["code"] == 0, ship.text

        r = client.post("/api/v1/shop/after-sales", headers=headers,
                        json={"orderId": oid, "type": 2, "reason": "商品有质量问题", "amount": price})
        assert r.json()["code"] == 0, r.text
        asid = r.json()["data"]["id"]

        r = client.post(f"/api/v1/after-sales/{asid}/audit", headers=admin_headers,
                        json={"agree": True, "handleNote": "同意退货"})
        assert r.json()["code"] == 0, r.text
        ad = client.get(f"/api/v1/shop/after-sales/{asid}", headers=headers).json()["data"]
        assert ad["status"] == 2

        r = client.post(f"/api/v1/shop/after-sales/{asid}/logistics", headers=headers,
                        json={"returnLogisticsCompany": "速达速运", "returnLogisticsNo": f"EX{_tag()}"})
        assert r.json()["code"] == 0, r.text
        arow = _q1("SELECT return_logistics_company,return_logistics_no FROM after_sales WHERE id=%s", (asid,))
        assert arow["return_logistics_company"] == "速达速运"

        r = client.post(f"/api/v1/after-sales/{asid}/confirm-receipt", headers=admin_headers)
        assert r.json()["code"] == 0, r.text
        ad = client.get(f"/api/v1/shop/after-sales/{asid}", headers=headers).json()["data"]
        assert ad["status"] == 3
        od = client.get(f"/api/v1/shop/orders/{oid}", headers=headers).json()["data"]
        assert od["orderStatus"] == 5 and "again" in od["actions"]
    finally:
        _cleanup_member(mid)
        _restore_snapshot(snap)
