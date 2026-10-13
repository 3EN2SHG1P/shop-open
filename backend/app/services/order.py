import csv
import io

from core import audit, database
from core.errors import bad_request, duplicate, not_found, state_error
from core.money import f2 as _money
from schemas.order import AfterSaleAudit, BatchShipReq, ExpressSave, PriceReq, ShipReq

ORDER_STATUS_TEXT = {1: "待付款", 2: "待发货", 3: "已发货", 4: "已完成", 5: "已取消", 6: "售后中"}
PAY_TYPE_TEXT = {1: "扫码支付", 2: "快捷支付"}
PAY_STATUS_TEXT = {0: "未支付", 1: "已支付"}
ORDER_SOURCE_TEXT = {"pc": "PC", "h5": "H5", "mp": "小程序", "app": "APP"}
AS_TYPE_TEXT = {1: "仅退款", 2: "退货退款"}
AS_STATUS_TEXT = {1: "待审核", 2: "处理中", 3: "已完成", 4: "已拒绝"}


def _op_name(user):
    return user.real_name or user.username


def _build_where(filters: dict, with_status: bool = True) -> tuple[str, list]:
    where = ["1=1"]
    params: list = []
    if filters.get("order_no"):
        where.append("o.order_no LIKE %s")
        params.append(f"%{filters['order_no']}%")
    if filters.get("member"):
        where.append("(m.nickname LIKE %s OR m.phone LIKE %s)")
        params += [f"%{filters['member']}%", f"%{filters['member']}%"]
    if filters.get("receiver"):
        where.append("(o.receiver_name LIKE %s OR o.receiver_phone LIKE %s)")
        params += [f"%{filters['receiver']}%", f"%{filters['receiver']}%"]
    if filters.get("pay_status") not in (None, ""):
        where.append("o.pay_status=%s")
        params.append(int(filters["pay_status"]))
    if with_status and filters.get("order_status") not in (None, ""):
        where.append("o.order_status=%s")
        params.append(int(filters["order_status"]))
    if filters.get("order_source"):
        where.append("o.order_source=%s")
        params.append(filters["order_source"])
    if filters.get("start_date"):
        where.append("DATE(o.created_at)>=%s")
        params.append(filters["start_date"])
    if filters.get("end_date"):
        where.append("DATE(o.created_at)<=%s")
        params.append(filters["end_date"])
    return " AND ".join(where), params


async def list_orders(page: int, page_size: int, filters: dict) -> dict:
    cond, params = _build_where(filters, with_status=True)
    total = await database.fetch_one(
        f"SELECT COUNT(*) AS c FROM orders o LEFT JOIN members m ON m.id=o.member_id WHERE {cond}", params
    )
    rows = await database.fetch_all(
        "SELECT o.id,o.order_no,o.member_id,o.total_amount,o.freight_amount,o.coupon_amount,o.points_amount,"
        "o.pay_amount,o.pay_type,o.pay_status,o.order_status,o.receiver_name,o.receiver_phone,o.order_source,"
        "o.created_at,m.nickname AS member_name,m.phone AS member_phone,"
        "(SELECT oi.goods_name FROM order_items oi WHERE oi.order_id=o.id ORDER BY oi.id LIMIT 1) AS goods_name,"
        "(SELECT SUM(oi.quantity) FROM order_items oi WHERE oi.order_id=o.id) AS goods_qty,"
        "(SELECT COUNT(*) FROM order_items oi WHERE oi.order_id=o.id) AS goods_kinds "
        f"FROM orders o LEFT JOIN members m ON m.id=o.member_id WHERE {cond} ORDER BY o.id DESC LIMIT %s OFFSET %s",
        params + [page_size, (page - 1) * page_size],
    )
    cond_ns, params_ns = _build_where(filters, with_status=False)
    counts_rows = await database.fetch_all(
        f"SELECT o.order_status AS s, COUNT(*) AS c FROM orders o LEFT JOIN members m ON m.id=o.member_id "
        f"WHERE {cond_ns} GROUP BY o.order_status",
        params_ns,
    )
    counts = {str(i): 0 for i in range(1, 7)}
    total_count = 0
    for r in counts_rows:
        counts[str(r["s"])] = r["c"]
        total_count += r["c"]
    counts["all"] = total_count
    items = []
    for r in rows:
        qty = r["goods_qty"] or 0
        summary = r["goods_name"] or ""
        if qty > 1:
            summary = f"{summary} 等{qty}件"
        items.append({
            "id": r["id"],
            "orderNo": r["order_no"],
            "memberId": r["member_id"],
            "memberName": r["member_name"] or f"会员#{r['member_id']}",
            "memberPhone": r["member_phone"] or "",
            "totalAmount": _money(r["total_amount"]),
            "freightAmount": _money(r["freight_amount"]),
            "couponAmount": _money(r["coupon_amount"]),
            "pointsAmount": _money(r["points_amount"]),
            "payAmount": _money(r["pay_amount"]),
            "payType": r["pay_type"],
            "payTypeText": PAY_TYPE_TEXT.get(r["pay_type"], ""),
            "payStatus": r["pay_status"],
            "payStatusText": PAY_STATUS_TEXT.get(r["pay_status"], ""),
            "orderStatus": r["order_status"],
            "orderStatusText": ORDER_STATUS_TEXT.get(r["order_status"], ""),
            "receiverName": r["receiver_name"],
            "receiverPhone": r["receiver_phone"],
            "goodsSummary": summary,
            "goodsKinds": r["goods_kinds"] or 0,
            "orderSource": r["order_source"],
            "orderSourceText": ORDER_SOURCE_TEXT.get(r["order_source"], r["order_source"] or ""),
            "createdAt": r["created_at"],
        })
    return {"list": items, "total": total["c"], "orderStatusCounts": counts, "page": page, "page_size": page_size}


async def order_detail(order_id: int) -> dict:
    row = await database.fetch_one(
        "SELECT o.*,m.nickname AS member_name,m.phone AS member_phone FROM orders o "
        "LEFT JOIN members m ON m.id=o.member_id WHERE o.id=%s",
        (order_id,),
    )
    if not row:
        not_found("订单不存在")
    items = await database.fetch_all(
        "SELECT goods_id,sku_id,goods_name,goods_image,spec_value,price,quantity,subtotal FROM order_items "
        "WHERE order_id=%s ORDER BY id ASC",
        (order_id,),
    )
    logs = await database.fetch_all(
        "SELECT operator_type,operator_id,operator_name,action,content,created_at FROM order_logs "
        "WHERE order_id=%s ORDER BY id ASC",
        (order_id,),
    )
    as_rows = await database.fetch_all(
        "SELECT id,after_sale_no,type,reason,amount,status,handle_note,return_logistics_company,"
        "return_logistics_no,handle_time,created_at FROM after_sales WHERE order_id=%s ORDER BY id ASC",
        (order_id,),
    )
    return {
        "id": row["id"],
        "orderNo": row["order_no"],
        "memberId": row["member_id"],
        "memberName": row["member_name"] or f"会员#{row['member_id']}",
        "memberPhone": row["member_phone"] or "",
        "totalAmount": _money(row["total_amount"]),
        "freightAmount": _money(row["freight_amount"]),
        "couponAmount": _money(row["coupon_amount"]),
        "pointsAmount": _money(row["points_amount"]),
        "payAmount": _money(row["pay_amount"]),
        "payType": row["pay_type"],
        "payTypeText": PAY_TYPE_TEXT.get(row["pay_type"], ""),
        "payStatus": row["pay_status"],
        "payStatusText": PAY_STATUS_TEXT.get(row["pay_status"], ""),
        "orderStatus": row["order_status"],
        "orderStatusText": ORDER_STATUS_TEXT.get(row["order_status"], ""),
        "receiver": {"name": row["receiver_name"], "phone": row["receiver_phone"], "address": row["receiver_address"]},
        "logistics": {"company": row["logistics_company"], "no": row["logistics_no"]},
        "buyerMessage": row["buyer_message"],
        "orderSource": row["order_source"],
        "orderSourceText": ORDER_SOURCE_TEXT.get(row["order_source"], row["order_source"] or ""),
        "remark": row["remark"],
        "paidAt": row["paid_at"],
        "shippedAt": row["shipped_at"],
        "completedAt": row["completed_at"],
        "canceledAt": row["canceled_at"],
        "createdAt": row["created_at"],
        "items": [
            {
                "goodsId": it["goods_id"],
                "skuId": it["sku_id"],
                "goodsName": it["goods_name"],
                "goodsImage": it["goods_image"],
                "specValue": it["spec_value"],
                "price": _money(it["price"]),
                "quantity": it["quantity"],
                "subtotal": _money(it["subtotal"]),
            }
            for it in items
        ],
        "logs": [
            {
                "operatorType": lg["operator_type"],
                "operatorId": lg["operator_id"],
                "operatorName": lg["operator_name"],
                "action": lg["action"],
                "content": lg["content"],
                "createdAt": lg["created_at"],
            }
            for lg in logs
        ],
        "afterSales": [
            {
                "id": a["id"],
                "afterSaleNo": a["after_sale_no"],
                "type": a["type"],
                "typeText": AS_TYPE_TEXT.get(a["type"], ""),
                "reason": a["reason"],
                "amount": _money(a["amount"]),
                "status": a["status"],
                "statusText": AS_STATUS_TEXT.get(a["status"], ""),
                "handleNote": a["handle_note"],
                "returnLogisticsCompany": a["return_logistics_company"],
                "returnLogisticsNo": a["return_logistics_no"],
                "handleTime": a["handle_time"],
                "createdAt": a["created_at"],
            }
            for a in as_rows
        ],
    }


async def _get_order(order_id: int) -> dict:
    row = await database.fetch_one("SELECT * FROM orders WHERE id=%s", (order_id,))
    if not row:
        not_found("订单不存在")
    return row


async def _insert_log(cur, order_id: int, user, action: str, content: str):
    await cur.execute(
        "INSERT INTO order_logs (order_id,operator_type,operator_id,operator_name,action,content) "
        "VALUES (%s,2,%s,%s,%s,%s)",
        (order_id, user.id, user.real_name or user.username, action, content),
    )


async def update_price(order_id: int, body: PriceReq, user) -> None:
    row = await _get_order(order_id)
    if row["order_status"] != 1:
        state_error("仅待付款订单可修改价格")
    new_amount = round(body.amount, 2)
    old_amount = _money(row["pay_amount"])
    note = f"订单金额由 {old_amount} 调整为 {new_amount}"
    if body.reason:
        note += f"（{body.reason}）"
    async with database.transaction() as cur:
        await cur.execute("UPDATE orders SET pay_amount=%s WHERE id=%s", (new_amount, order_id))
        await _insert_log(cur, order_id, user, "修改价格", note)
    await audit.log_action(user.id, "order", audit.ACTION_EDIT, f"order:{row['order_no']}", note)


async def ship_order(order_id: int, body: ShipReq, user) -> None:
    row = await _get_order(order_id)
    if row["order_status"] != 2:
        state_error("仅待发货订单可发货")
    async with database.transaction() as cur:
        updated = await cur.execute(
            "UPDATE orders SET order_status=3,logistics_company=%s,logistics_no=%s,shipped_at=NOW() "
            "WHERE id=%s AND order_status=2",
            (body.logistics_company, body.logistics_no, order_id),
        )
        if not updated:
            state_error("订单状态已变化，请刷新后重试")
        await _insert_log(cur, order_id, user, "订单发货", f"{body.logistics_company} 运单号 {body.logistics_no}")
    await audit.log_action(user.id, "order", audit.ACTION_EDIT, f"order:{row['order_no']}", "订单发货")


async def batch_ship(body: BatchShipReq, user) -> None:
    done: list[str] = []
    async with database.transaction() as cur:
        for item in body.orders:
            await cur.execute("SELECT * FROM orders WHERE id=%s FOR UPDATE", (item.order_id,))
            row = await cur.fetchone()
            if not row:
                not_found(f"订单 {item.order_id} 不存在")
            if row["order_status"] != 2:
                state_error(f"订单 {row['order_no']} 非待发货状态，无法发货")
            await cur.execute(
                "UPDATE orders SET order_status=3,logistics_company=%s,logistics_no=%s,shipped_at=NOW() WHERE id=%s",
                (item.logistics_company, item.logistics_no, item.order_id),
            )
            await _insert_log(cur, item.order_id, user, "订单发货", f"{item.logistics_company} 运单号 {item.logistics_no}")
            done.append(row["order_no"])
    await audit.log_action(user.id, "order", audit.ACTION_EDIT, "order:batch_ship", f"批量发货 {len(done)} 单")


async def cancel_order(order_id: int, user) -> None:
    row = await _get_order(order_id)
    if row["order_status"] != 1:
        state_error("仅未付款订单可取消")
    async with database.transaction() as cur:
        # 明细读取放进事务；注意事务内只能用传入的 cur，调 database.fetch_* 会另取连接、不在同一事务
        await cur.execute(
            "SELECT goods_id,sku_id,quantity FROM order_items WHERE order_id=%s", (order_id,)
        )
        items = await cur.fetchall()
        total_qty = sum(it["quantity"] for it in items)
        for it in items:
            if it["sku_id"]:
                await cur.execute(
                    "UPDATE goods_sku SET stock=stock+%s,version=version+1 WHERE id=%s",
                    (it["quantity"], it["sku_id"]),
                )
            await cur.execute(
                "UPDATE goods SET stock=stock+%s WHERE id=%s", (it["quantity"], it["goods_id"])
            )
        updated = await cur.execute(
            "UPDATE orders SET order_status=5,canceled_at=NOW() WHERE id=%s AND order_status=1", (order_id,)
        )
        if not updated:
            # 并发下已被取消/支付：抛错让事务回滚，避免库存被重复回补
            state_error("订单状态已变更，请刷新后重试")
        await _insert_log(cur, order_id, user, "取消订单", f"取消未付款订单，回补库存 {total_qty} 件")
    await audit.log_action(user.id, "order", audit.ACTION_EDIT, f"order:{row['order_no']}", "取消未付款订单")


async def export_orders(filters: dict) -> bytes:
    cond, params = _build_where(filters, with_status=True)
    rows = await database.fetch_all(
        "SELECT o.order_no,o.member_id,o.total_amount,o.freight_amount,o.coupon_amount,o.points_amount,"
        "o.pay_amount,o.pay_type,o.pay_status,o.order_status,o.receiver_name,o.receiver_phone,o.receiver_address,"
        "o.order_source,o.created_at,m.nickname AS member_name,"
        "(SELECT oi.goods_name FROM order_items oi WHERE oi.order_id=o.id ORDER BY oi.id LIMIT 1) AS goods_name,"
        "(SELECT SUM(oi.quantity) FROM order_items oi WHERE oi.order_id=o.id) AS goods_qty "
        f"FROM orders o LEFT JOIN members m ON m.id=o.member_id WHERE {cond} ORDER BY o.id DESC LIMIT 50000",
        params,
    )
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["订单号", "会员", "收货人", "收货电话", "收货地址", "商品", "件数", "商品总额", "运费",
                     "优惠金额", "积分抵扣", "实付金额", "支付方式", "支付状态", "订单状态", "订单来源", "下单时间"])
    for r in rows:
        qty = r["goods_qty"] or 0
        goods = r["goods_name"] or ""
        if qty > 1:
            goods = f"{goods} 等{qty}件"
        writer.writerow([
            r["order_no"], r["member_name"] or "", r["receiver_name"], r["receiver_phone"], r["receiver_address"],
            goods, qty, r["total_amount"], r["freight_amount"], r["coupon_amount"], r["points_amount"],
            r["pay_amount"], PAY_TYPE_TEXT.get(r["pay_type"], ""), PAY_STATUS_TEXT.get(r["pay_status"], ""),
            ORDER_STATUS_TEXT.get(r["order_status"], ""), ORDER_SOURCE_TEXT.get(r["order_source"], ""), r["created_at"],
        ])
    return ("\ufeff" + buf.getvalue()).encode("utf-8")


async def _fallback_target(order_row: dict, finished: bool) -> int:
    if finished:
        if order_row["completed_at"]:
            return 4
        return 5
    if order_row["completed_at"]:
        return 4
    if order_row["shipped_at"]:
        return 3
    if order_row["paid_at"]:
        return 2
    return 1


async def _finish_order_status(cur, order_row: dict, user, after_sale_no: str, finished: bool, content: str):
    target = await _fallback_target(order_row, finished)
    if target == 5:
        await cur.execute(
            "UPDATE orders SET order_status=5,canceled_at=COALESCE(canceled_at,NOW()) WHERE id=%s",
            (order_row["id"],),
        )
    else:
        await cur.execute("UPDATE orders SET order_status=%s WHERE id=%s", (target, order_row["id"]))
    await _insert_log(cur, order_row["id"], user, "售后结束", f"售后单 {after_sale_no}：{content}")
    return target


async def list_after_sales(page: int, page_size: int, filters: dict) -> dict:
    base_where = ["1=1"]
    base_params: list = []
    if filters.get("type") not in (None, ""):
        base_where.append("a.type=%s")
        base_params.append(int(filters["type"]))
    if filters.get("keyword"):
        base_where.append("(a.after_sale_no LIKE %s OR o.order_no LIKE %s OR m.nickname LIKE %s)")
        base_params += [f"%{filters['keyword']}%", f"%{filters['keyword']}%", f"%{filters['keyword']}%"]
    where = list(base_where)
    params = list(base_params)
    if filters.get("status") not in (None, ""):
        where.append("a.status=%s")
        params.append(int(filters["status"]))
    cond = " AND ".join(where)
    base_cond = " AND ".join(base_where)
    total = await database.fetch_one(
        f"SELECT COUNT(*) AS c FROM after_sales a JOIN orders o ON o.id=a.order_id "
        f"LEFT JOIN members m ON m.id=a.member_id WHERE {cond}",
        params,
    )
    rows = await database.fetch_all(
        "SELECT a.id,a.after_sale_no,a.order_id,a.member_id,a.type,a.reason,a.amount,a.status,a.handle_note,"
        "a.return_logistics_company,a.return_logistics_no,a.handle_time,a.created_at,"
        "o.order_no,o.order_status AS order_status,m.nickname AS member_name,"
        "(SELECT oi.goods_name FROM order_items oi WHERE oi.order_id=a.order_id ORDER BY oi.id LIMIT 1) AS goods_name "
        f"FROM after_sales a JOIN orders o ON o.id=a.order_id "
        f"LEFT JOIN members m ON m.id=a.member_id WHERE {cond} ORDER BY a.id DESC LIMIT %s OFFSET %s",
        params + [page_size, (page - 1) * page_size],
    )
    counts_rows = await database.fetch_all(
        f"SELECT a.status AS s, COUNT(*) AS c FROM after_sales a JOIN orders o ON o.id=a.order_id "
        f"LEFT JOIN members m ON m.id=a.member_id WHERE {base_cond} GROUP BY a.status",
        base_params,
    )
    counts = {str(i): 0 for i in range(1, 5)}
    total_count = 0
    for r in counts_rows:
        counts[str(r["s"])] = r["c"]
        total_count += r["c"]
    counts["all"] = total_count
    items = []
    for r in rows:
        items.append({
            "id": r["id"],
            "afterSaleNo": r["after_sale_no"],
            "orderId": r["order_id"],
            "orderNo": r["order_no"],
            "memberId": r["member_id"],
            "memberName": r["member_name"] or f"会员#{r['member_id']}",
            "goodsName": r["goods_name"] or "",
            "type": r["type"],
            "typeText": AS_TYPE_TEXT.get(r["type"], ""),
            "reason": r["reason"],
            "amount": _money(r["amount"]),
            "status": r["status"],
            "statusText": AS_STATUS_TEXT.get(r["status"], ""),
            "orderStatus": r["order_status"],
            "handleNote": r["handle_note"],
            "returnLogisticsCompany": r["return_logistics_company"],
            "returnLogisticsNo": r["return_logistics_no"],
            "handleTime": r["handle_time"],
            "createdAt": r["created_at"],
        })
    return {"list": items, "total": total["c"], "statusCounts": counts, "page": page, "page_size": page_size}


async def audit_after_sale(aid: int, body: AfterSaleAudit, user) -> None:
    arow = await database.fetch_one("SELECT * FROM after_sales WHERE id=%s", (aid,))
    if not arow:
        not_found("售后申请不存在")
    if arow["status"] != 1:
        state_error("仅待审核的售后申请可审核")
    order_row = await database.fetch_one("SELECT * FROM orders WHERE id=%s", (arow["order_id"],))
    default_note = "同意退款申请" if (body.agree and arow["type"] == 1) else ("同意退货退款，等待买家退货" if body.agree else "拒绝售后申请")
    handle_note = body.handle_note.strip() or default_note
    new_status = 3 if (body.agree and arow["type"] == 1) else (2 if body.agree else 4)
    async with database.transaction() as cur:
        await cur.execute(
            "UPDATE after_sales SET status=%s,handle_note=%s,handle_time=NOW(),handle_by=%s WHERE id=%s",
            (new_status, handle_note, user.id, aid),
        )
        if order_row and order_row["order_status"] == 6:
            if new_status == 3:
                await _finish_order_status(cur, order_row, user, arow["after_sale_no"], True, "售后完成")
            elif new_status == 4:
                await _finish_order_status(cur, order_row, user, arow["after_sale_no"], False, "售后申请被拒绝")
        action_text = "售后审核同意" if body.agree else "售后审核拒绝"
    await audit.log_action(user.id, "order", audit.ACTION_AUDIT, f"after-sale:{arow['after_sale_no']}", action_text)


async def confirm_after_sale_receipt(aid: int, user) -> None:
    arow = await database.fetch_one("SELECT * FROM after_sales WHERE id=%s", (aid,))
    if not arow:
        not_found("售后申请不存在")
    if arow["type"] != 2:
        state_error("该售后类型无需确认退货收货")
    if arow["status"] != 2:
        state_error("仅处理中的退货退款可确认收货")
    order_row = await database.fetch_one("SELECT * FROM orders WHERE id=%s", (arow["order_id"],))
    async with database.transaction() as cur:
        await cur.execute(
            "UPDATE after_sales SET status=3,handle_note=%s,handle_time=NOW(),handle_by=%s WHERE id=%s",
            ("确认退货收货，退款完成", user.id, aid),
        )
        if order_row and order_row["order_status"] == 6:
            await _finish_order_status(cur, order_row, user, arow["after_sale_no"], True, "确认退货收货，退款完成")
    await audit.log_action(user.id, "order", audit.ACTION_AUDIT, f"after-sale:{arow['after_sale_no']}", "确认退货收货")


async def list_express(status: int | None = None) -> list[dict]:
    if status is not None:
        rows = await database.fetch_all(
            "SELECT id,name,code,status,created_at FROM express_companies WHERE status=%s ORDER BY id ASC", (status,)
        )
    else:
        rows = await database.fetch_all("SELECT id,name,code,status,created_at FROM express_companies ORDER BY id ASC")
    return [
        {"id": r["id"], "name": r["name"], "code": r["code"], "status": r["status"], "createdAt": r["created_at"]}
        for r in rows
    ]


async def create_express(body: ExpressSave, user) -> int:
    exist = await database.fetch_one("SELECT id FROM express_companies WHERE code=%s", (body.code,))
    if exist:
        duplicate("快递公司编码已存在")
    eid = await database.execute_return_id(
        "INSERT INTO express_companies (name,code,status) VALUES (%s,%s,1)", (body.name, body.code)
    )
    await audit.log_action(user.id, "order", audit.ACTION_ADD, f"express:{body.code}", f"新增快递公司 {body.name}")
    return eid
