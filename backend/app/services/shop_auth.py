from core import database
from core.config import config
from core.errors import auth_failed, bad_request, duplicate
from core.security import create_member_token, hash_code, hash_password, random_code, verify_code, verify_password
from core.timezone import now as tz_now, to_naive

_SMS_MAX_FAIL = 5

_MEMBER_BASE_SELECT = (
    "SELECT m.id,m.nickname,m.avatar,m.phone,m.email,m.level_id,m.points,m.total_consume,m.status,"
    "l.level_name AS level_name FROM members m LEFT JOIN member_level l ON l.id=m.level_id"
)


def member_item(r: dict) -> dict:
    return {
        "id": r["id"],
        "nickname": r["nickname"] or "",
        "avatar": r["avatar"] or "",
        "phone": r["phone"] or "",
        "email": r["email"] or "",
        "levelId": r["level_id"],
        "levelName": r["level_name"] or "",
        "points": r["points"] or 0,
        "totalConsume": float(r["total_consume"] or 0),
    }


def _member_log(member_id: int, action_type: str, action: str, ip: str = ""):
    return database.execute(
        "INSERT INTO member_logs (member_id, action_type, action, ip) VALUES (%s,%s,%s,%s)",
        (member_id, action_type, action, ip),
    )


async def send_code(phone: str, scene: str, ip: str = "") -> str:
    """生成并落库一条真验证码，返回明文供上层投递（mock 时打印/回显）。

    历史实现有两个致命问题，现已修掉：
    1. 不生成验证码 → register 只能比一个全局固定值（等于万能口令）；
    2. 限频存在进程内 dict → 多 worker/多副本下完全失效，且不与「是否真的发过码」绑定。
    现在改为：一码一记录（phone+scene），落库校验 + 过期 + 失败次数上限，天然多副本可用。
    """
    if scene != "register":
        bad_request("暂不支持该验证码场景")
    if not config.sms_mock:
        # 本项目未内置任何短信服务商 SDK。关闭演示开关后必须显式失败，
        # 而不是像老版本那样回一句「已发送」——那等于对外声称做了没做的事。
        bad_request("未接入短信服务商：本项目当前只有演示通道，请保持 SMS_MOCK=true 或自行实现短信 Provider")
    # 同一号码同一场景的旧码立即失效，避免多码并存扩大爆破面
    await database.execute(
        "UPDATE sms_codes SET used_at=NOW() WHERE phone=%s AND scene=%s AND used_at IS NULL",
        (phone, scene),
    )
    last = await database.fetch_one(
        "SELECT created_at FROM sms_codes WHERE phone=%s AND scene=%s "
        "ORDER BY created_at DESC LIMIT 1",
        (phone, scene),
    )
    if last and _seconds_elapsed(last["created_at"]) < config.sms_interval_seconds:
        bad_request("验证码发送过于频繁，请稍后再试")
    code = random_code(6)
    await database.execute(
        "INSERT INTO sms_codes (phone,scene,code_hash,ip,expires_at) "
        "VALUES (%s,%s,%s,%s,DATE_ADD(NOW(), INTERVAL %s SECOND))",
        (phone, scene, hash_code(code), ip, config.sms_code_expire_seconds),
    )
    return code


def _seconds_elapsed(when) -> float:
    """距某个 DB DATETIME 过去了多少秒（正数=已过去）。

    MySQL 返回的 DATETIME 是 naive 且会话时区已固定 +08:00（见 core.database.init_pool），
    因此必须与 core.timezone.now() 去 tzinfo 后的字面量口径比较，否则会差 8 小时。
    """
    import datetime as dt

    if when is None:
        return float("inf")
    if isinstance(when, str):
        when = dt.datetime.strptime(when, "%Y-%m-%d %H:%M:%S")
    return (to_naive(tz_now()) - when).total_seconds()


async def _consume_code(phone: str, scene: str, code: str) -> None:
    """校验验证码并核销。失败计入 fail_count，超限即作废（防穷举）。"""
    row = await database.fetch_one(
        "SELECT id,code_hash,fail_count,expires_at FROM sms_codes "
        "WHERE phone=%s AND scene=%s AND used_at IS NULL ORDER BY created_at DESC LIMIT 1",
        (phone, scene),
    )
    if not row:
        bad_request("请先获取验证码")
    if row["fail_count"] >= _SMS_MAX_FAIL or _seconds_elapsed(row["expires_at"]) > 0:
        await database.execute("UPDATE sms_codes SET used_at=NOW() WHERE id=%s", (row["id"],))
        bad_request("验证码已失效，请重新获取")
    if not verify_code(str(code or ""), row["code_hash"]):
        await database.execute(
            "UPDATE sms_codes SET fail_count=fail_count+1 WHERE id=%s", (row["id"],)
        )
        bad_request("验证码错误")
    await database.execute("UPDATE sms_codes SET used_at=NOW() WHERE id=%s", (row["id"],))


async def register(phone: str, code: str, password: str, ip: str = "") -> None:
    # 先判重复再核销验证码：同一手机号第二次提交时（无论码对错）都应得到「已注册」，
    # 而不是被验证码已失效的错误掩盖
    existed = await database.fetch_one("SELECT id FROM members WHERE phone=%s", (phone,))
    if existed:
        duplicate("该手机号已注册")
    await _consume_code(phone, "register", code)
    level = await database.fetch_one(
        "SELECT id FROM member_level WHERE level_name='普通会员' ORDER BY id LIMIT 1"
    )
    pwd_hash = hash_password(password)
    mid = await database.execute_return_id(
        "INSERT INTO members (phone,password_hash,nickname,level_id,points,total_consume,status,registered_at) "
        "VALUES (%s,%s,%s,%s,0,0.00,1,NOW())",
        (phone, pwd_hash, f"会员{phone[-4:]}", level["id"] if level else None),
    )
    await _member_log(mid, "register", "注册成功", ip)


async def login(phone: str, password: str, ip: str = "") -> dict:
    row = await database.fetch_one("SELECT * FROM members WHERE phone=%s", (phone,))
    if not row or not verify_password(password, row["password_hash"] or ""):
        auth_failed("手机号或密码错误")
    if row["status"] != 1:
        auth_failed("账号已被禁用")
    token = create_member_token(row["id"], phone)
    await database.execute(
        "UPDATE members SET last_login_time=NOW() WHERE id=%s", (row["id"],)
    )
    await _member_log(row["id"], "login", "用户登录成功", ip)
    detail = await member_detail(row["id"])
    return {"token": token, "member": detail}


async def member_detail(member_id: int) -> dict:
    row = await database.fetch_one(f"{_MEMBER_BASE_SELECT} WHERE m.id=%s", (member_id,))
    if not row:
        auth_failed()
    return member_item(row)


async def update_profile(member_id: int, nickname: str, avatar: str, ip: str = "") -> dict:
    await database.execute(
        "UPDATE members SET nickname=%s,avatar=%s WHERE id=%s",
        (nickname, avatar, member_id),
    )
    await _member_log(member_id, "profile", "修改个人资料", ip)
    return await member_detail(member_id)


async def change_password(member_id: int, old_password: str, new_password: str, ip: str = "") -> None:
    row = await database.fetch_one("SELECT password_hash FROM members WHERE id=%s", (member_id,))
    if not row or not verify_password(old_password, row["password_hash"] or ""):
        auth_failed("原密码不正确")
    await database.execute(
        "UPDATE members SET password_hash=%s WHERE id=%s", (hash_password(new_password), member_id)
    )
    await _member_log(member_id, "password", "修改登录密码", ip)


async def logout(member_id: int, ip: str = "") -> None:
    await _member_log(member_id, "logout", "用户退出登录", ip)
