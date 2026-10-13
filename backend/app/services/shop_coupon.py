from core import database
from core.errors import coupon_unavailable, state_error

COUPON_TYPE_TEXT = {1: "满减券", 2: "折扣券"}


def _parse_scope_ids(value) -> list[int]:
    result = []
    if value:
        for part in str(value).split(","):
            if part.strip().isdigit():
                result.append(int(part.strip()))
    return result


def _coupon_vo(c: dict, received_count: int = 0, received: bool = False) -> dict:
    return {
        "id": c["id"],
        "name": c["name"],
        "type": c["type"],
        "typeText": COUPON_TYPE_TEXT.get(c["type"], ""),
        "amount": float(c["amount"] or 0),
        "rate": float(c["rate"]) if c["rate"] is not None else None,
        "minAmount": float(c["min_amount"] or 0),
        "scope": c["scope"],
        "scopeIds": _parse_scope_ids(c["scope_ids"]),
        "startTime": c["start_time"],
        "endTime": c["end_time"],
        "totalCount": c["total_count"] or 0,
        "receivedCount": received_count,
        "perLimit": c["per_limit"] or 1,
        "received": received,
    }


async def list_mine(member_id: int, page: int, page_size: int, status: int | None = None) -> dict:
    where = ["cr.member_id=%s"]
    params: list = [member_id]
    if status not in (None, "", 0):
        if int(status) == 1:
            where.append("cr.status=1 AND c.end_time>=NOW()")
        elif int(status) == 2:
            where.append("cr.status=2")
        elif int(status) == 3:
            where.append("cr.status=1 AND c.end_time<NOW()")
        else:
            state_error("优惠券状态参数不正确")
    cond = " AND ".join(where)
    total = await database.fetch_one(
        f"SELECT COUNT(*) AS c FROM coupon_receive cr JOIN coupons c ON c.id=cr.coupon_id WHERE {cond}",
        params,
    )
    rows = await database.fetch_all(
        "SELECT cr.id AS receive_id,cr.coupon_id AS id,cr.status AS receive_status,"
        "(c.end_time<NOW()) AS expired_flg,c.name,c.type,c.amount,c.rate,c.min_amount,c.scope,c.scope_ids,"
        "c.start_time,c.end_time,c.total_count,c.per_limit "
        f"FROM coupon_receive cr JOIN coupons c ON c.id=cr.coupon_id WHERE {cond} "
        "ORDER BY cr.id DESC LIMIT %s OFFSET %s",
        params + [page_size, (page - 1) * page_size],
    )
    items = []
    for r in rows:
        vo = _coupon_vo(r)
        vo["receiveId"] = r["receive_id"]
        if r["receive_status"] == 2:
            vo["status"] = 2
        elif r["expired_flg"]:
            vo["status"] = 3
        else:
            vo["status"] = 1
        items.append(vo)
    return {
        "list": items,
        "total": total["c"],
        "page": page,
        "page_size": page_size,
    }


async def available_list(member_id: int) -> dict:
    rows = await database.fetch_all(
        "SELECT c.*, (SELECT COUNT(*) FROM coupon_receive cr WHERE cr.coupon_id=c.id) AS actual_received "
        "FROM coupons c WHERE c.status=1 AND c.start_time<=NOW() AND c.end_time>=NOW() "
        "ORDER BY c.id ASC"
    )
    items = []
    for c in rows:
        if c["total_count"] and c["actual_received"] >= c["total_count"]:
            continue
        got = await database.fetch_one(
            "SELECT COUNT(*) AS c FROM coupon_receive WHERE coupon_id=%s AND member_id=%s",
            (c["id"], member_id),
        )
        if c["per_limit"] and got["c"] >= c["per_limit"]:
            continue
        items.append(_coupon_vo(c, received_count=c["actual_received"], received=got["c"] > 0))
    return {"list": items}


async def receive(member_id: int, coupon_id: int) -> dict:
    coupon = await database.fetch_one(
        "SELECT * FROM coupons WHERE id=%s AND status=1 AND start_time<=NOW() AND end_time>=NOW()",
        (coupon_id,),
    )
    if not coupon:
        coupon_unavailable("优惠券不存在或不在领取时间内")
    # 领取必须在事务内完成「计数 → 校验 → 插入」，并用行锁串行化同一张券的并发领取。
    # 原先是裸 SELECT COUNT 再 INSERT（无事务无锁），并发下会突破 per_limit 与 total_count 造成超发。
    async with database.transaction() as cur:
        # 行锁：同一券的领取请求排队执行，杜绝 check-then-act 竞态
        await cur.execute("SELECT id FROM coupons WHERE id=%s FOR UPDATE", (coupon_id,))
        await cur.execute(
            "SELECT COUNT(*) AS c FROM coupon_receive WHERE coupon_id=%s AND member_id=%s",
            (coupon_id, member_id),
        )
        got = await cur.fetchone()
        # coupon_receive 上有 UNIQUE(coupon_id, member_id)，每人每券实际只能持有一张；
        # 若按 per_limit>1 放行第二次插入，会直接撞唯一键抛 1062 变成 500。
        if got["c"] > 0:
            coupon_unavailable("该优惠券已领取或达到领取上限")
        if coupon["total_count"]:
            await cur.execute(
                "SELECT COUNT(*) AS c FROM coupon_receive WHERE coupon_id=%s", (coupon_id,)
            )
            actual = await cur.fetchone()
            if actual["c"] >= coupon["total_count"]:
                coupon_unavailable("该优惠券已领完")
        await cur.execute(
            "INSERT INTO coupon_receive (coupon_id,member_id,status) VALUES (%s,%s,1)",
            (coupon_id, member_id),
        )
        rid = cur.lastrowid
        await cur.execute(
            "UPDATE coupons SET received_count=received_count+1 WHERE id=%s", (coupon_id,)
        )
    return {"receiveId": rid}
