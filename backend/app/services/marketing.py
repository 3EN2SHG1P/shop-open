from core.timezone import now

from core import audit, database
from core.errors import bad_request, duplicate, not_found, referenced
from core.money import f2 as _money

COUPON_TYPE_TEXT = {1: "满减券", 2: "折扣券"}
SCOPE_TEXT = {1: "全部商品", 2: "指定分类", 3: "指定商品"}
STATUS_TEXT = {1: "启用", 0: "停用"}
DIST_STATUS_TEXT = {1: "待审核", 2: "已通过", 3: "已拒绝"}
DIST_LEVEL_TEXT = {1: "一级分销", 2: "二级分销", 3: "三级分销"}
COMMISSION_STATUS_TEXT = {1: "待结算", 2: "已结算"}


def _act_stage(start_time: str, end_time: str) -> tuple[int, str]:
    now_str = now().strftime("%Y-%m-%d %H:%M:%S")
    if start_time and now_str < str(start_time):
        return 1, "待开始"
    if end_time and now_str > str(end_time):
        return 3, "已结束"
    return 2, "进行中"


def _check_time(start_time: str, end_time: str, label: str = "活动"):
    if not start_time or not end_time:
        bad_request(f"{label}起止时间不能为空")
    if str(end_time) <= str(start_time):
        bad_request(f"{label}结束时间必须晚于开始时间")


def _item_map(r: dict, text_map: dict) -> str:
    return text_map.get(r, "")


# ==================== 优惠券 ====================


def _coupon_item(r: dict) -> dict:
    return {
        "id": r["id"],
        "name": r["name"],
        "type": r["type"],
        "typeText": COUPON_TYPE_TEXT.get(r["type"], ""),
        "amount": _money(r["amount"]),
        "rate": _money(r["rate"]) if r["rate"] is not None else None,
        "minAmount": _money(r["min_amount"]),
        "scope": r["scope"],
        "scopeText": SCOPE_TEXT.get(r["scope"], ""),
        "scopeIds": r["scope_ids"] or "",
        "totalCount": r["total_count"],
        "perLimit": r["per_limit"],
        "receivedCount": r["received_count"] or 0,
        "usedCount": r["used_count"] or 0,
        "startTime": r["start_time"],
        "endTime": r["end_time"],
        "status": r["status"],
        "statusText": STATUS_TEXT.get(r["status"], ""),
        "createdAt": r["created_at"],
    }


async def list_coupons(page: int, page_size: int, filters: dict) -> dict:
    where = ["1=1"]
    params: list = []
    if filters.get("keyword"):
        where.append("c.name LIKE %s")
        params.append(f"%{filters['keyword']}%")
    if filters.get("type") not in (None, ""):
        where.append("c.type=%s")
        params.append(int(filters["type"]))
    if filters.get("scope") not in (None, ""):
        where.append("c.scope=%s")
        params.append(int(filters["scope"]))
    if filters.get("status") not in (None, ""):
        where.append("c.status=%s")
        params.append(int(filters["status"]))
    if filters.get("start_date"):
        where.append("DATE(c.start_time)>=%s")
        params.append(filters["start_date"])
    if filters.get("end_date"):
        where.append("DATE(c.start_time)<=%s")
        params.append(filters["end_date"])
    cond = " AND ".join(where)
    total = await database.fetch_one(f"SELECT COUNT(*) AS c FROM coupons c WHERE {cond}", params)
    rows = await database.fetch_all(
        f"SELECT * FROM coupons c WHERE {cond} ORDER BY c.id DESC LIMIT %s OFFSET %s",
        params + [page_size, (page - 1) * page_size],
    )
    return {
        "list": [_coupon_item(r) for r in rows],
        "total": total["c"],
        "page": page,
        "page_size": page_size,
    }


async def create_coupon(body, user) -> int:
    name = body.name.strip()
    if not name:
        bad_request("优惠券名称不能为空")
    if body.type == 1 and body.amount <= 0:
        bad_request("满减券面额必须大于 0")
    if body.type == 2 and (body.rate is None or body.rate <= 0 or body.rate >= 10):
        bad_request("折扣券折扣需大于 0 且小于 10")
    _check_time(body.start_time, body.end_time, "优惠券")
    cid = await database.execute_return_id(
        "INSERT INTO coupons (name,type,amount,rate,min_amount,scope,scope_ids,total_count,per_limit,"
        "start_time,end_time,status,created_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            name, body.type, body.amount, body.rate, body.min_amount, body.scope, body.scope_ids,
            body.total_count, body.per_limit, body.start_time, body.end_time, body.status, user.id,
        ),
    )
    await audit.log_action(user.id, "marketing", audit.ACTION_ADD, f"coupon:{cid}", f"新增优惠券「{name}」")
    return cid


async def update_coupon(coupon_id: int, body, user) -> None:
    row = await database.fetch_one("SELECT id,name FROM coupons WHERE id=%s", (coupon_id,))
    if not row:
        not_found("优惠券不存在")
    _check_time(body.start_time, body.end_time, "优惠券")
    await database.execute(
        "UPDATE coupons SET name=%s,type=%s,amount=%s,rate=%s,min_amount=%s,scope=%s,scope_ids=%s,"
        "total_count=%s,per_limit=%s,start_time=%s,end_time=%s,status=%s WHERE id=%s",
        (
            body.name.strip(), body.type, body.amount, body.rate, body.min_amount, body.scope, body.scope_ids,
            body.total_count, body.per_limit, body.start_time, body.end_time, body.status, coupon_id,
        ),
    )
    await audit.log_action(user.id, "marketing", audit.ACTION_EDIT, f"coupon:{coupon_id}", f"编辑优惠券「{body.name.strip()}」")


async def delete_coupon(coupon_id: int, user) -> None:
    row = await database.fetch_one("SELECT id,name FROM coupons WHERE id=%s", (coupon_id,))
    if not row:
        not_found("优惠券不存在")
    rec = await database.fetch_one(
        "SELECT COUNT(*) AS c FROM coupon_receive WHERE coupon_id=%s", (coupon_id,)
    )
    if rec and rec["c"]:
        referenced("该优惠券已有会员领取记录，不可删除")
    await database.execute("DELETE FROM coupons WHERE id=%s", (coupon_id,))
    await audit.log_action(user.id, "marketing", audit.ACTION_DELETE, f"coupon:{coupon_id}", f"删除优惠券「{row['name']}」")


async def list_coupon_records(coupon_id: int, page: int, page_size: int, filters: dict) -> dict:
    row = await database.fetch_one("SELECT id,name FROM coupons WHERE id=%s", (coupon_id,))
    if not row:
        not_found("优惠券不存在")
    where = ["cr.coupon_id=%s"]
    params: list = [coupon_id]
    if filters.get("status") not in (None, ""):
        where.append("cr.status=%s")
        params.append(int(filters["status"]))
    if filters.get("keyword"):
        where.append("(m.nickname LIKE %s OR m.phone LIKE %s)")
        params += [f"%{filters['keyword']}%", f"%{filters['keyword']}%"]
    cond = " AND ".join(where)
    total = await database.fetch_one(
        f"SELECT COUNT(*) AS c FROM coupon_receive cr LEFT JOIN members m ON m.id=cr.member_id WHERE {cond}", params
    )
    rows = await database.fetch_all(
        "SELECT cr.id,cr.coupon_id,cr.member_id,cr.status,cr.received_at,cr.used_at,o.order_no,"
        "m.nickname AS member_name,m.phone AS member_phone "
        f"FROM coupon_receive cr LEFT JOIN members m ON m.id=cr.member_id "
        f"LEFT JOIN orders o ON o.id=cr.order_id WHERE {cond} ORDER BY cr.id DESC LIMIT %s OFFSET %s",
        params + [page_size, (page - 1) * page_size],
    )
    return {
        "list": [
            {
                "id": r["id"],
                "memberId": r["member_id"],
                "memberName": r["member_name"] or f"会员#{r['member_id']}",
                "memberPhone": r["member_phone"] or "",
                "status": r["status"],
                "statusText": "已使用" if r["status"] == 2 else "未使用",
                "orderNo": r["order_no"] or "",
                "receivedAt": r["received_at"],
                "usedAt": r["used_at"],
            }
            for r in rows
        ],
        "total": total["c"],
        "page": page,
        "page_size": page_size,
        "coupon": {"id": row["id"], "name": row["name"]},
    }


# ==================== 秒杀 ====================


def _seckill_item(r: dict) -> dict:
    stage_code, stage_text = _act_stage(r["start_time"], r["end_time"])
    return {
        "id": r["id"],
        "name": r["name"],
        "goodsId": r["goods_id"],
        "goodsName": r["goods_name"] or "",
        "skuId": r["sku_id"],
        "seckillPrice": _money(r["seckill_price"]),
        "seckillStock": r["seckill_stock"],
        "perLimit": r["per_limit"],
        "startTime": r["start_time"],
        "endTime": r["end_time"],
        "isStackable": r["is_stackable"],
        "status": stage_code,
        "statusText": stage_text,
        "createdAt": r["created_at"],
    }


async def list_seckills(page: int, page_size: int, filters: dict) -> dict:
    where = ["1=1"]
    params: list = []
    if filters.get("keyword"):
        where.append("(s.name LIKE %s OR g.name LIKE %s)")
        params += [f"%{filters['keyword']}%", f"%{filters['keyword']}%"]
    cond = " AND ".join(where)
    total = await database.fetch_one(
        f"SELECT COUNT(*) AS c FROM seckill_activities s LEFT JOIN goods g ON g.id=s.goods_id WHERE {cond}", params
    )
    rows = await database.fetch_all(
        "SELECT s.*,g.name AS goods_name FROM seckill_activities s LEFT JOIN goods g ON g.id=s.goods_id "
        f"WHERE {cond} ORDER BY s.id DESC LIMIT %s OFFSET %s",
        params + [page_size, (page - 1) * page_size],
    )
    return {
        "list": [_seckill_item(r) for r in rows],
        "total": total["c"],
        "page": page,
        "page_size": page_size,
    }


async def seckill_detail(activity_id: int) -> dict:
    row = await database.fetch_one(
        "SELECT s.*,g.name AS goods_name,g.price AS goods_price,g.stock AS goods_stock FROM seckill_activities s "
        "LEFT JOIN goods g ON g.id=s.goods_id WHERE s.id=%s",
        (activity_id,),
    )
    if not row:
        not_found("秒杀活动不存在")
    item = _seckill_item(row)
    item["goodsPrice"] = _money(row["goods_price"])
    item["goodsStock"] = row["goods_stock"] or 0
    return item


async def save_seckill(activity_id: int | None, body, user) -> int:
    goods = await database.fetch_one("SELECT id,name FROM goods WHERE id=%s", (body.goods_id,))
    if not goods:
        not_found("所选商品不存在")
    _check_time(body.start_time, body.end_time, "秒杀活动")
    stage_code, _ = _act_stage(body.start_time, body.end_time)
    data = (
        body.name.strip(), body.goods_id, body.sku_id, body.seckill_price, body.seckill_stock,
        body.per_limit, body.start_time, body.end_time, stage_code, body.is_stackable,
    )
    if activity_id:
        row = await database.fetch_one("SELECT id,name FROM seckill_activities WHERE id=%s", (activity_id,))
        if not row:
            not_found("秒杀活动不存在")
        await database.execute(
            "UPDATE seckill_activities SET name=%s,goods_id=%s,sku_id=%s,seckill_price=%s,seckill_stock=%s,"
            "per_limit=%s,start_time=%s,end_time=%s,status=%s,is_stackable=%s WHERE id=%s",
            data + (activity_id,),
        )
        await audit.log_action(user.id, "marketing", audit.ACTION_EDIT, f"seckill:{activity_id}", f"编辑秒杀活动「{body.name.strip()}」")
        return activity_id
    aid = await database.execute_return_id(
        "INSERT INTO seckill_activities (name,goods_id,sku_id,seckill_price,seckill_stock,per_limit,"
        "start_time,end_time,status,is_stackable,created_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        data + (user.id,),
    )
    await audit.log_action(user.id, "marketing", audit.ACTION_ADD, f"seckill:{aid}", f"新增秒杀活动「{body.name.strip()}」")
    return aid


# ==================== 满减满折 ====================


def _full_item(r: dict) -> dict:
    stage_code, stage_text = _act_stage(r["start_time"], r["end_time"])
    return {
        "id": r["id"],
        "name": r["name"],
        "type": r["type"],
        "typeText": "满减" if r["type"] == 1 else "满折",
        "threshold": _money(r["threshold"]),
        "discountValue": _money(r["discount_value"]),
        "scope": r["scope"],
        "scopeText": SCOPE_TEXT.get(r["scope"], ""),
        "scopeIds": r["scope_ids"] or "",
        "startTime": r["start_time"],
        "endTime": r["end_time"],
        "isStackable": r["is_stackable"],
        "status": stage_code,
        "statusText": stage_text,
        "createdAt": r["created_at"],
    }


async def list_full_discounts(page: int, page_size: int, filters: dict) -> dict:
    where = ["1=1"]
    params: list = []
    if filters.get("keyword"):
        where.append("f.name LIKE %s")
        params.append(f"%{filters['keyword']}%")
    if filters.get("type") not in (None, ""):
        where.append("f.type=%s")
        params.append(int(filters["type"]))
    cond = " AND ".join(where)
    total = await database.fetch_one(
        f"SELECT COUNT(*) AS c FROM full_discount_activities f WHERE {cond}", params
    )
    rows = await database.fetch_all(
        f"SELECT * FROM full_discount_activities f WHERE {cond} ORDER BY f.id DESC LIMIT %s OFFSET %s",
        params + [page_size, (page - 1) * page_size],
    )
    return {
        "list": [_full_item(r) for r in rows],
        "total": total["c"],
        "page": page,
        "page_size": page_size,
    }


async def save_full_discount(activity_id: int | None, body, user) -> int:
    if body.type == 1 and body.discount_value <= 0:
        bad_request("满减金额必须大于 0")
    if body.type == 2 and (body.discount_value <= 0 or body.discount_value >= 10):
        bad_request("满折折扣需大于 0 且小于 10")
    _check_time(body.start_time, body.end_time, "满减活动")
    data = (
        body.name.strip(), body.type, body.threshold, body.discount_value, body.scope, body.scope_ids,
        body.start_time, body.end_time, body.is_stackable,
    )
    if activity_id:
        row = await database.fetch_one("SELECT id,name FROM full_discount_activities WHERE id=%s", (activity_id,))
        if not row:
            not_found("满减活动不存在")
        await database.execute(
            "UPDATE full_discount_activities SET name=%s,type=%s,threshold=%s,discount_value=%s,scope=%s,"
            "scope_ids=%s,start_time=%s,end_time=%s,is_stackable=%s WHERE id=%s",
            data + (activity_id,),
        )
        await audit.log_action(user.id, "marketing", audit.ACTION_EDIT, f"full-discount:{activity_id}", f"编辑满减活动「{body.name.strip()}」")
        return activity_id
    aid = await database.execute_return_id(
        "INSERT INTO full_discount_activities (name,type,threshold,discount_value,scope,scope_ids,"
        "start_time,end_time,is_stackable,created_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        data + (user.id,),
    )
    await audit.log_action(user.id, "marketing", audit.ACTION_ADD, f"full-discount:{aid}", f"新增满减活动「{body.name.strip()}」")
    return aid


# ==================== 拼团 ====================


def _group_item(r: dict) -> dict:
    stage_code, stage_text = _act_stage(r["start_time"], r["end_time"])
    return {
        "id": r["id"],
        "name": r["name"],
        "goodsId": r["goods_id"],
        "goodsName": r["goods_name"] or "",
        "leaderPrice": _money(r["leader_price"]),
        "memberPrice": _money(r["member_price"]),
        "groupSize": r["group_size"],
        "validHours": r["valid_hours"],
        "startTime": r["start_time"],
        "endTime": r["end_time"],
        "status": stage_code,
        "statusText": stage_text,
        "createdAt": r["created_at"],
    }


async def list_group_buys(page: int, page_size: int, filters: dict) -> dict:
    where = ["1=1"]
    params: list = []
    if filters.get("keyword"):
        where.append("(gb.name LIKE %s OR g.name LIKE %s)")
        params += [f"%{filters['keyword']}%", f"%{filters['keyword']}%"]
    cond = " AND ".join(where)
    total = await database.fetch_one(
        f"SELECT COUNT(*) AS c FROM group_buy_activities gb LEFT JOIN goods g ON g.id=gb.goods_id WHERE {cond}", params
    )
    rows = await database.fetch_all(
        "SELECT gb.*,g.name AS goods_name FROM group_buy_activities gb LEFT JOIN goods g ON g.id=gb.goods_id "
        f"WHERE {cond} ORDER BY gb.id DESC LIMIT %s OFFSET %s",
        params + [page_size, (page - 1) * page_size],
    )
    return {
        "list": [_group_item(r) for r in rows],
        "total": total["c"],
        "page": page,
        "page_size": page_size,
    }


async def save_group_buy(activity_id: int | None, body, user) -> int:
    goods = await database.fetch_one("SELECT id,name FROM goods WHERE id=%s", (body.goods_id,))
    if not goods:
        not_found("所选商品不存在")
    _check_time(body.start_time, body.end_time, "拼团活动")
    stage_code, _ = _act_stage(body.start_time, body.end_time)
    data = (
        body.name.strip(), body.goods_id, body.leader_price, body.member_price, body.group_size,
        body.valid_hours, body.start_time, body.end_time, stage_code,
    )
    if activity_id:
        row = await database.fetch_one("SELECT id,name FROM group_buy_activities WHERE id=%s", (activity_id,))
        if not row:
            not_found("拼团活动不存在")
        await database.execute(
            "UPDATE group_buy_activities SET name=%s,goods_id=%s,leader_price=%s,member_price=%s,group_size=%s,"
            "valid_hours=%s,start_time=%s,end_time=%s,status=%s WHERE id=%s",
            data + (activity_id,),
        )
        await audit.log_action(user.id, "marketing", audit.ACTION_EDIT, f"group-buy:{activity_id}", f"编辑拼团活动「{body.name.strip()}」")
        return activity_id
    aid = await database.execute_return_id(
        "INSERT INTO group_buy_activities (name,goods_id,leader_price,member_price,group_size,valid_hours,"
        "start_time,end_time,status,created_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        data + (user.id,),
    )
    await audit.log_action(user.id, "marketing", audit.ACTION_ADD, f"group-buy:{aid}", f"新增拼团活动「{body.name.strip()}」")
    return aid


# ==================== 分销 ====================


def _dist_item(r: dict) -> dict:
    return {
        "id": r["id"],
        "memberId": r["member_id"],
        "memberName": r["member_name"] or f"会员#{r['member_id']}",
        "memberPhone": r["member_phone"] or "",
        "level": r["level"],
        "levelText": DIST_LEVEL_TEXT.get(r["level"], ""),
        "commissionRate": _money(r["commission_rate"]),
        "status": r["status"],
        "statusText": DIST_STATUS_TEXT.get(r["status"], ""),
        "invitedBy": r["invited_by"],
        "totalCommission": _money(r["total_commission"]),
        "createdAt": r["created_at"],
    }


async def list_distributors(page: int, page_size: int, filters: dict) -> dict:
    where = ["1=1"]
    params: list = []
    if filters.get("keyword"):
        where.append("(m.nickname LIKE %s OR m.phone LIKE %s)")
        params += [f"%{filters['keyword']}%", f"%{filters['keyword']}%"]
    if filters.get("status") not in (None, ""):
        where.append("d.status=%s")
        params.append(int(filters["status"]))
    if filters.get("level") not in (None, ""):
        where.append("d.level=%s")
        params.append(int(filters["level"]))
    cond = " AND ".join(where)
    base_from = (
        "FROM distributor d LEFT JOIN members m ON m.id=d.member_id LEFT JOIN "
        "(SELECT distributor_id,COALESCE(SUM(amount),0) AS total_commission FROM commission_logs GROUP BY distributor_id) c "
        "ON c.distributor_id=d.id"
    )
    total = await database.fetch_one(f"SELECT COUNT(*) AS c {base_from} WHERE {cond}", params)
    rows = await database.fetch_all(
        "SELECT d.*,m.nickname AS member_name,m.phone AS member_phone,COALESCE(c.total_commission,0) AS total_commission "
        f"{base_from} WHERE {cond} ORDER BY d.id DESC LIMIT %s OFFSET %s",
        params + [page_size, (page - 1) * page_size],
    )
    return {
        "list": [_dist_item(r) for r in rows],
        "total": total["c"],
        "page": page,
        "page_size": page_size,
    }


async def save_distributor(dist_id: int | None, body, user) -> int:
    member = await database.fetch_one("SELECT id,nickname FROM members WHERE id=%s", (body.member_id,))
    if not member:
        not_found("所选会员不存在")
    if getattr(body, "invited_by", None):
        if body.invited_by == body.member_id:
            bad_request("邀请人不能是分销会员本人")
        inviter = await database.fetch_one("SELECT id FROM members WHERE id=%s", (body.invited_by,))
        if not inviter:
            not_found("邀请人会员不存在")
    if dist_id:
        row = await database.fetch_one("SELECT id,member_id FROM distributor WHERE id=%s", (dist_id,))
        if not row:
            not_found("分销商不存在")
        if row["member_id"] != body.member_id:
            dup = await database.fetch_one(
                "SELECT id FROM distributor WHERE member_id=%s AND id<>%s", (body.member_id, dist_id)
            )
            if dup:
                duplicate("该会员已是分销商")
        await database.execute(
            "UPDATE distributor SET member_id=%s,level=%s,commission_rate=%s,status=%s,invited_by=%s WHERE id=%s",
            (body.member_id, body.level, body.commission_rate, body.status, body.invited_by, dist_id),
        )
        await audit.log_action(user.id, "marketing", audit.ACTION_EDIT, f"distributor:{dist_id}", f"编辑分销商「{member['nickname']}」")
        return dist_id
    dup = await database.fetch_one("SELECT id FROM distributor WHERE member_id=%s", (body.member_id,))
    if dup:
        duplicate("该会员已是分销商")
    did = await database.execute_return_id(
        "INSERT INTO distributor (member_id,level,commission_rate,status,invited_by,created_by) "
        "VALUES (%s,%s,%s,%s,%s,%s)",
        (body.member_id, body.level, body.commission_rate, body.status, body.invited_by, user.id),
    )
    await audit.log_action(user.id, "marketing", audit.ACTION_ADD, f"distributor:{did}", f"新增分销商「{member['nickname']}」")
    return did


async def list_commission_logs(dist_id: int, page: int, page_size: int) -> dict:
    row = await database.fetch_one("SELECT id,member_id FROM distributor WHERE id=%s", (dist_id,))
    if not row:
        not_found("分销商不存在")
    total = await database.fetch_one(
        "SELECT COUNT(*) AS c FROM commission_logs WHERE distributor_id=%s", (dist_id,)
    )
    rows = await database.fetch_all(
        "SELECT cl.id,cl.distributor_id,cl.amount,cl.status,cl.created_at,o.order_no "
        "FROM commission_logs cl LEFT JOIN orders o ON o.id=cl.order_id "
        "WHERE cl.distributor_id=%s ORDER BY cl.id DESC LIMIT %s OFFSET %s",
        (dist_id, page_size, (page - 1) * page_size),
    )
    return {
        "list": [
            {
                "id": r["id"],
                "orderNo": r["order_no"] or "",
                "amount": _money(r["amount"]),
                "status": r["status"],
                "statusText": COMMISSION_STATUS_TEXT.get(r["status"], ""),
                "createdAt": r["created_at"],
            }
            for r in rows
        ],
        "total": total["c"],
        "page": page,
        "page_size": page_size,
    }


# ==================== 下拉选项 ====================

async def goods_options() -> list[dict]:
    rows = await database.fetch_all(
        "SELECT id,name,price FROM goods WHERE status=1 ORDER BY id ASC LIMIT 200"
    )
    return [{"id": r["id"], "name": r["name"], "price": _money(r["price"])} for r in rows]


async def sku_options(goods_id: int) -> list[dict]:
    rows = await database.fetch_all(
        "SELECT id,sku_code,price,stock FROM goods_sku WHERE goods_id=%s AND status=1", (goods_id,)
    )
    return [{"id": r["id"], "skuCode": r["sku_code"], "price": _money(r["price"]), "stock": r["stock"]} for r in rows]


async def member_options() -> list[dict]:
    rows = await database.fetch_all(
        "SELECT m.id,m.nickname,m.phone FROM members m LEFT JOIN distributor d ON d.member_id=m.id "
        "WHERE d.id IS NULL AND m.status=1 ORDER BY m.id ASC LIMIT 200"
    )
    return [{"id": r["id"], "nickname": r["nickname"], "phone": r["phone"] or ""} for r in rows]
