import random
import time

from core import database
from core.errors import bad_request, not_found, state_error

AS_TYPE_TEXT = {1: "仅退款", 2: "退货退款"}
AS_STATUS_TEXT = {1: "待审核", 2: "处理中", 3: "已完成", 4: "已拒绝"}


from core.money import f2 as _money, d, q2, sub_money, gt


def _gen_as_no() -> str:
    return f"AS{time.strftime('%Y%m%d%H%M%S')}{random.randint(1000, 9999)}"


def _as_item(r: dict) -> dict:
    return {
        "id": r["id"],
        "afterSaleNo": r["after_sale_no"],
        "orderId": r["order_id"],
        "orderNo": r["order_no"],
        "goodsName": r["goods_name"] or "",
        "goodsImage": r["goods_image"] or "",
        "type": r["type"],
        "typeText": AS_TYPE_TEXT.get(r["type"], ""),
        "reason": r["reason"] or "",
        "amount": _money(r["amount"]),
        "status": r["status"],
        "statusText": AS_STATUS_TEXT.get(r["status"], ""),
        "handleNote": r["handle_note"] or "",
        "returnLogisticsCompany": r["return_logistics_company"] or "",
        "returnLogisticsNo": r["return_logistics_no"] or "",
        "handleTime": r["handle_time"],
        "createdAt": r["created_at"],
    }


async def apply_after_sale(member_id: int, body) -> int:
    order = await database.fetch_one(
        "SELECT * FROM orders WHERE id=%s AND member_id=%s", (body.order_id, member_id)
    )
    if not order:
        not_found("订单不存在")
    if order["pay_status"] != 1:
        state_error("当前订单状态不支持发起售后")
    if body.type == 1 and order["order_status"] not in (2, 3, 4):
        state_error("当前订单状态不支持仅退款")
    if body.type == 2 and order["order_status"] not in (3, 4):
        state_error("待发货订单仅支持仅退款")
    active = await database.fetch_one(
        "SELECT id FROM after_sales WHERE order_id=%s AND status IN (1,2) LIMIT 1", (order["id"],)
    )
    if active:
        state_error("该订单存在进行中的售后申请")
    amount = q2(body.amount) if body.amount is not None else d(order["pay_amount"])
    # 可退上限 = 实付 - 历史已通过/进行中的退款合计。
    # 原先只比对单笔 pay_amount：前一笔售后被驳回后可以再次申请，多次合计能远超实付金额。
    refunded = await database.fetch_one(
        "SELECT IFNULL(SUM(amount),0) AS s FROM after_sales WHERE order_id=%s AND status IN (1,2,3)",
        (order["id"],),
    )
    remain = sub_money(order["pay_amount"], refunded["s"])
    if not gt(remain, 0):
        state_error("该订单无可退金额")
    if not gt(amount, 0) or gt(amount, remain):
        bad_request(f"售后金额超出剩余可退上限（剩余可退 {float(remain)} 元）")
    member = await database.fetch_one("SELECT nickname FROM members WHERE id=%s", (member_id,))
    as_no = _gen_as_no()
    async with database.transaction() as cur:
        aid = await cur.execute(
            "INSERT INTO after_sales (after_sale_no,order_id,member_id,type,reason,amount,status,created_by) "
            "VALUES (%s,%s,%s,%s,%s,%s,1,%s)",
            (as_no, order["id"], member_id, body.type, body.reason, amount, member_id),
        )
        aid = cur.lastrowid
        await cur.execute(
            "UPDATE orders SET order_status=6 WHERE id=%s AND order_status IN (2,3,4)",
            (order["id"],),
        )
        await cur.execute(
            "INSERT INTO order_logs (order_id,operator_type,operator_id,operator_name,action,content) "
            "VALUES (%s,1,%s,%s,%s,%s)",
            (order["id"], member_id, member["nickname"] or "", "申请售后",
             f"发起售后申请：{AS_TYPE_TEXT.get(body.type, '')}"),
        )
        await cur.execute(
            "INSERT INTO member_logs (member_id,action_type,action) VALUES (%s,'after_sale',%s)",
            (member_id, f"发起售后申请 {as_no}"),
        )
    return aid


async def list_after_sales(member_id: int, page: int, page_size: int, status: int | None = None) -> dict:
    where = ["a.member_id=%s"]
    params: list = [member_id]
    if status not in (None, ""):
        where.append("a.status=%s")
        params.append(int(status))
    cond = " AND ".join(where)
    total = await database.fetch_one(f"SELECT COUNT(*) AS c FROM after_sales a WHERE {cond}", params)
    rows = await database.fetch_all(
        "SELECT a.id,a.after_sale_no,a.order_id,a.type,a.reason,a.amount,a.status,a.handle_note,"
        "a.return_logistics_company,a.return_logistics_no,a.handle_time,a.created_at,"
        "o.order_no,(SELECT oi.goods_name FROM order_items oi WHERE oi.order_id=a.order_id ORDER BY oi.id LIMIT 1) AS goods_name,"
        "(SELECT oi.goods_image FROM order_items oi WHERE oi.order_id=a.order_id ORDER BY oi.id LIMIT 1) AS goods_image "
        f"FROM after_sales a JOIN orders o ON o.id=a.order_id WHERE {cond} ORDER BY a.id DESC LIMIT %s OFFSET %s",
        params + [page_size, (page - 1) * page_size],
    )
    return {
        "list": [_as_item(r) for r in rows],
        "total": total["c"],
        "page": page,
        "page_size": page_size,
    }


async def after_sale_detail(member_id: int, after_sale_id: int) -> dict:
    row = await database.fetch_one(
        "SELECT a.*,o.order_no,o.order_status,o.pay_amount,o.logistics_company,o.logistics_no "
        "FROM after_sales a JOIN orders o ON o.id=a.order_id WHERE a.id=%s AND a.member_id=%s",
        (after_sale_id, member_id),
    )
    if not row:
        not_found("售后单不存在")
    images = await database.fetch_all(
        "SELECT oi.goods_name,oi.goods_image,oi.spec_value,oi.price,oi.quantity "
        "FROM order_items oi WHERE oi.order_id=%s ORDER BY oi.id ASC", (row["order_id"],)
    )
    row["goods_name"] = images[0]["goods_name"] if images else ""
    row["goods_image"] = images[0]["goods_image"] if images else ""
    item = _as_item(row)
    item["orderStatus"] = row["order_status"]
    item["items"] = [
        {"goodsName": it["goods_name"], "goodsImage": it["goods_image"] or "", "specValue": it["spec_value"] or "",
         "price": _money(it["price"]), "quantity": it["quantity"]}
        for it in images
    ]
    return item


async def fill_logistics(member_id: int, after_sale_id: int, company: str, no: str) -> None:
    row = await database.fetch_one(
        "SELECT * FROM after_sales WHERE id=%s AND member_id=%s", (after_sale_id, member_id)
    )
    if not row:
        not_found("售后单不存在")
    if row["type"] != 2:
        state_error("仅退货退款售后需要填写退货运单")
    if row["status"] != 2:
        state_error("当前售后状态不可填写退货运单")
    await database.execute(
        "UPDATE after_sales SET return_logistics_company=%s,return_logistics_no=%s WHERE id=%s",
        (company, no, after_sale_id),
    )


async def cancel_after_sale(member_id: int, after_sale_id: int) -> None:
    row = await database.fetch_one(
        "SELECT * FROM after_sales WHERE id=%s AND member_id=%s", (after_sale_id, member_id)
    )
    if not row:
        not_found("售后单不存在")
    if row["status"] != 1:
        state_error("仅待审核的售后单可撤销")
    order = await database.fetch_one("SELECT * FROM orders WHERE id=%s", (row["order_id"],))
    member = await database.fetch_one("SELECT nickname FROM members WHERE id=%s", (member_id,))
    async with database.transaction() as cur:
        await cur.execute(
            "SELECT * FROM after_sales WHERE id=%s AND member_id=%s AND status=1 FOR UPDATE",
            (after_sale_id, member_id),
        )
        cur_row = await cur.fetchone()
        if not cur_row:
            state_error("售后单状态已变化，请刷新后重试")
        await cur.execute(
            "UPDATE after_sales SET status=4,handle_note='用户撤销申请',handle_time=NOW() WHERE id=%s",
            (after_sale_id,),
        )
        if order["completed_at"]:
            target = 4
        elif order["shipped_at"]:
            target = 3
        elif order["paid_at"]:
            target = 2
        else:
            target = 1
        await cur.execute(
            "UPDATE orders SET order_status=%s WHERE id=%s AND order_status=6", (target, order["id"])
        )
        await cur.execute(
            "INSERT INTO order_logs (order_id,operator_type,operator_id,operator_name,action,content) "
            "VALUES (%s,1,%s,%s,%s,%s)",
            (order["id"], member_id, member["nickname"] or "", "撤销售后",
             f"用户撤销售后申请 {row['after_sale_no']}"),
        )
        await cur.execute(
            "INSERT INTO member_logs (member_id,action_type,action) VALUES (%s,'after_sale',%s)",
            (member_id, f"撤销售后申请 {row['after_sale_no']}"),
        )
