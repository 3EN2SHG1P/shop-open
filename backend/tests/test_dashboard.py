def _ok(client, headers, url):
    r = client.get(url, headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["code"] == 0, body
    return body["data"]


def test_dashboard_overview_shape(client, admin_headers):
    data = _ok(client, admin_headers, "/api/v1/dashboard/overview")
    stats = data["stats"]
    for k in ("orders", "gmv", "newMembers", "totalGoods", "totalMembers",
              "pendingPayment", "pendingShip", "lowStock"):
        assert k in stats
    assert isinstance(stats["gmv"], (int, float))
    assert isinstance(stats["orders"], int)
    assert isinstance(data["statusDist"], list)
    assert isinstance(data["recentOrders"], list)


def test_dashboard_overview_windows(client, admin_headers):
    d1 = _ok(client, admin_headers, "/api/v1/dashboard/overview?days=1")["stats"]
    d7 = _ok(client, admin_headers, "/api/v1/dashboard/overview?days=7")["stats"]
    d30 = _ok(client, admin_headers, "/api/v1/dashboard/overview?days=30")["stats"]
    assert d7["orders"] >= d1["orders"]
    assert d30["orders"] >= d7["orders"]
    assert d7["newMembers"] >= d1["newMembers"]
    assert d7["gmv"] >= d1["gmv"]


def test_dashboard_trend(client, admin_headers):
    d7 = _ok(client, admin_headers, "/api/v1/dashboard/trend?days=7")
    assert len(d7) == 7
    assert all({"date", "day", "amount", "orders"} <= set(x) for x in d7)
    d30 = _ok(client, admin_headers, "/api/v1/dashboard/trend?days=30")
    assert len(d30) == 30


def test_dashboard_hot_goods(client, admin_headers):
    data = _ok(client, admin_headers, "/api/v1/dashboard/hot-goods?days=30")
    assert isinstance(data, list)
    # 空列表时循环体一次都不执行，必须先断言有数据
    assert len(data) >= 1, "未产生热销榜：请先执行 uv run python -m seed.runner demo"
    for x in data:
        assert {"rank", "goodsName", "sales", "amount"} <= set(x)


def test_dashboard_permission_required(client):
    r = client.get("/api/v1/dashboard/overview")
    assert r.status_code in (401, 403)
