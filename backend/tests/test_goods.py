import asyncio
import uuid

from core.config import config


def _tag():
    return uuid.uuid4().hex[:10]


def _exec_sqls(sqls: list[tuple[str, tuple]]):
    import aiomysql

    async def run():
        conn = await aiomysql.connect(
            host=config.db_host, port=config.db_port, user=config.db_user,
            password=config.db_password, db=config.db_name, charset=config.db_charset,
            autocommit=True,
        )
        try:
            cur = await conn.cursor()
            for sql, params in sqls:
                await cur.execute(sql, params)
        finally:
            conn.close()

    asyncio.run(run())


def _find(datas, key, value):
    return next((x for x in datas if x.get(key) == value), None)


def test_category_brand_crud(client, admin_headers):
    tag = _tag()
    cat_id = brand_id = None
    try:
        r = client.post("/api/v1/categories", json={"name": f"测试分类-{tag}", "parent_id": 0, "sort": 0, "is_show": 1}, headers=admin_headers)
        assert r.status_code == 200 and r.json()["code"] == 0, r.text
        cat_id = r.json()["data"]["id"]

        r = client.get("/api/v1/categories", headers=admin_headers)
        assert r.json()["code"] == 0, r.text
        tree = r.json()["data"]
        assert _find(tree, "name", f"测试分类-{tag}")

        r = client.put(f"/api/v1/categories/{cat_id}", json={"name": f"测试分类改-{tag}", "parent_id": 0, "sort": 1, "is_show": 1}, headers=admin_headers)
        assert r.json()["code"] == 0

        r = client.post("/api/v1/brands", json={"name": f"测试品牌-{tag}", "logo": "", "description": "t", "sort": 0}, headers=admin_headers)
        assert r.json()["code"] == 0, r.text
        brand_id = r.json()["data"]["id"]

        r = client.put(f"/api/v1/brands/{brand_id}/status?status=0", headers=admin_headers)
        assert r.json()["code"] == 0
        brands = client.get("/api/v1/brands?status=0", headers=admin_headers).json()["data"]
        assert _find(brands["list"], "name", f"测试品牌-{tag}")
    finally:
        if brand_id:
            client.delete(f"/api/v1/brands/{brand_id}", headers=admin_headers)
        if cat_id:
            client.delete(f"/api/v1/categories/{cat_id}", headers=admin_headers)


def test_spec_attr_crud(client, admin_headers):
    tag = _tag()
    spec_id = attr_id = None
    try:
        r = client.post("/api/v1/goods/specs", json={"name": f"颜色-{tag}", "category_id": 0, "sort": 0, "values": [{"value": "红"}, {"value": "蓝"}]}, headers=admin_headers)
        assert r.json()["code"] == 0, r.text
        spec_id = r.json()["data"]["id"]

        specs = client.get("/api/v1/goods/specs", headers=admin_headers).json()["data"]
        node = _find(specs, "name", f"颜色-{tag}")
        assert node and len(node["values"]) == 2

        r = client.post("/api/v1/goods/attrs", json={"name": f"材质-{tag}", "category_id": 0, "sort": 0, "values": [{"value": "棉"}]}, headers=admin_headers)
        assert r.json()["code"] == 0, r.text
        attr_id = r.json()["data"]["id"]

        r = client.put(f"/api/v1/goods/specs/{spec_id}", json={"name": f"颜色-{tag}", "category_id": 0, "sort": 0, "values": [{"value": "红"}, {"value": "绿"}]}, headers=admin_headers)
        assert r.json()["code"] == 0
        specs = client.get("/api/v1/goods/specs", headers=admin_headers).json()["data"]
        node = _find(specs, "name", f"颜色-{tag}")
        assert {v["value"] for v in node["values"]} == {"红", "绿"}
    finally:
        if attr_id:
            client.delete(f"/api/v1/goods/attrs/{attr_id}", headers=admin_headers)
        if spec_id:
            client.delete(f"/api/v1/goods/specs/{spec_id}", headers=admin_headers)


def test_goods_full_crud(client, admin_headers):
    tag = _tag()
    cat_id = brand_id = spec_id = goods_id = None
    try:
        cat_id = client.post("/api/v1/categories", json={"name": f"分类-{tag}", "parent_id": 0, "sort": 0, "is_show": 1}, headers=admin_headers).json()["data"]["id"]
        brand_id = client.post("/api/v1/brands", json={"name": f"品牌-{tag}", "logo": "", "description": "", "sort": 0}, headers=admin_headers).json()["data"]["id"]
        spec_id = client.post("/api/v1/goods/specs", json={"name": f"规格-{tag}", "category_id": 0, "sort": 0, "values": [{"value": "M"}, {"value": "L"}]}, headers=admin_headers).json()["data"]["id"]

        specs = client.get("/api/v1/goods/specs", headers=admin_headers).json()["data"]
        node = _find(specs, "name", f"规格-{tag}")
        vid1, vid2 = node["values"][0]["id"], node["values"][1]["id"]

        payload = {
            "name": f"测试商品-{tag}",
            "subtitle": "子标题",
            "category_id": cat_id,
            "brand_id": brand_id,
            "spu_code": f"SPU-{tag}",
            "unit": "件",
            "market_price": 199.0,
            "price": 129.0,
            "cost_price": 80.0,
            "warn_stock": 5,
            "status": 1,
            "is_recommend": 1,
            "is_hot": 0,
            "is_new": 1,
            "detail_html": "<p>hello</p>",
            "seo_title": "seo标题",
            "seo_keywords": "kw",
            "seo_desc": "desc",
            "images": [{"url": "http://x/a.jpg", "sort": 1, "type": 1}],
            "skus": [
                {"sku_code": f"{tag}-M", "price": 129.0, "stock": 10, "image": "", "spec_values": [{"spec_id": spec_id, "spec_value_id": vid1}]},
                {"sku_code": f"{tag}-L", "price": 139.0, "stock": 8, "image": "", "spec_values": [{"spec_id": spec_id, "spec_value_id": vid2}]},
            ],
        }
        r = client.post("/api/v1/goods", json=payload, headers=admin_headers)
        assert r.status_code == 200 and r.json()["code"] == 0, r.text
        goods_id = r.json()["data"]["id"]

        lst = client.get(f"/api/v1/goods?keyword={tag}", headers=admin_headers).json()["data"]
        assert lst["total"] >= 1
        row = lst["list"][0]
        assert row["name"] == f"测试商品-{tag}"
        assert row["categoryId"] == cat_id
        assert row["statusText"] == "上架"
        assert isinstance(row["price"], float)

        detail = client.get(f"/api/v1/goods/{goods_id}", headers=admin_headers).json()["data"]
        assert detail["name"] == f"测试商品-{tag}"
        assert len(detail["images"]) == 1
        assert len(detail["skus"]) == 2
        assert detail["seo"]["title"] == "seo标题"
        assert detail["skus"][0]["specValues"][0]["specValueId"] == vid1

        payload["name"] = f"测试商品改-{tag}"
        payload["skus"].append({"sku_code": f"{tag}-XL", "price": 149.0, "stock": 5, "image": "", "spec_values": []})
        r = client.put(f"/api/v1/goods/{goods_id}", json=payload, headers=admin_headers)
        assert r.json()["code"] == 0, r.text
        detail = client.get(f"/api/v1/goods/{goods_id}", headers=admin_headers).json()["data"]
        assert len(detail["skus"]) == 3

        r = client.put("/api/v1/goods/batch/status", json={"ids": [goods_id], "status": 0}, headers=admin_headers)
        assert r.json()["code"] == 0
        lst = client.get(f"/api/v1/goods?status=0&keyword={tag}", headers=admin_headers).json()["data"]
        assert any(x["id"] == goods_id for x in lst["list"])

        r = client.put("/api/v1/goods/batch/status", json={"ids": [goods_id], "status": 1}, headers=admin_headers)
        assert r.json()["code"] == 0

        exp = client.get("/api/v1/goods/export?keyword={0}".format(tag), headers=admin_headers)
        assert exp.status_code == 200
        assert "text/csv" in exp.headers.get("content-type", "")
        assert f"测试商品改-{tag}".encode("utf-8") in exp.content
    finally:
        if goods_id:
            client.delete(f"/api/v1/goods/{goods_id}", headers=admin_headers)
        if spec_id:
            client.delete(f"/api/v1/goods/specs/{spec_id}", headers=admin_headers)
        if brand_id:
            client.delete(f"/api/v1/brands/{brand_id}", headers=admin_headers)
        if cat_id:
            client.delete(f"/api/v1/categories/{cat_id}", headers=admin_headers)


def test_comment_audit_reply(client, admin_headers):
    tag = _tag()
    goods_id = comment_id = None
    try:
        goods_id = client.post(
            "/api/v1/goods",
            json={"name": f"评论商品-{tag}", "status": 1, "images": [], "skus": [{"sku_code": f"{tag}-S", "price": 10.0, "stock": 1, "image": "", "spec_values": []}]},
            headers=admin_headers,
        ).json()["data"]["id"]

        _exec_sqls([
            ("INSERT INTO goods_comments (goods_id, member_id, score, content, status) VALUES (%s,%s,%s,%s,%s)", (goods_id, 0, 5, f"好评-{tag}", 1)),
        ])

        lst = client.get(f"/api/v1/goods/comments?goods_id={goods_id}", headers=admin_headers).json()["data"]
        assert lst["total"] >= 1 and "goodRate" in lst
        target = next(x for x in lst["list"] if x["content"] == f"好评-{tag}")
        comment_id = target["id"]

        r = client.put(f"/api/v1/goods/comments/{comment_id}/audit", json={"pass": False}, headers=admin_headers)
        assert r.json()["code"] == 0
        lst = client.get(f"/api/v1/goods/comments?goods_id={goods_id}&status=2", headers=admin_headers).json()["data"]
        assert any(x["id"] == comment_id for x in lst["list"])

        reply = f"感谢您的评价-{tag}"
        r = client.post(f"/api/v1/goods/comments/{comment_id}/reply", json={"content": reply}, headers=admin_headers)
        assert r.json()["code"] == 0
        lst = client.get(f"/api/v1/goods/comments?goods_id={goods_id}", headers=admin_headers).json()["data"]
        target = next(x for x in lst["list"] if x["id"] == comment_id)
        assert target["reply"] == reply

        r = client.delete(f"/api/v1/goods/comments/{comment_id}", headers=admin_headers)
        assert r.json()["code"] == 0
        comment_id = None
    finally:
        if comment_id:
            client.delete(f"/api/v1/goods/comments/{comment_id}", headers=admin_headers)
        if goods_id:
            client.delete(f"/api/v1/goods/{goods_id}", headers=admin_headers)
