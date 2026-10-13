import asyncio
import uuid

import aiomysql
from aiomysql.cursors import DictCursor

from core.config import config


def _tag():
    return "T" + uuid.uuid4().hex[:8].upper()


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


def _create_member(nickname: str, phone: str, points: int = 0):
    import bcrypt

    pwd = bcrypt.hashpw(b"123456", bcrypt.gensalt()).decode("utf-8")
    _run([
        (
            "INSERT INTO members (nickname,phone,password_hash,points,status,registered_at) "
            "VALUES (%s,%s,%s,%s,1,'2026-01-01 00:00:00')",
            (nickname, phone, pwd, points),
        )
    ])
    row = _q1("SELECT id FROM members WHERE phone=%s", (phone,))
    return row["id"]


def _clean_member(mid: int):
    _run([
        ("DELETE FROM member_logs WHERE member_id=%s", (mid,)),
        ("DELETE FROM points_logs WHERE member_id=%s", (mid,)),
        ("DELETE FROM orders WHERE member_id=%s", (mid,)),
        ("DELETE FROM members WHERE id=%s", (mid,)),
    ])


def test_member_list_and_detail(client, admin_headers):
    r = client.get("/api/v1/members", headers=admin_headers)
    assert r.status_code == 200 and r.json()["code"] == 0, r.text
    data = r.json()["data"]
    assert data["total"] >= 3
    for item in data["list"]:
        assert "nickname" in item and "orderCount" in item

    r = client.get("/api/v1/members?keyword=张小明", headers=admin_headers)
    assert r.json()["code"] == 0
    # 断言必须包含「至少有结果」：空列表时 all(...) 恒为真，这条用例会退化成永远通过
    searched = r.json()["data"]["list"]
    assert len(searched) >= 1, "未搜到会员：请先执行 uv run python -m seed.runner demo"
    assert all("张小明" in x["nickname"] for x in searched)

    r = client.get("/api/v1/members?status=1", headers=admin_headers)
    assert r.json()["code"] == 0
    assert all(x["status"] == 1 for x in r.json()["data"]["list"])

    r = client.get("/api/v1/members?page=1&page_size=2", headers=admin_headers)
    page = r.json()["data"]
    assert len(page["list"]) <= 2 and page["total"] >= 3

    mid = page["list"][0]["id"]
    r = client.get(f"/api/v1/members/{mid}", headers=admin_headers)
    assert r.json()["code"] == 0, r.text
    detail = r.json()["data"]
    assert detail["id"] == mid
    assert isinstance(detail["orders"], list)
    assert isinstance(detail["logs"], list)
    assert "levelName" in detail and "totalConsume" in detail


def test_member_edit_and_status(client, admin_headers):
    tag = _tag()
    phone = "139" + tag[:8]
    mid = _create_member("测试会员" + tag, phone)
    try:
        levels = client.get("/api/v1/member-levels", headers=admin_headers).json()["data"]
        assert levels, "需先有会员等级种子"
        lid = levels[0]["id"]

        r = client.put(
            f"/api/v1/members/{mid}", headers=admin_headers,
            json={"nickname": "改名" + tag, "phone": phone, "email": "a@b.com", "levelId": lid},
        )
        assert r.json()["code"] == 0, r.text
        row = _q1("SELECT nickname,email,level_id FROM members WHERE id=%s", (mid,))
        assert row["nickname"] == "改名" + tag and row["email"] == "a@b.com" and row["level_id"] == lid

        r = client.put(f"/api/v1/members/{mid}/status", headers=admin_headers, json={"status": 0})
        assert r.json()["code"] == 0
        assert _q1("SELECT status FROM members WHERE id=%s", (mid,))["status"] == 0
        r = client.put(f"/api/v1/members/{mid}/status", headers=admin_headers, json={"status": 1})
        assert r.json()["code"] == 0
        assert _q1("SELECT status FROM members WHERE id=%s", (mid,))["status"] == 1

        phone_other = "135" + tag[:8]
        other = _create_member("他人手机" + tag, phone_other)
        try:
            r = client.put(
                f"/api/v1/members/{mid}", headers=admin_headers,
                json={"nickname": "改名" + tag, "phone": phone_other, "levelId": lid},
            )
            assert r.json()["code"] != 0
        finally:
            _clean_member(other)
    finally:
        _clean_member(mid)


def test_member_reset_password(client, admin_headers):
    from core.security import verify_password

    tag = _tag()
    phone = "137" + tag[:8]
    mid = _create_member("密码会员" + tag, phone)
    try:
        r = client.put(f"/api/v1/members/{mid}/reset-password", headers=admin_headers, json={"password": "newpass123"})
        assert r.json()["code"] == 0, r.text
        row = _q1("SELECT password_hash FROM members WHERE id=%s", (mid,))
        assert verify_password("newpass123", row["password_hash"])

        r = client.put(f"/api/v1/members/{mid}/reset-password", headers=admin_headers, json={})
        assert r.json()["code"] == 2001, r.text

        r = client.put(f"/api/v1/members/{mid}/reset-password", headers=admin_headers, json={"password": "reset456"})
        assert r.json()["code"] == 0, r.text
        row = _q1("SELECT password_hash FROM members WHERE id=%s", (mid,))
        assert verify_password("reset456", row["password_hash"])

        logs = _q1("SELECT COUNT(*) AS c FROM member_logs WHERE member_id=%s AND action_type='password'", (mid,))
        assert logs["c"] >= 2
    finally:
        _clean_member(mid)


def test_member_level_create_update(client, admin_headers):
    tag = _tag()
    name = "冒烟等级" + tag
    created_id = None
    try:
        r = client.get("/api/v1/member-levels", headers=admin_headers)
        assert r.json()["code"] == 0
        base_count = len(r.json()["data"])
        assert base_count >= 3
        assert all("memberCount" in x for x in r.json()["data"])

        r = client.post(
            "/api/v1/member-levels", headers=admin_headers,
            json={"levelName": name, "upgradeAmount": 20000, "upgradePoints": 20000,
                  "discountRate": 8.8, "benefits": "88折特惠", "status": 1},
        )
        assert r.json()["code"] == 0, r.text
        created_id = r.json()["data"]["id"]

        r = client.post(
            "/api/v1/member-levels", headers=admin_headers,
            json={"levelName": name, "upgradeAmount": 0, "discountRate": 9},
        )
        assert r.json()["code"] != 0

        rows = client.get("/api/v1/member-levels", headers=admin_headers).json()["data"]
        assert len(rows) == base_count + 1
        found = next(x for x in rows if x["id"] == created_id)
        assert found["levelName"] == name and found["discountRate"] == 8.8

        r = client.put(
            f"/api/v1/member-levels/{created_id}", headers=admin_headers,
            json={"levelName": name + "改", "upgradeAmount": 25000, "upgradePoints": 25000,
                  "discountRate": 8.5, "benefits": "85折", "status": 0},
        )
        assert r.json()["code"] == 0, r.text
        row = _q1("SELECT level_name,discount_rate,status FROM member_level WHERE id=%s", (created_id,))
        assert row["level_name"] == name + "改" and row["status"] == 0
    finally:
        if created_id:
            _run([("DELETE FROM member_level WHERE id=%s", (created_id,))])


def test_member_register_date_filter(client, admin_headers):
    """Bug 1 验收：会员「注册时间」日期范围应匹配 registered_at（不是 created_at）。

    场景：demo seed 中 3 个会员 registered_at='2026-01-01 00:00:00'，created_at 约 seed 时刻 2026-09-xx。
    修复前：2026-09 范围按 created_at 仍能命中（错位）；修复后应按 registered_at 返回 0。
    """
    # 全量（无日期筛选）应至少 3 条
    r = client.get("/api/v1/members", headers=admin_headers)
    assert r.status_code == 200 and r.json()["code"] == 0
    total_all = r.json()["data"]["total"]
    assert total_all >= 3

    # 关键断言 1：2026-09-04~2026-09-17（用户截图范围）按 registered_at 应 0
    r = client.get(
        "/api/v1/members?start_date=2026-09-04&end_date=2026-09-17", headers=admin_headers
    )
    assert r.status_code == 200 and r.json()["code"] == 0
    assert r.json()["data"]["total"] == 0, (
        f"修复后 2026-09 范围应按 registered_at 返回 0（demo 数据 registered_at=2026-01-01），"
        f"实际返回 {r.json()['data']['total']}"
    )

    # 关键断言 2：2026-01-01~2026-01-31 应命中 3 条
    r = client.get(
        "/api/v1/members?start_date=2026-01-01&end_date=2026-01-31", headers=admin_headers
    )
    assert r.json()["code"] == 0
    assert r.json()["data"]["total"] == total_all, (
        f"2026-01 范围应命中全部 {total_all} 条，实际 {r.json()['data']['total']}"
    )

    # 关键断言 3：2025 全年应 0
    r = client.get(
        "/api/v1/members?start_date=2025-01-01&end_date=2025-12-31", headers=admin_headers
    )
    assert r.json()["code"] == 0
    assert r.json()["data"]["total"] == 0

    # 关键断言 4：仅 start 边界（2026-01-02 起）应 0
    r = client.get("/api/v1/members?start_date=2026-01-02", headers=admin_headers)
    assert r.json()["code"] == 0
    assert r.json()["data"]["total"] == 0

    # 关键断言 5：仅 end 边界（2026-01-01 止）应 3
    r = client.get("/api/v1/members?end_date=2026-01-01", headers=admin_headers)
    assert r.json()["code"] == 0
    assert r.json()["data"]["total"] == total_all


def test_points_logs_and_adjust(client, admin_headers):
    tag = _tag()
    phone = "136" + tag[:8]
    mid = _create_member("积分会员" + tag, phone, points=500)
    try:
        r = client.get("/api/v1/points/logs", headers=admin_headers)
        assert r.json()["code"] == 0, r.text
        data = r.json()["data"]
        assert data["total"] >= 5
        assert set(("todayGrant", "todayConsume", "totalBalance", "holders")) <= set(data["stats"].keys())
        for item in data["list"]:
            assert "changeValue" in item and "typeText" in item

        r = client.get("/api/v1/points/logs?member=张小明", headers=admin_headers)
        assert r.json()["code"] == 0
        # 同样先断言非空，避免空列表让 all(...) 恒真
        logs = r.json()["data"]["list"]
        assert len(logs) >= 1, "未查到积分流水：请先执行 uv run python -m seed.runner demo"
        assert all(x["memberName"] == "张小明" for x in logs)

        r = client.post(
            "/api/v1/points/adjust", headers=admin_headers,
            json={"memberId": mid, "change": 200, "reason": "测试增加积分"},
        )
        assert r.json()["code"] == 0, r.text
        assert r.json()["data"]["points"] == 700
        row = _q1("SELECT points FROM members WHERE id=%s", (mid,))
        assert row["points"] == 700
        log = _q1(
            "SELECT type,change_value,created_by FROM points_logs WHERE member_id=%s ORDER BY id DESC LIMIT 1",
            (mid,),
        )
        assert log["type"] == 3 and log["change_value"] == 200

        r = client.post(
            "/api/v1/points/adjust", headers=admin_headers,
            json={"memberId": mid, "change": -9999, "reason": "测试超额扣减"},
        )
        assert r.json()["code"] != 0
        assert _q1("SELECT points FROM members WHERE id=%s", (mid,))["points"] == 700

        r = client.post(
            "/api/v1/points/adjust", headers=admin_headers,
            json={"memberId": 999999999, "change": 10, "reason": "不存在会员"},
        )
        assert r.json()["code"] != 0
    finally:
        _clean_member(mid)


def test_member_logs_list(client, admin_headers):
    r = client.get("/api/v1/member-logs", headers=admin_headers)
    assert r.json()["code"] == 0, r.text
    data = r.json()["data"]
    assert data["total"] >= 1
    for item in data["list"]:
        assert "memberName" in item and "actionType" in item

    r = client.get("/api/v1/member-logs?keyword=登录", headers=admin_headers)
    assert r.json()["code"] == 0
