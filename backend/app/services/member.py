from core import audit, database
from core.errors import bad_request, duplicate, not_found
from core.money import f2 as _money
from core.security import hash_password
from schemas.member import (
    LevelSave,
    MemberProfileUpdate,
    MemberResetPassword,
    MemberStatusUpdate,
    PointsAdjust,
)

POINTS_TYPE_TEXT = {1: "获取", 2: "消费", 3: "手动调整"}


def _build_member_where(filters: dict) -> tuple[str, list]:
    where = ["1=1"]
    params: list = []
    if filters.get("keyword"):
        where.append("(m.nickname LIKE %s OR m.phone LIKE %s OR m.email LIKE %s)")
        params += [f"%{filters['keyword']}%"] * 3
    if filters.get("level_id") not in (None, ""):
        where.append("m.level_id=%s")
        params.append(int(filters["level_id"]))
    if filters.get("status") not in (None, ""):
        where.append("m.status=%s")
        params.append(int(filters["status"]))
    if filters.get("start_date"):
        where.append("DATE(m.registered_at)>=%s")
        params.append(filters["start_date"])
    if filters.get("end_date"):
        where.append("DATE(m.registered_at)<=%s")
        params.append(filters["end_date"])
    return " AND ".join(where), params


MEMBER_LIST_SELECT = (
    "SELECT m.id,m.nickname,m.avatar,m.phone,m.email,m.level_id,m.points,m.total_consume,m.status,"
    "m.registered_at,m.last_login_time,m.created_at,l.level_name AS level_name,"
    "(SELECT COUNT(*) FROM orders o WHERE o.member_id=m.id) AS order_count "
    "FROM members m LEFT JOIN member_level l ON l.id=m.level_id"
)


def _member_item(r: dict) -> dict:
    return {
        "id": r["id"],
        "nickname": r["nickname"],
        "avatar": r["avatar"],
        "phone": r["phone"] or "",
        "email": r["email"] or "",
        "levelId": r["level_id"],
        "levelName": r["level_name"] or "",
        "points": r["points"] or 0,
        "totalConsume": _money(r["total_consume"]),
        "orderCount": r["order_count"] or 0,
        "status": r["status"],
        "registeredAt": r["registered_at"],
        "lastLoginTime": r["last_login_time"],
        "createdAt": r["created_at"],
    }


async def list_members(page: int, page_size: int, filters: dict) -> dict:
    cond, params = _build_member_where(filters)
    total = await database.fetch_one(
        f"SELECT COUNT(*) AS c FROM members m LEFT JOIN member_level l ON l.id=m.level_id WHERE {cond}", params
    )
    rows = await database.fetch_all(
        f"{MEMBER_LIST_SELECT} WHERE {cond} ORDER BY m.id DESC LIMIT %s OFFSET %s",
        params + [page_size, (page - 1) * page_size],
    )
    return {
        "list": [_member_item(r) for r in rows],
        "total": total["c"],
        "page": page,
        "page_size": page_size,
    }


async def member_detail(member_id: int) -> dict:
    row = await database.fetch_one(f"{MEMBER_LIST_SELECT} WHERE m.id=%s", (member_id,))
    if not row:
        not_found("会员不存在")
    orders = await database.fetch_all(
        "SELECT id,order_no,pay_amount,pay_status,order_status,created_at FROM orders "
        "WHERE member_id=%s ORDER BY id DESC LIMIT 20",
        (member_id,),
    )
    logs = await database.fetch_all(
        "SELECT id,action_type,action,ip,created_at FROM member_logs "
        "WHERE member_id=%s ORDER BY id DESC LIMIT 30",
        (member_id,),
    )
    detail = _member_item(row)
    detail["orders"] = [
        {
            "id": o["id"],
            "orderNo": o["order_no"],
            "payAmount": _money(o["pay_amount"]),
            "payStatus": o["pay_status"],
            "orderStatus": o["order_status"],
            "createdAt": o["created_at"],
        }
        for o in orders
    ]
    detail["logs"] = [
        {
            "id": lg["id"],
            "actionType": lg["action_type"],
            "action": lg["action"],
            "ip": lg["ip"],
            "createdAt": lg["created_at"],
        }
        for lg in logs
    ]
    return detail


async def update_member_profile(member_id: int, body: MemberProfileUpdate, user) -> None:
    row = await database.fetch_one("SELECT id,nickname FROM members WHERE id=%s", (member_id,))
    if not row:
        not_found("会员不存在")
    nickname = body.nickname.strip()
    if not nickname:
        bad_request("昵称不能为空")
    phone = body.phone.strip() or None
    email = body.email.strip() or None
    if phone:
        dup = await database.fetch_one("SELECT id FROM members WHERE phone=%s AND id<>%s", (phone, member_id))
        if dup:
            duplicate("手机号已被其他会员使用")
    if body.level_id is not None:
        lv = await database.fetch_one("SELECT id FROM member_level WHERE id=%s", (body.level_id,))
        if not lv:
            not_found("会员等级不存在")
    await database.execute(
        "UPDATE members SET nickname=%s,phone=%s,email=%s,level_id=%s WHERE id=%s",
        (nickname, phone, email, body.level_id, member_id),
    )
    await _log_member_action(member_id, "profile", f"管理员编辑会员资料：昵称 {row['nickname']} → {nickname}")
    await audit.log_action(user.id, "member", audit.ACTION_EDIT, f"member:{member_id}", "编辑会员资料")


async def set_member_status(member_id: int, body: MemberStatusUpdate, user) -> None:
    row = await database.fetch_one("SELECT id,nickname,status FROM members WHERE id=%s", (member_id,))
    if not row:
        not_found("会员不存在")
    if row["status"] == body.status:
        return
    await database.execute("UPDATE members SET status=%s WHERE id=%s", (body.status, member_id))
    await _log_member_action(
        member_id, "status", f"管理员{'禁用' if body.status == 0 else '启用'}会员账号"
    )
    await audit.log_action(user.id, "member", audit.ACTION_EDIT, f"member:{member_id}", f"启禁用会员（status={body.status}）")


async def reset_member_password(member_id: int, body: MemberResetPassword, user) -> None:
    row = await database.fetch_one("SELECT id,nickname FROM members WHERE id=%s", (member_id,))
    if not row:
        not_found("会员不存在")
    if not body.password:
        bad_request("请提供新密码（至少 6 位）")
    password = body.password
    await database.execute(
        "UPDATE members SET password_hash=%s WHERE id=%s", (hash_password(password), member_id)
    )
    await _log_member_action(member_id, "password", "管理员重置会员登录密码")
    await audit.log_action(user.id, "member", audit.ACTION_EDIT, f"member:{member_id}", "重置会员密码")


async def list_levels() -> list[dict]:
    rows = await database.fetch_all(
        "SELECT l.id,l.level_name,l.upgrade_amount,l.upgrade_points,l.discount_rate,l.benefits,l.status,l.created_at,"
        "(SELECT COUNT(*) FROM members m WHERE m.level_id=l.id) AS member_count "
        "FROM member_level l ORDER BY l.upgrade_amount ASC,l.id ASC"
    )
    return [
        {
            "id": r["id"],
            "levelName": r["level_name"],
            "upgradeAmount": _money(r["upgrade_amount"]),
            "upgradePoints": r["upgrade_points"] or 0,
            "discountRate": _money(r["discount_rate"]),
            "benefits": r["benefits"] or "",
            "status": r["status"],
            "memberCount": r["member_count"] or 0,
            "createdAt": r["created_at"],
        }
        for r in rows
    ]


async def create_level(body: LevelSave, user) -> int:
    name = body.level_name.strip()
    if not name:
        bad_request("等级名称不能为空")
    exist = await database.fetch_one("SELECT id FROM member_level WHERE level_name=%s", (name,))
    if exist:
        duplicate("等级名称已存在")
    lid = await database.execute_return_id(
        "INSERT INTO member_level (level_name,upgrade_amount,upgrade_points,discount_rate,benefits,status) "
        "VALUES (%s,%s,%s,%s,%s,%s)",
        (name, body.upgrade_amount, body.upgrade_points, body.discount_rate, body.benefits, body.status),
    )
    await audit.log_action(user.id, "member", audit.ACTION_ADD, f"member-level:{name}", "新增会员等级")
    return lid


async def update_level(level_id: int, body: LevelSave, user) -> None:
    row = await database.fetch_one("SELECT id FROM member_level WHERE id=%s", (level_id,))
    if not row:
        not_found("会员等级不存在")
    name = body.level_name.strip()
    if not name:
        bad_request("等级名称不能为空")
    exist = await database.fetch_one(
        "SELECT id FROM member_level WHERE level_name=%s AND id<>%s", (name, level_id)
    )
    if exist:
        duplicate("等级名称已存在")
    await database.execute(
        "UPDATE member_level SET level_name=%s,upgrade_amount=%s,upgrade_points=%s,discount_rate=%s,"
        "benefits=%s,status=%s WHERE id=%s",
        (name, body.upgrade_amount, body.upgrade_points, body.discount_rate, body.benefits, body.status, level_id),
    )
    await audit.log_action(user.id, "member", audit.ACTION_EDIT, f"member-level:{name}", "编辑会员等级")


async def list_points_logs(page: int, page_size: int, filters: dict) -> dict:
    where = ["1=1"]
    params: list = []
    if filters.get("member"):
        where.append("(m.nickname LIKE %s OR m.phone LIKE %s)")
        params += [f"%{filters['member']}%", f"%{filters['member']}%"]
    if filters.get("type") not in (None, ""):
        where.append("p.type=%s")
        params.append(int(filters["type"]))
    if filters.get("start_date"):
        where.append("DATE(p.created_at)>=%s")
        params.append(filters["start_date"])
    if filters.get("end_date"):
        where.append("DATE(p.created_at)<=%s")
        params.append(filters["end_date"])
    cond = " AND ".join(where)
    total = await database.fetch_one(
        f"SELECT COUNT(*) AS c FROM points_logs p LEFT JOIN members m ON m.id=p.member_id WHERE {cond}", params
    )
    rows = await database.fetch_all(
        "SELECT p.id,p.member_id,p.change_value,p.reason,p.type,p.related_id,p.created_by,p.created_at,"
        "m.nickname AS member_name,m.phone AS member_phone,a.real_name AS admin_name,a.username AS admin_username "
        f"FROM points_logs p LEFT JOIN members m ON m.id=p.member_id "
        f"LEFT JOIN admin_users a ON a.id=p.created_by WHERE {cond} ORDER BY p.id DESC LIMIT %s OFFSET %s",
        params + [page_size, (page - 1) * page_size],
    )
    today = await database.fetch_one(
        "SELECT COALESCE(SUM(CASE WHEN change_value>0 THEN change_value ELSE 0 END),0) AS grant_v,"
        "COALESCE(SUM(CASE WHEN change_value<0 THEN -change_value ELSE 0 END),0) AS consume_v "
        "FROM points_logs WHERE DATE(created_at)=CURDATE()"
    )
    bal_row = await database.fetch_one(
        "SELECT COALESCE(SUM(points),0) AS bal FROM members WHERE points>0"
    )
    holders = await database.fetch_one("SELECT COUNT(*) AS c FROM members WHERE points>0")
    return {
        "list": [
            {
                "id": r["id"],
                "memberId": r["member_id"],
                "memberName": r["member_name"] or f"会员#{r['member_id']}",
                "memberPhone": r["member_phone"] or "",
                "type": r["type"],
                "typeText": POINTS_TYPE_TEXT.get(r["type"], ""),
                "changeValue": r["change_value"],
                "reason": r["reason"],
                "relatedId": r["related_id"],
                "operatorName": (r["admin_name"] or r["admin_username"] or "系统") if r["created_by"] else "系统",
                "createdAt": r["created_at"],
            }
            for r in rows
        ],
        "total": total["c"],
        "stats": {
            "todayGrant": today["grant_v"] or 0,
            "todayConsume": today["consume_v"] or 0,
            "totalBalance": bal_row["bal"] or 0,
            "holders": holders["c"] or 0,
        },
        "page": page,
        "page_size": page_size,
    }


async def adjust_points(body: PointsAdjust, user) -> int:
    member = await database.fetch_one("SELECT id FROM members WHERE id=%s", (body.member_id,))
    if not member:
        not_found("会员不存在")
    if body.change == 0:
        bad_request("调整积分数量不能为 0")
    async with database.transaction() as cur:
        await cur.execute("SELECT id,points,nickname FROM members WHERE id=%s FOR UPDATE", (body.member_id,))
        mrow = await cur.fetchone()
        new_points = mrow["points"] + body.change
        if new_points < 0:
            bad_request(f"会员 {mrow['nickname']} 积分不足，扣减后不可为负")
        await cur.execute("UPDATE members SET points=%s WHERE id=%s", (new_points, body.member_id))
        await cur.execute(
            "INSERT INTO points_logs (member_id,change_value,reason,type,created_by) VALUES (%s,%s,%s,3,%s)",
            (body.member_id, body.change, body.reason, user.id),
        )
        await cur.execute(
            "INSERT INTO member_logs (member_id,action_type,action,ip) VALUES (%s,'points',%s,'127.0.0.1')",
            (body.member_id, f"管理员手动调整积分 {body.change:+d}：{body.reason}"),
        )
    await audit.log_action(user.id, "member", audit.ACTION_EDIT, f"member:{body.member_id}", f"手动调整积分 {body.change:+d}")
    return new_points


async def list_member_logs(page: int, page_size: int, filters: dict) -> dict:
    where = ["1=1"]
    params: list = []
    if filters.get("keyword"):
        where.append("(m.nickname LIKE %s OR m.phone LIKE %s OR lg.action LIKE %s)")
        params += [f"%{filters['keyword']}%", f"%{filters['keyword']}%", f"%{filters['keyword']}%"]
    if filters.get("action_type"):
        where.append("lg.action_type=%s")
        params.append(filters["action_type"])
    if filters.get("start_date"):
        where.append("DATE(lg.created_at)>=%s")
        params.append(filters["start_date"])
    if filters.get("end_date"):
        where.append("DATE(lg.created_at)<=%s")
        params.append(filters["end_date"])
    cond = " AND ".join(where)
    total = await database.fetch_one(
        f"SELECT COUNT(*) AS c FROM member_logs lg LEFT JOIN members m ON m.id=lg.member_id WHERE {cond}", params
    )
    rows = await database.fetch_all(
        "SELECT lg.id,lg.member_id,lg.action_type,lg.action,lg.ip,lg.created_at,"
        "m.nickname AS member_name,m.phone AS member_phone "
        f"FROM member_logs lg LEFT JOIN members m ON m.id=lg.member_id WHERE {cond} ORDER BY lg.id DESC "
        f"LIMIT %s OFFSET %s",
        params + [page_size, (page - 1) * page_size],
    )
    return {
        "list": [
            {
                "id": r["id"],
                "memberId": r["member_id"],
                "memberName": r["member_name"] or f"会员#{r['member_id']}",
                "memberPhone": r["member_phone"] or "",
                "actionType": r["action_type"],
                "action": r["action"],
                "ip": r["ip"],
                "createdAt": r["created_at"],
            }
            for r in rows
        ],
        "total": total["c"],
        "page": page,
        "page_size": page_size,
    }


async def _log_member_action(member_id: int, action_type: str, action: str) -> None:
    await database.execute(
        "INSERT INTO member_logs (member_id,action_type,action,ip) VALUES (%s,%s,%s,'127.0.0.1')",
        (member_id, action_type, action),
    )
