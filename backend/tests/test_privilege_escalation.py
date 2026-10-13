"""越权（提权）回归测试。

这组用例锁住四条真实存在的提权链路，防止被后续重构悄悄改回去：

1. **改自己的资料顺手给自己挂超管角色**
   check_own_admin 允许管理员改自己的资料（合理），而 AdminUpdate.role_ids 会被
   全量覆盖写回 —— 于是改资料时带上 role_ids=[超管] 就能提权。
   修复：routers/permission.py 里用 strip_role_ids 丢弃普通管理员提交的 role_ids。

2. **把自己的角色抬成超管级 data_scope**
   RoleSave.data_scope 默认曾被设为 3（超管级），update_role 又会无条件写回，
   因此省略 permission_ids 提交 {role_name, role_key} 就能把自己变超管，
   之后所有闸门都会放行。修复：data_scope 默认改为 1，且角色写操作整体收紧到超管。

3. **复制/篡改权限资源**
   copy_role 可克隆超管角色、update_resource 可把某条资源的 code 改写成别的权限码。
   修复：这些写操作同样要求超管。

4. **用 dept_id 参数跨部门看管理员列表**
   list_admins 只校验了 permission:list 权限码，完全不叠加 data_scope，
   于是 data_scope=1/2 的账号传 `dept_id=<其他部门>` 就能列出全部管理员账号
   （进而拿到改密、授权的入口）。
   修复：services/permission.py 里按 data_scope 叠加 dept_id / id 维度条件。

设计要点：管理端前端**总是**会提交 role_ids / permission_ids（哪怕一个都没勾），
所以这里刻意模拟「传了非空数组」的真实请求；若只测「完全不传字段」，
会漏掉真实场景下普通管理员被误伤的问题。
"""

import pytest

PROBE_ROLE_KEY = "esc_probe_role"
PROBE_ROLE_KEY_2 = "esc_probe_role_2"
PROBE_ADMIN = "esc_probe_admin"
PROBE_TARGET = "esc_probe_target"
PROBE_PWD = "esc123456"
DENIED = (403, 4001)  # core/errors.py 的 no_permission → HTTP 403 / body.code 4001


def _roles(client, headers):
    r = client.get("/api/v1/permission/roles", headers=headers)
    assert r.status_code == 200 and r.json()["code"] == 0, r.text
    return r.json()["data"]


def _role_by_key(client, headers, key):
    return next((x for x in _roles(client, headers) if x["roleKey"] == key), None)


def _own_role_ids(client, headers, admin_id):
    r = client.get(f"/api/v1/permission/admins/{admin_id}", headers=headers)
    assert r.status_code == 200 and r.json()["code"] == 0, r.text
    return r.json()["data"]["roleIds"]


def _assert_denied(resp, what):
    """必须是「明确被拒绝」，而不是 500/422/网络异常之类的巧合。"""
    assert resp.status_code == DENIED[0], f"{what} 应返回 403，实际 {resp.status_code}: {resp.text}"
    assert resp.json()["code"] == DENIED[1], f"{what} 应返回业务码 4001，实际 {resp.text}"


def _purge(client, admin_headers):
    """清掉上一轮残留的探针数据。顺序很重要：先删管理员，再删角色，
    否则角色会因仍被引用而删不掉，下一轮建同名角色时报「标识已存在」。"""
    for name in (PROBE_ADMIN, PROBE_TARGET):
        r = client.get("/api/v1/permission/admins", params={"keyword": name}, headers=admin_headers)
        if r.status_code == 200:
            for a in r.json()["data"]["list"]:
                if a["username"] == name:
                    client.delete(f"/api/v1/permission/admins/{a['id']}", headers=admin_headers)
    for key in (PROBE_ROLE_KEY, PROBE_ROLE_KEY_2):
        for x in _roles(client, admin_headers):
            if x["roleKey"] == key:
                client.delete(f"/api/v1/permission/roles/{x['id']}", headers=admin_headers)


@pytest.fixture
def probe(client, admin_headers):
    """造一个 data_scope=2（非超管）但持有全部权限码的管理员。

    它有 permission:add / permission:edit，因此能调通这些写接口；
    但 data_scope<3，所以任何涉及授权的操作都应被拦下。
    """
    _purge(client, admin_headers)

    super_role = _role_by_key(client, admin_headers, "admin")
    assert super_role is not None, "未找到 role_key=admin 的超管角色，请先执行 seed.runner base"
    assert super_role["permissionIds"], "超管角色没有任何权限码，用例将无法验证（seed 是否跑完整？）"

    created = {}
    try:
        r = client.post(
            "/api/v1/permission/roles",
            json={
                "role_name": "越权探针角色",
                "role_key": PROBE_ROLE_KEY,
                "description": "回归测试临时角色，跑完即删",
                "data_scope": 2,  # 关键：非超管
                "status": 1,
                "permission_ids": super_role["permissionIds"],
            },
            headers=admin_headers,
        )
        assert r.status_code == 200 and r.json()["code"] == 0, r.text
        created["role_id"] = r.json()["data"]["id"]

        r = client.post(
            "/api/v1/permission/admins",
            json={
                "username": PROBE_ADMIN,
                "password": PROBE_PWD,
                "real_name": "越权探针",
                "status": 1,
                "role_ids": [created["role_id"]],
            },
            headers=admin_headers,
        )
        assert r.status_code == 200 and r.json()["code"] == 0, r.text
        created["admin_id"] = r.json()["data"]["id"]

        r = client.post("/api/v1/auth/login", json={"username": PROBE_ADMIN, "password": PROBE_PWD})
        assert r.status_code == 200 and r.json()["code"] == 0, r.text
        created["headers"] = {"Authorization": f"Bearer {r.json()['data']['token']}"}
        created["super_role_id"] = super_role["id"]

        yield created
    finally:
        if created.get("admin_id"):
            r = client.delete(f"/api/v1/permission/admins/{created['admin_id']}", headers=admin_headers)
            assert r.status_code == 200, f"清理探针管理员失败（会污染后续运行）：{r.text}"
        if created.get("role_id"):
            r = client.delete(f"/api/v1/permission/roles/{created['role_id']}", headers=admin_headers)
            assert r.status_code == 200, f"清理探针角色失败（会污染后续运行）：{r.text}"
        _purge(client, admin_headers)


def test_probe_does_have_write_permission(client, probe):
    """前置校验：探针确实持有 permission:edit，否则后面所有断言都没有意义。"""
    r = client.get("/api/v1/auth/me", headers=probe["headers"])
    assert r.status_code == 200 and r.json()["code"] == 0, r.text
    codes = r.json()["data"]["permissions"]
    assert {"permission:list", "permission:edit"} <= set(codes)


def test_probe_is_not_super_admin(client, probe):
    """前置校验：探针的 data_scope 必须小于 3，否则它本来就是超管，用例失去区分度。"""
    r = client.get("/api/v1/auth/me", headers=probe["headers"])
    assert r.json()["data"]["dataScope"] < 3


def test_grant_self_super_role_is_dropped(client, admin_headers, probe):
    """链路①：改自己资料时携带的超管角色必须被丢弃——接口成功，但角色没变。"""
    r = client.put(
        f"/api/v1/permission/admins/{probe['admin_id']}",
        json={"real_name": "越权探针", "status": 1, "role_ids": [probe["super_role_id"]]},
        headers=probe["headers"],
    )
    assert r.status_code == 200 and r.json()["code"] == 0, r.text
    assert probe["super_role_id"] not in _own_role_ids(client, admin_headers, probe["admin_id"])


def test_edit_own_profile_with_front_payload_works(client, admin_headers, probe):
    """不误伤：管理端前端总会带上当期勾选的 role_ids，普通管理员必须仍能改自己的资料。"""
    r = client.put(
        f"/api/v1/permission/admins/{probe['admin_id']}",
        json={
            "real_name": "探针改名成功",
            "phone": "10000000004",
            "email": "probe@example.com",
            "status": 1,
            "role_ids": [probe["role_id"]],  # 前端总是提交，这里也一样
        },
        headers=probe["headers"],
    )
    assert r.status_code == 200 and r.json()["code"] == 0, r.text
    # 角色必须原样保留：既不能被清空，也不能被替换成超管角色
    assert _own_role_ids(client, admin_headers, probe["admin_id"]) == [probe["role_id"]]


def test_cannot_create_admin_with_role(client, admin_headers, probe):
    """链路① 的建号版本：普通管理员可以建号，但附带的角色会被丢弃。"""
    r = client.post(
        "/api/v1/permission/admins",
        json={
            "username": "esc_probe_target",
            "password": PROBE_PWD,
            "real_name": "探针建的目标账号",
            "status": 1,
            "role_ids": [probe["super_role_id"]],
        },
        headers=probe["headers"],
    )
    assert r.status_code == 200 and r.json()["code"] == 0, r.text
    target_id = r.json()["data"]["id"]
    try:
        # 用超管视角核查：建号时附带的 role_ids 有没有被 strip_role_ids 丢掉
        assert _own_role_ids(client, admin_headers, target_id) == [], "普通管理员建号时竟然能直接授予角色"
        # 同时验证深度防御：probe 的 data_scope<3，连**看**这个账号都不该被允许。
        # 历史实现里 get_admin 只按 id 查询，任何持 permission:list 的账号都能遍历全部管理员明细。
        r2 = client.get(f"/api/v1/permission/admins/{target_id}", headers=probe["headers"])
        assert r2.status_code == 401 or r2.json().get("code") in (1001, 4001), \
            f"受限管理员仍能读取他人账号详情：{r2.text}"
    finally:
        client.delete(f"/api/v1/permission/admins/{target_id}", headers=admin_headers)


def test_cannot_promote_own_role_data_scope(client, admin_headers, probe):
    """链路②：不得通过改自己角色的 data_scope 把自己抬成超管级。"""
    r = client.put(
        f"/api/v1/permission/roles/{probe['role_id']}",
        # 刻意省略 permission_ids —— 这正是原实现可以被绕过的入口
        json={"role_name": "越权探针角色", "role_key": PROBE_ROLE_KEY, "description": "试图提权", "status": 1},
        headers=probe["headers"],
    )
    _assert_denied(r, "普通管理员修改角色")
    row = _role_by_key(client, admin_headers, PROBE_ROLE_KEY)
    assert row["dataScope"] == 2, "角色的 data_scope 被普通管理员改掉了"


def test_cannot_create_or_copy_privileged_role(client, probe):
    """链路③：不得新建带权限的角色，也不得复制超管角色。"""
    r = client.post(
        "/api/v1/permission/roles",
        json={
            "role_name": "探针自建角色",
            "role_key": PROBE_ROLE_KEY_2,
            "description": "",
            "data_scope": 3,
            "status": 1,
            "permission_ids": probe["super_role_id"] and [1],
        },
        headers=probe["headers"],
    )
    _assert_denied(r, "普通管理员新建角色")
    assert _role_by_key(client, probe["headers"], PROBE_ROLE_KEY_2) is None


def test_admin_list_respects_data_scope(client, admin_headers, probe):
    """链路④：持有 permission:list 但 data_scope<3 的账号，不得用 dept_id 跨部门看人。"""
    listed = client.get(
        "/api/v1/permission/admins", params={"keyword": "admin"}, headers=admin_headers
    )
    assert listed.status_code == 200 and listed.json()["code"] == 0, listed.text
    assert any(a["username"] == "admin" for a in listed.json()["data"]["list"]), (
        "未找到超管账号 admin，请先执行 seed.runner base"
    )

    # 显式指定部门（含总部）时，也不得越出自己的数据范围
    r = client.get("/api/v1/permission/admins", params={"dept_id": 1}, headers=probe["headers"])
    assert r.status_code == 200 and r.json()["code"] == 0, r.text
    usernames = [a["username"] for a in r.json()["data"]["list"]]
    assert "admin" not in usernames, f"受限账号通过 dept_id 看到了超管账号：{usernames}"

    # 不传 dept_id 时同样收敛：探针未分配部门（dept_id 为空），因此只能看到自己
    r2 = client.get("/api/v1/permission/admins", headers=probe["headers"])
    assert r2.status_code == 200 and r2.json()["code"] == 0, r2.text
    ids = [a["id"] for a in r2.json()["data"]["list"]]
    assert ids == [probe["admin_id"]], f"受限账号应只看到自己，实际：{ids}"

    r = client.post(f"/api/v1/permission/roles/{probe['super_role_id']}/copy", headers=probe["headers"])
    _assert_denied(r, "普通管理员复制超管角色")


def test_cannot_tamper_permission_resource(client, probe):
    """链路③：不得通过改权限资源的 code 来给自己造权限。

    这里刻意使用一个**不存在**的资源 id：鉴权发生在查库之前，所以 403 与否足以
    区分「有没有闸门」；同时避免在验证过程中把真实菜单改坏。
    """
    payload = {
        "parent_id": 0,
        "permission_type": "api",
        "name": "探针资源",
        "code": "probe:granted",
        "path": "/api/v1/probe",
        "method": "GET",
        "icon": "",
        "sort": 0,
        "status": 1,
    }
    r = client.put("/api/v1/permission/resources/999999", json=payload, headers=probe["headers"])
    _assert_denied(r, "普通管理员修改权限资源")

    r = client.post("/api/v1/permission/resources", json=payload, headers=probe["headers"])
    _assert_denied(r, "普通管理员新建权限资源")


def test_super_admin_flow_is_unaffected(client, admin_headers, probe):
    """反向用例：超管本人的所有操作必须不受影响，防止修复过度。"""
    r = client.put(
        f"/api/v1/permission/admins/{probe['admin_id']}",
        json={"real_name": "超管改的", "status": 1, "role_ids": [probe["role_id"], probe["super_role_id"]]},
        headers=admin_headers,
    )
    assert r.status_code == 200 and r.json()["code"] == 0, r.text
    assert probe["super_role_id"] in _own_role_ids(client, admin_headers, probe["admin_id"])

    r = client.put(
        f"/api/v1/permission/roles/{probe['role_id']}",
        json={
            "role_name": "超管改的角色",
            "role_key": PROBE_ROLE_KEY,
            "description": "",
            "data_scope": 2,
            "status": 1,
            "permission_ids": [1],
        },
        headers=admin_headers,
    )
    assert r.status_code == 200 and r.json()["code"] == 0, r.text
