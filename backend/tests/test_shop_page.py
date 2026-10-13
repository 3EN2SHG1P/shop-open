def _q1(sql, params=()):
    import asyncio

    import aiomysql
    from aiomysql.cursors import DictCursor

    from core.config import config

    async def run():
        conn = await aiomysql.connect(
            host=config.db_host, port=config.db_port, user=config.db_user,
            password=config.db_password, db=config.db_name, charset=config.db_charset,
            autocommit=True, cursorclass=DictCursor,
        )
        try:
            cur = await conn.cursor()
            await cur.execute(sql, params)
            return await cur.fetchone()
        finally:
            conn.close()

    return asyncio.run(run())


def _create_member():
    import asyncio
    import re
    import uuid

    import aiomysql
    import bcrypt
    from aiomysql.cursors import DictCursor

    from core.config import config

    digits = re.sub(r"\D", "", uuid.uuid4().hex)
    phone = "13" + digits[:9]

    async def run():
        conn = await aiomysql.connect(
            host=config.db_host, port=config.db_port, user=config.db_user,
            password=config.db_password, db=config.db_name, charset=config.db_charset,
            autocommit=True, cursorclass=DictCursor,
        )
        try:
            cur = await conn.cursor()
            await cur.execute(
                "INSERT INTO members (nickname,phone,password_hash,points,status,registered_at) "
                "VALUES (%s,%s,%s,0,1,'2026-01-01 00:00:00')",
                (f"页面测试{phone[-4:]}", phone, bcrypt.hashpw(b"123456", bcrypt.gensalt()).decode("utf-8")),
            )
            return cur.lastrowid
        finally:
            conn.close()

    return asyncio.run(run())


def _login(client, mid: int):
    phone = _q1("SELECT phone FROM members WHERE id=%s", (mid,))["phone"]
    r = client.post("/api/v1/shop/auth/login", json={"phone": phone, "password": "123456"})
    assert r.json()["code"] == 0, r.text
    return {"Authorization": "Bearer " + r.json()["data"]["token"]}


def _cleanup_member(mid: int):
    import asyncio

    import aiomysql
    from aiomysql.cursors import DictCursor

    from core.config import config

    async def run():
        conn = await aiomysql.connect(
            host=config.db_host, port=config.db_port, user=config.db_user,
            password=config.db_password, db=config.db_name, charset=config.db_charset,
            autocommit=True, cursorclass=DictCursor,
        )
        try:
            cur = await conn.cursor()
            oids = []
            await cur.execute("SELECT id FROM orders WHERE member_id=%s", (mid,))
            for r in await cur.fetchall():
                oids.append(r["id"])
            for oid in oids:
                await cur.execute("DELETE FROM after_sales WHERE order_id=%s", (oid,))
                await cur.execute("DELETE FROM order_logs WHERE order_id=%s", (oid,))
                await cur.execute("DELETE FROM order_items WHERE order_id=%s", (oid,))
            await cur.execute("DELETE FROM after_sales WHERE member_id=%s", (mid,))
            await cur.execute("DELETE FROM goods_comments WHERE member_id=%s", (mid,))
            await cur.execute("DELETE FROM coupon_receive WHERE member_id=%s", (mid,))
            await cur.execute("DELETE FROM member_address WHERE member_id=%s", (mid,))
            await cur.execute("DELETE FROM member_cart WHERE member_id=%s", (mid,))
            await cur.execute("DELETE FROM member_logs WHERE member_id=%s", (mid,))
            await cur.execute("DELETE FROM points_logs WHERE member_id=%s", (mid,))
            await cur.execute("DELETE FROM orders WHERE member_id=%s", (mid,))
            await cur.execute("DELETE FROM members WHERE id=%s", (mid,))
        finally:
            conn.close()

    asyncio.run(run())


def test_guest_pages(client):
    for url in ["/api/v1/shop/home", "/api/v1/shop/notices", "/api/v1/shop/categories",
                "/api/v1/shop/brands", "/api/v1/shop/specs"]:
        r = client.get(url)
        assert r.json()["code"] == 0, r.text
    r = client.get("/api/v1/shop/goods", params={"page": 1, "pageSize": 10})
    assert r.json()["code"] == 0 and len(r.json()["data"]["list"]) > 0
    r = client.get("/api/v1/shop/goods/1")
    assert r.json()["code"] == 0 and r.json()["data"]["id"] == 1
    assert r.json()["data"].get("detailHtml")
    r = client.get("/api/v1/shop/goods/1/comments")
    assert r.json()["code"] == 0
    r = client.post("/api/v1/shop/goods/1/visit")
    assert r.json()["code"] == 0
    r = client.get("/api/v1/shop/goods/6")
    assert r.json()["code"] == 0
    d6 = r.json()["data"]
    assert d6["specs"] == [], d6["specs"]
    assert len(d6["skus"]) >= 1, "无规格商品必须返回默认 SKU（否则前端无法加购）"
    assert d6["skus"][0]["stock"] > 0 and d6["skus"][0]["specText"] == "", d6["skus"][0]
    r = client.get("/api/v1/shop/ads")
    assert r.json()["code"] == 0


def test_shop_address_cart_crud(client):
    mid = _create_member()
    headers = _login(client, mid)
    try:
        base = {
            "receiverName": "收货人", "receiverPhone": _q1("SELECT phone FROM members WHERE id=%s", (mid,))["phone"],
            "province": "示例市", "city": "示例市", "district": "示例区", "detail": "科技路1号", "isDefault": 1,
        }
        r = client.post("/api/v1/shop/addresses", headers=headers, json=base)
        assert r.json()["code"] == 0, r.text
        aid1 = r.json()["data"]["id"]
        base2 = dict(base, detail="望京街2号", isDefault=0)
        r = client.post("/api/v1/shop/addresses", headers=headers, json=base2)
        aid2 = r.json()["data"]["id"]
        assert aid2 != aid1

        r = client.put(f"/api/v1/shop/addresses/{aid2}", headers=headers, json=dict(base2, detail="编辑后的新地址"))
        assert r.json()["code"] == 0, r.text
        row = _q1("SELECT detail FROM member_address WHERE id=%s", (aid2,))
        assert row["detail"] == "编辑后的新地址"

        r = client.put(f"/api/v1/shop/addresses/{aid2}/default", headers=headers)
        assert r.json()["code"] == 0, r.text
        assert _q1("SELECT is_default FROM member_address WHERE id=%s", (aid1,))["is_default"] == 0
        assert _q1("SELECT is_default FROM member_address WHERE id=%s", (aid2,))["is_default"] == 1

        r = client.get("/api/v1/shop/regions")
        assert r.json()["code"] == 0

        sku1 = _q1("SELECT id FROM goods_sku WHERE goods_id=1 ORDER BY id LIMIT 1")["id"]
        sku2 = _q1("SELECT id FROM goods_sku WHERE goods_id=2 ORDER BY id LIMIT 1")["id"]
        cid = None
        for sku in (sku1, sku2):
            r = client.post("/api/v1/shop/cart", headers=headers, json={"goodsId": 1 if sku == sku1 else 2, "skuId": sku, "quantity": 1})
            assert r.json()["code"] == 0, r.text
        r = client.get("/api/v1/shop/cart", headers=headers)
        assert r.json()["code"] == 0
        cid = _q1("SELECT id FROM member_cart WHERE member_id=%s ORDER BY id LIMIT 1", (mid,))["id"]
        r = client.put(f"/api/v1/shop/cart/{cid}", headers=headers, json={"quantity": 3})
        assert r.json()["code"] == 0, r.text
        r = client.put("/api/v1/shop/cart/selected", headers=headers, json={"ids": [cid], "selected": 0})
        assert r.json()["code"] == 0, r.text
        r = client.delete(f"/api/v1/shop/cart/{cid}", headers=headers)
        assert r.json()["code"] == 0, r.text
        r = client.delete("/api/v1/shop/cart", headers=headers)
        assert r.json()["code"] == 0, r.text

        r = client.delete(f"/api/v1/shop/addresses/{aid1}", headers=headers)
        assert r.json()["code"] == 0, r.text
        r = client.delete(f"/api/v1/shop/addresses/{aid2}", headers=headers)
        assert r.json()["code"] == 0, r.text
        data = client.get("/api/v1/shop/addresses", headers=headers).json()["data"]
        assert len(data["list"]) == 0
    finally:
        _cleanup_member(mid)
