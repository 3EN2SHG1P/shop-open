"""商城前台 · 会员认证接口回归（specs/商城前台V1.2.spec.md §5.1）

固化的历史缺陷：
1. send-code 函数内对模块级 `_sms_sent_at` 重新赋值而未声明 global → UnboundLocalError → 接口 500；
2. 注册校验收一个**全局固定验证码**（默认 123456），且不校验该手机号是否真的请求过验证码
   ——等于给所有人留了一个注册后门。现在改为「随机码 + 落库哈希比对 + 过期 + 失败次数上限」。
"""
import asyncio
import re
import uuid

import aiomysql
from aiomysql.cursors import DictCursor

from core.config import config


def _phone():
    digits = re.sub(r"\D", "", uuid.uuid4().hex)
    return "13" + digits[:9]


def _send_code(client, phone):
    """获取验证码。演示通道会通过 data.devCode 回显（无真实短信下发）。"""
    r = client.post("/api/v1/shop/auth/send-code", json={"phone": phone, "scene": "register"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["code"] == 0, r.text
    return (body.get("data") or {}).get("devCode")


def _delete_members(phones):
    """清理本文件注册的会员，避免污染其他对 members 全表敏感的用例（如会员注册日期筛选）"""

    async def run():
        conn = await aiomysql.connect(
            host=config.db_host, port=config.db_port, user=config.db_user,
            password=config.db_password, db=config.db_name, charset=config.db_charset,
            autocommit=True, cursorclass=DictCursor,
        )
        try:
            cur = await conn.cursor()
            for phone in phones:
                await cur.execute("SELECT id FROM members WHERE phone=%s", (phone,))
                row = await cur.fetchone()
                if not row:
                    continue
                mid = row["id"]
                for table in ("member_cart", "member_logs", "member_address", "points_logs", "coupon_receive", "sms_codes"):
                    try:
                        await cur.execute(f"DELETE FROM {table} WHERE member_id=%s", (mid,))
                    except Exception:
                        pass
                try:
                    await cur.execute("DELETE FROM orders WHERE member_id=%s", (mid,))
                except Exception:
                    pass
                await cur.execute("DELETE FROM members WHERE id=%s", (mid,))
        finally:
            conn.close()

    asyncio.run(run())


def test_send_code_ok(client):
    r = client.post("/api/v1/shop/auth/send-code", json={"phone": _phone(), "scene": "register"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["code"] == 0, r.text
    assert body["data"]["expiresIn"] == config.sms_code_expire_seconds


def test_send_code_devcode_is_random(client):
    """验证码必须每次随机：固定值等于注册后门。"""
    seen = set()
    for _ in range(3):
        code = _send_code(client, _phone())
        assert code and len(code) == 6 and code.isdigit(), f"未拿到合法验证码：{code}"
        seen.add(code)
    assert len(seen) == 3, f"验证码出现重复值，疑似固定：{seen}"


def test_register_rejects_universal_code(client):
    """回归：历史实现里 123456 是全局万能码，任何人都能批量注册。"""
    phone = _phone()
    try:
        _send_code(client, phone)
        r = client.post(
            "/api/v1/shop/auth/register", json={"phone": phone, "code": "123456", "password": "Test1234"}
        )
        body = r.json()
        assert body["code"] != 0, f"万能验证码仍然可用：{r.text}"
    finally:
        _delete_members([phone])


def test_register_rejects_when_code_never_sent(client):
    """未调用过 send-code 就直接提交注册，必须失败。"""
    phone = _phone()
    try:
        r = client.post(
            "/api/v1/shop/auth/register", json={"phone": phone, "code": "999999", "password": "Test1234"}
        )
        assert r.json()["code"] != 0, f"未发码也能注册成功：{r.text}"
    finally:
        _delete_members([phone])


def test_send_code_repeat_returns_biz_error_not_500(client):
    """60s 内重复发送：应回业务码 2001，绝不能 5000（曾因 UnboundLocalError 全崩）"""
    phone = _phone()
    first = client.post("/api/v1/shop/auth/send-code", json={"phone": phone, "scene": "register"})
    assert first.json()["code"] == 0, first.text

    second = client.post("/api/v1/shop/auth/send-code", json={"phone": phone, "scene": "register"})
    body = second.json()
    assert body["code"] != 5000, f"重复发送触发了服务器内部错误: {second.text}"
    assert body["code"] == 2001, second.text


def test_send_code_rejects_unsupported_scene(client):
    r = client.post("/api/v1/shop/auth/send-code", json={"phone": _phone(), "scene": "login"})
    assert r.json()["code"] == 2001, r.text


def test_register_login_roundtrip(client):
    """注册 → 登录 → /auth/me 全链路（游客→会员）"""
    phone = _phone()
    try:
        _roundtrip(client, phone)
    finally:
        _delete_members([phone])


def _roundtrip(client, phone):
    code = _send_code(client, phone)
    assert code, "未拿到验证码：请在 backend/.env 设置 SMS_MOCK=true（演示通道）后重跑"

    reg = client.post("/api/v1/shop/auth/register", json={"phone": phone, "code": code, "password": "Test1234"})
    assert reg.json()["code"] == 0, reg.text

    # 同一手机号重复注册：应报「已注册」(3004)，而不是被验证码失效的错误掩盖
    dup = client.post("/api/v1/shop/auth/register", json={"phone": phone, "code": code, "password": "Test1234"})
    assert dup.json()["code"] == 3004, dup.text

    login = client.post("/api/v1/shop/auth/login", json={"phone": phone, "password": "Test1234"})
    body = login.json()
    assert body["code"] == 0, login.text
    token = body["data"]["token"]
    assert token and body["data"]["member"]["phone"] == phone

    me = client.get("/api/v1/shop/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["code"] == 0, me.text
    assert me.json()["data"]["phone"] == phone

    wrong = client.post("/api/v1/shop/auth/login", json={"phone": phone, "password": "WrongPass"})
    assert wrong.json()["code"] == 1001, wrong.text
