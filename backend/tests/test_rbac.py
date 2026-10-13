def test_login_and_me(client, admin_headers):
    r = client.get("/api/v1/auth/me", headers=admin_headers)
    assert r.status_code == 200
    # 必须校验业务码：HTTP 200 也可能是 code!=0 的错误体
    assert r.json()["code"] == 0, r.text
    data = r.json()["data"]
    assert data["username"] == "admin"
    assert "permissions" in data
    assert "goods:list" in data["permissions"]
    assert "permission:list" in data["permissions"]
    assert len(set(data["permissions"])) == len(data["permissions"])


def test_wrong_password(client):
    r = client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"})
    assert r.status_code == 401


def test_no_token_denied(client):
    r = client.get("/api/v1/permission/admins")
    assert r.status_code in (401, 403)


def test_admin_list(client, admin_headers):
    r = client.get("/api/v1/permission/admins", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    assert body["data"]["total"] >= 1
    assert any(u["username"] == "admin" for u in body["data"]["list"])


def test_role_tree(client, admin_headers):
    r = client.get("/api/v1/permission/tree", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["code"] == 0, r.text
    tree = r.json()["data"]
    assert len(tree) >= 8
    names = {n["name"] for n in tree}
    assert {"仪表盘", "商品管理", "订单管理", "用户管理", "权限管理", "操作日志"} <= names


def test_role_list(client, admin_headers):
    r = client.get("/api/v1/permission/roles", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["code"] == 0, r.text
    roles = r.json()["data"]
    keys = {x["roleKey"] for x in roles}
    assert {"admin", "operator"} <= keys
    admin_role = next(x for x in roles if x["roleKey"] == "admin")
    assert admin_role["dataScope"] == 3
    assert len(admin_role["permissionIds"]) > 0


def test_dept_tree(client, admin_headers):
    r = client.get("/api/v1/permission/depts", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["code"] == 0, r.text
    tree = r.json()["data"]
    assert any(n["deptName"] == "总部" for n in tree)


def test_change_password_restore(client, admin_headers, admin_password):
    """用 fixture 提供的口令（而非写死值）走一遍改密码，顺便验证口令来源正确。"""
    r = client.put(
        "/api/v1/auth/password",
        json={"old_password": admin_password, "new_password": admin_password},
        headers=admin_headers,
    )
    assert r.status_code == 200
    # 只断言 200 等于没断言：错误业务码同样返回 200
    assert r.json()["code"] == 0, r.text


def test_login_logs(client, admin_headers):
    r = client.get("/api/v1/permission/login-logs", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["data"]["total"] >= 1
