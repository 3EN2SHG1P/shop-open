import random
import secrets
import time

from core import database
from core.config import config
from core.errors import (
    bad_request,
    buy_limit,
    coupon_unavailable,
    not_found,
    order_timeout,
    state_error,
    stock_not_enough,
)
from core.money import (
    ZERO,
    add_money,
    d,
    f2 as _money,
    gt,
    min_money,
    money_to_points,
    mul_money,
    points_to_money,
    q2,
    sub_money,
)
from services.shop_address import get_address
from services.shop_common import get_goods_image, get_sku, get_sku_spec_text

ORDER_STATUS_TEXT = {1: "待付款", 2: "待发货", 3: "已发货", 4: "已完成", 5: "已取消", 6: "售后中"}
PAY_TYPE_TEXT = {1: "扫码支付", 2: "快捷支付"}
PAY_STATUS_TEXT = {0: "未支付", 1: "已支付"}
_ACTIONS = {
    1: ["pay", "cancel"],
    2: ["remindShip"],
    3: ["confirm", "logistics", "afterSale"],
    4: ["again", "afterSale"],
    5: ["again"],
    6: ["viewAfterSale"],
}
POINTS_RATIO = 100
PREVIEW_TTL_SECONDS = 15 * 60

_preview_tokens: dict[str, dict] = {}


def _gen_no(prefix: str = "") -> str:
    return f"{prefix}{time.strftime('%Y%m%d%H%M%S')}{random.randint(1000, 9999)}"


async def _active_seckill(goods_id: int, sku_id: int) -> dict | None:
    return await database.fetch_one(
        "SELECT id,seckill_price FROM seckill_activities WHERE goods_id=%s AND status=1 "
        "AND (sku_id IS NULL OR sku_id=%s) AND start_time<=NOW() AND end_time>=NOW() "
        "ORDER BY id LIMIT 1",
        (goods_id, sku_id),
    )


async def _load_item(sku_id: int, goods_id: int, quantity: int) -> dict:
    sku = await get_sku(sku_id)
    if not sku or sku["goods_id"] != goods_id:
        not_found("商品规格不存在")
    if sku["goods_status"] != 1 or sku["sku_status"] != 1:
        not_found("商品已下架")
    if quantity > (sku["sku_stock"] or 0):
        stock_not_enough("商品库存不足")
    sec = await _active_seckill(goods_id, sku_id)
    # q2() 内部兜底 None：seckill_price 为 NULL 时 float(None) 会抛 TypeError
    price = q2(sec["seckill_price"]) if sec else q2(sku["sku_price"])
    return {
        "goodsId": goods_id,
        "skuId": sku_id,
        "goodsName": sku["goods_name"],
        "specText": await get_sku_spec_text(sku_id),
        "image": await get_goods_image(goods_id),
        "skuStock": sku["sku_stock"] or 0,
        "price": _money(price),
        "quantity": quantity,
        "subtotal": _money(mul_money(price, quantity)),
        "seckill": bool(sec),
    }


def _parse_scope_ids(value) -> list[int]:
    result = []
    if value:
        for part in str(value).split(","):
            if part.strip().isdigit():
                result.append(int(part.strip()))
    return result


def _coupon_eligible(c: dict, goods_items: list[dict]) -> tuple[bool, float]:
    scope_ids = _parse_scope_ids(c["scope_ids"])
    base = ZERO
    for it in goods_items:
        if it["seckill"]:
            continue
        if c["scope"] == 1:
            base += d(it["subtotal"])
        elif c["scope"] == 2 and it.get("categoryId") in scope_ids:
            base += d(it["subtotal"])
        elif c["scope"] == 3 and it["goodsId"] in scope_ids:
            base += d(it["subtotal"])
    # 先量化再比较，杜绝 float 边界抖动（如 100.00000000000001 被判不达 100 门槛）
    if lt(base, c["min_amount"]):
        return False, 0.0
    return True, _money(base)


def _coupon_discount(c: dict, base) -> float:
    base = d(base)
    if c["type"] == 2:
        discount = mul_money(base, 1 - d(c["rate"] or 1))
        # min 之后再量化：原先此处漏了 round，正确性依赖 amount 列恰好是 DECIMAL(10,2)
        if gt(c["amount"], 0):
            discount = min_money(discount, c["amount"])
        return _money(discount)
    return _money(min_money(c["amount"], base))


async def _member_usable_coupons(member_id: int) -> list[dict]:
    rows = await database.fetch_all(
        "SELECT cr.id AS receive_id,cr.coupon_id,c.name,c.type,c.amount,c.rate,c.min_amount,c.scope,"
        "c.scope_ids,c.start_time,c.end_time FROM coupon_receive cr "
        "JOIN coupons c ON c.id=cr.coupon_id "
        "WHERE cr.member_id=%s AND cr.status=1 AND c.status=1 AND c.start_time<=NOW() AND c.end_time>=NOW()",
        (member_id,),
    )
    return rows


def _coupon_vo(c: dict, eligible: bool, base: float) -> dict:
    amount = _coupon_discount(c, base) if eligible else 0.0
    return {
        "id": c["coupon_id"],
        "name": c["name"],
        "type": c["type"],
        "amount": float(c["amount"] or 0),
        "rate": float(c["rate"]) if c["rate"] is not None else None,
        "minAmount": float(c["min_amount"] or 0),
        "scope": c["scope"],
        "scopeIds": _parse_scope_ids(c["scope_ids"]),
        "startTime": c["start_time"],
        "endTime": c["end_time"],
        "usable": eligible,
        "discount": amount,
    }


async def _item_goods_rows(goods_ids: list[int]) -> dict:
    if not goods_ids:
        return {}
    ph = ",".join(["%s"] * len(goods_ids))
    rows = await database.fetch_all(
        f"SELECT id,category_id,buy_limit FROM goods WHERE id IN ({ph})", tuple(goods_ids)
    )
    return {r["id"]: r for r in rows}


async def _check_buy_limit(member_id: int, item_map: list[dict], goods_map: dict, cur) -> None:
    group: dict[int, int] = {}
    for it in item_map:
        group[it["goodsId"]] = group.get(it["goodsId"], 0) + it["quantity"]
    for goods_id, qty in group.items():
        g = goods_map.get(goods_id)
        if not g or not g["buy_limit"]:
            continue
        await cur.execute(
            "SELECT COALESCE(SUM(oi.quantity),0) AS total FROM order_items oi "
            "JOIN orders o ON o.id=oi.order_id WHERE o.member_id=%s AND oi.goods_id=%s "
            "AND o.order_status IN (1,2,3,4,6)",
            (member_id, goods_id),
        )
        rows = await cur.fetchall()
        bought = rows[0]["total"] if rows else 0
        if bought + qty > g["buy_limit"]:
            buy_limit()


def _calc_amounts(goods_items: list[dict], coupon: dict | None, points_used: int, member_points: int) -> dict:
    # 先逐项量化再求和，避免 float 累加误差（内置 round 还是 banker's rounding）
    total_amount = add_money(*[d(it["subtotal"]) for it in goods_items])
    freight_amount = ZERO
    coupon_amount = ZERO
    eligible, base = (True, total_amount)
    if coupon:
        eligible, base = _coupon_eligible(coupon, goods_items)
        if eligible:
            coupon_amount = d(_coupon_discount(coupon, base))
    points_amount = ZERO
    if points_used and points_used > 0 and member_points > 0:
        payable_before = q2(total_amount + freight_amount - coupon_amount)
        if gt(payable_before, 0):
            points_money = points_to_money(min(points_used, member_points))
            points_amount = min_money(points_money, payable_before)
    pay_amount = q2(total_amount + freight_amount - coupon_amount - points_amount)
    return {
        "totalAmount": _money(total_amount),
        "freightAmount": _money(freight_amount),
        "couponAmount": _money(coupon_amount),
        "pointsAmount": _money(points_amount),
        "payAmount": _money(pay_amount),
    }


def _new_preview_token(payload: dict) -> str:
    token = secrets.token_hex(8)
    payload["expires"] = time.time() + PREVIEW_TTL_SECONDS
    _preview_tokens[token] = payload
    if len(_preview_tokens) > 2000:
        now = time.time()
        for k in [k for k, v in _preview_tokens.items() if v["expires"] < now]:
            _preview_tokens.pop(k, None)
    return token


async def preview_order(member_id: int, body) -> dict:
    if body.type == "cart":
        cart_rows = await database.fetch_all(
            "SELECT id,goods_id,sku_id,quantity FROM member_cart WHERE member_id=%s AND selected=1 "
            "ORDER BY id ASC",
            (member_id,),
        )
        if body.cart_ids:
            id_set = set(body.cart_ids)
            cart_rows = [c for c in cart_rows if c["id"] in id_set]
            if len(cart_rows) != len(id_set):
                not_found("部分购物车商品不存在，请刷新后重试")
        if not cart_rows:
            bad_request("请先选择需要结算的商品")
        raw_items = [
            {"goodsId": c["goods_id"], "skuId": c["sku_id"], "quantity": c["quantity"], "cartId": c["id"]}
            for c in cart_rows
        ]
    else:
        if not body.items:
            bad_request("请选择商品规格")
        raw_items = [i.model_dump(by_alias=True) | {"cartId": None} for i in body.items]
    items = []
    for raw in raw_items:
        item = await _load_item(int(raw["skuId"]), int(raw["goodsId"]), int(raw["quantity"]))
        item["cartId"] = raw.get("cartId")
        items.append(item)
    member = await database.fetch_one(
        "SELECT points FROM members WHERE id=%s AND status=1", (member_id,)
    )
    if not member:
        state_error("账号状态异常")
    address_id = body.address_id
    if not address_id:
        default_addr = await database.fetch_one(
            "SELECT id FROM member_address WHERE member_id=%s ORDER BY is_default DESC,id DESC LIMIT 1",
            (member_id,),
        )
        address_id = default_addr["id"] if default_addr else None
    member_points = member["points"] or 0
    coupon_rows = await _member_usable_coupons(member_id)
    goods_rows = await _item_goods_rows([it["goodsId"] for it in items])
    for it in items:
        it["categoryId"] = goods_rows.get(it["goodsId"], {}).get("category_id")
    coupons = []
    chosen = None
    for c in coupon_rows:
        eligible, base = _coupon_eligible(c, items)
        vo = _coupon_vo(c, eligible, base)
        coupons.append(vo)
        if c["coupon_id"] == body.coupon_id and eligible:
            chosen = c
    if body.coupon_id and not chosen:
        coupon_unavailable("所选优惠券当前不可用，请重新选择")
    amounts = _calc_amounts(items, chosen, body.points_used, member_points)
    token = _new_preview_token({
        "mid": member_id,
        "kind": body.type,
        "items": [{"goodsId": it["goodsId"], "skuId": it["skuId"], "quantity": it["quantity"]} for it in items],
        "cartIds": [it["cartId"] for it in items if it.get("cartId")],
        "addressId": address_id,
        "couponId": body.coupon_id,
        "pointsUsed": body.points_used,
    })
    return {
        "previewToken": token,
        "items": [{
            "goodsId": it["goodsId"],
            "skuId": it["skuId"],
            "goodsName": it["goodsName"],
            "specText": it["specText"],
            "image": it["image"],
            "price": it["price"],
            "quantity": it["quantity"],
            "subtotal": it["subtotal"],
            "stock": it["skuStock"],
            "seckill": it["seckill"],
        } for it in items],
        "addressId": address_id,
        "memberPoints": member_points,
        "availableCoupons": coupons,
        "totalAmount": amounts["totalAmount"],
        "freightAmount": amounts["freightAmount"],
        "couponAmount": amounts["couponAmount"],
        "pointsAmount": amounts["pointsAmount"],
        "payAmount": amounts["payAmount"],
    }


async def submit_order(member_id: int, body) -> dict:
    snap = _preview_tokens.pop(body.preview_token, None)
    if not snap or snap.get("mid") != member_id or snap["expires"] < time.time():
        order_timeout("订单确认凭据已失效，请重新提交")
    if (
        (snap.get("addressId") or 0) != (body.address_id or 0)
        or (snap.get("couponId") or 0) != (body.coupon_id or 0)
        or (snap.get("pointsUsed") or 0) != (body.points_used or 0)
    ):
        state_error("订单信息已变化，请重新确认订单")
    addr = await get_address(member_id, body.address_id)
    if not addr:
        not_found("收货地址不存在，请重新选择")
    if body.pay_type not in (1, 2):
        bad_request("请选择支付方式")

    member = await database.fetch_one(
        "SELECT id,nickname,points FROM members WHERE id=%s AND status=1", (member_id,)
    )
    if not member:
        state_error("账号状态异常")
    items = []
    for it in snap["items"]:
        items.append(await _load_item(int(it["skuId"]), int(it["goodsId"]), int(it["quantity"])))
    goods_rows = await _item_goods_rows([it["goodsId"] for it in items])
    for it in items:
        it["categoryId"] = goods_rows.get(it["goodsId"], {}).get("category_id")
    coupon_rows = await _member_usable_coupons(member_id)
    chosen = None
    for c in coupon_rows:
        if c["coupon_id"] == body.coupon_id:
            chosen = c
            break
    if body.coupon_id and not chosen:
        coupon_unavailable("优惠券不可用，请重新下单")
    amounts = _calc_amounts(items, chosen, body.points_used, member["points"] or 0)
    coupon_discount = amounts["couponAmount"]
    if chosen and coupon_discount <= 0:
        coupon_unavailable("所选优惠券当前不可用，请重新下单")

    async with database.transaction() as cur:
        await _check_buy_limit(member_id, items, goods_rows, cur)
        for it in items:
            updated = await cur.execute(
                "UPDATE goods_sku SET stock=stock-%s,version=version+1 WHERE id=%s AND stock>=%s",
                (it["quantity"], it["skuId"], it["quantity"]),
            )
            if not updated:
                stock_not_enough(f"商品 {it['goodsName']} 库存不足")
            await cur.execute(
                "UPDATE goods SET stock=GREATEST(stock-%s,0) WHERE id=%s",
                (it["quantity"], it["goodsId"]),
            )
        receiver_address = " ".join(filter(None, [addr["province"], addr["city"], addr["district"], addr["detail"]]))
        order_no = _gen_no("O")
        await cur.execute(
            "INSERT INTO orders (order_no,member_id,total_amount,freight_amount,coupon_amount,points_amount,"
            "pay_amount,pay_type,pay_status,order_status,receiver_name,receiver_phone,receiver_address,"
            "buyer_message,order_source) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,0,1,%s,%s,%s,%s,'h5')",
            (order_no, member_id, amounts["totalAmount"], amounts["freightAmount"], amounts["couponAmount"],
             amounts["pointsAmount"], amounts["payAmount"], body.pay_type, addr["receiverName"],
             addr["receiverPhone"], receiver_address, body.buyer_message),
        )
        order_id = cur.lastrowid
        for it in items:
            await cur.execute(
                "INSERT INTO order_items (order_id,goods_id,sku_id,goods_name,goods_image,spec_value,price,"
                "quantity,subtotal) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (order_id, it["goodsId"], it["skuId"], it["goodsName"], it["image"], it["specText"],
                 it["price"], it["quantity"], it["subtotal"]),
            )
        await cur.execute(
            "INSERT INTO order_logs (order_id,operator_type,operator_id,operator_name,action,content) "
            "VALUES (%s,1,%s,%s,'下单','提交订单')",
            (order_id, member_id, member["nickname"] or ""),
        )
        if amounts["couponAmount"] > 0:
            used = await cur.execute(
                "UPDATE coupon_receive SET status=2,order_id=%s,used_at=NOW() "
                "WHERE member_id=%s AND coupon_id=%s AND status=1",
                (order_id, member_id, body.coupon_id),
            )
            if not used:
                # 券已被并发核销：不能带着折扣继续下单，抛错让事务回滚
                state_error("优惠券已被使用，请重新选择")
        if amounts["pointsAmount"] > 0:
            used_points = money_to_points(amounts["pointsAmount"])
            # 必须检查 rowcount：条件更新在积分不足时影响 0 行，此前却照常写入抵扣流水，
            # 等于积分没扣、账本记了负账（TOCTOU + 不校验结果）。
            deducted = await cur.execute(
                "UPDATE members SET points=points-%s WHERE id=%s AND points>=%s",
                (used_points, member_id, used_points),
            )
            if not deducted:
                state_error("积分不足，请重新下单")
            await cur.execute(
                "INSERT INTO points_logs (member_id,change_value,reason,type,related_id) "
                "VALUES (%s,%s,%s,2,%s)",
                (member_id, -used_points, f"订单抵扣 {order_no}", order_id),
            )
        if snap["cartIds"]:
            ph = ",".join(["%s"] * len(snap["cartIds"]))
            await cur.execute(
                f"DELETE FROM member_cart WHERE member_id=%s AND id IN ({ph})",
                [member_id] + snap["cartIds"],
            )
        await cur.execute(
            "INSERT INTO member_logs (member_id,action_type,action) VALUES (%s,'order',%s)",
            (member_id, f"提交订单 {order_no}"),
        )
    return {"id": order_id, "orderNo": order_no}


def _order_card(o: dict) -> dict:
    return {
        "id": o["id"],
        "orderNo": o["order_no"],
        "orderStatus": o["order_status"],
        "orderStatusText": ORDER_STATUS_TEXT.get(o["order_status"], ""),
        "payStatus": o["pay_status"],
        "payStatusText": PAY_STATUS_TEXT.get(o["pay_status"], ""),
        "totalAmount": _money(o["total_amount"]),
        "freightAmount": _money(o["freight_amount"]),
        "couponAmount": _money(o["coupon_amount"]),
        "pointsAmount": _money(o["points_amount"]),
        "payAmount": _money(o["pay_amount"]),
        "payType": o["pay_type"],
        "goodsCount": o["goods_count"],
        "totalQuantity": o["total_quantity"],
        "goodsName": o["goods_name"] or "",
        "goodsImage": o["goods_image"] or "",
        "createdAt": o["created_at"],
        "actions": _ACTIONS.get(o["order_status"], []),
    }


async def list_orders(member_id: int, page: int, page_size: int, order_status: int | None = None,
                      keyword: str = "") -> dict:
    counts_rows = await database.fetch_all(
        "SELECT order_status AS s, COUNT(*) AS c FROM orders WHERE member_id=%s GROUP BY order_status",
        (member_id,),
    )
    counts = {str(i): 0 for i in range(1, 7)}
    total_count = 0
    for r in counts_rows:
        counts[str(r["s"])] = r["c"]
        total_count += r["c"]
    counts["all"] = total_count
    where = ["member_id=%s"]
    params: list = [member_id]
    if order_status not in (None, ""):
        where.append("order_status=%s")
        params.append(int(order_status))
    if keyword:
        where.append("order_no LIKE %s")
        params.append(f"%{keyword}%")
    total = await database.fetch_one(
        f"SELECT COUNT(*) AS c FROM orders WHERE {' AND '.join(where)}", params
    )
    rows = await database.fetch_all(
        f"SELECT o.id,o.order_no,o.member_id,o.total_amount,o.freight_amount,o.coupon_amount,o.points_amount,"
        f"o.pay_amount,o.pay_type,o.pay_status,o.order_status,o.created_at,"
        f"(SELECT oi.goods_name FROM order_items oi WHERE oi.order_id=o.id ORDER BY oi.id LIMIT 1) AS goods_name,"
        f"(SELECT oi.goods_image FROM order_items oi WHERE oi.order_id=o.id ORDER BY oi.id LIMIT 1) AS goods_image,"
        f"(SELECT COUNT(*) FROM order_items oi WHERE oi.order_id=o.id) AS goods_count,"
        f"(SELECT SUM(oi.quantity) FROM order_items oi WHERE oi.order_id=o.id) AS total_quantity "
        f"FROM orders o WHERE {' AND '.join(where)} ORDER BY o.id DESC LIMIT %s OFFSET %s",
        params + [page_size, (page - 1) * page_size],
    )
    return {
        "list": [_order_card(o) for o in rows],
        "total": total["c"],
        "orderStatusCounts": counts,
        "page": page,
        "page_size": page_size,
    }


async def _find_order(member_id: int, order_key: int | str) -> dict:
    row = None
    if isinstance(order_key, int) or str(order_key).isdigit():
        row = await database.fetch_one(
            "SELECT * FROM orders WHERE id=%s AND member_id=%s", (int(order_key), member_id)
        )
    if not row:
        row = await database.fetch_one(
            "SELECT * FROM orders WHERE order_no=%s AND member_id=%s", (str(order_key), member_id)
        )
    if not row:
        not_found("订单不存在")
    return row


async def order_detail(member_id: int, order_id: int | str) -> dict:
    row = await _find_order(member_id, order_id)
    await _maybe_expire_order(row)
    row = await _find_order(member_id, order_id)
    items = await database.fetch_all(
        "SELECT goods_id,sku_id,goods_name,goods_image,spec_value,price,quantity,subtotal "
        "FROM order_items WHERE order_id=%s ORDER BY id ASC",
        (row["id"],),
    )
    logs = await database.fetch_all(
        "SELECT action,content,created_at FROM order_logs WHERE order_id=%s ORDER BY id ASC",
        (row["id"],),
    )
    as_rows = await database.fetch_all(
        "SELECT id,after_sale_no,type,reason,amount,status,handle_note,return_logistics_company,"
        "return_logistics_no,handle_time,created_at FROM after_sales WHERE order_id=%s ORDER BY id DESC LIMIT 1",
        (row["id"],),
    )
    card = _order_card(row | {
        "goods_count": len(items),
        "total_quantity": sum(it["quantity"] for it in items),
        "goods_name": items[0]["goods_name"] if items else "",
        "goods_image": items[0]["goods_image"] if items else "",
    })
    return {
        **card,
        "receiverName": row["receiver_name"],
        "receiverPhone": row["receiver_phone"],
        "receiverAddress": row["receiver_address"],
        "payStatusText": PAY_STATUS_TEXT.get(row["pay_status"], ""),
        "payTypeText": PAY_TYPE_TEXT.get(row["pay_type"] or 0, ""),
        "logisticsCompany": row["logistics_company"] or "",
        "logisticsNo": row["logistics_no"] or "",
        "shippedAt": row["shipped_at"],
        "paidAt": row["paid_at"],
        "createdAt": row["created_at"],
        "buyerMessage": row["buyer_message"] or "",
        "items": [
            {
                "id": it["id"] if False else i + 1,
                "goodsId": it["goods_id"],
                "skuId": it["sku_id"],
                "goodsName": it["goods_name"],
                "goodsImage": it["goods_image"] or "",
                "specValue": it["spec_value"] or "",
                "price": _money(it["price"]),
                "quantity": it["quantity"],
                "subtotal": _money(it["subtotal"]),
            }
            for i, it in enumerate(items)
        ],
        "afterSales": [
            {
                "id": a["id"],
                "afterSaleNo": a["after_sale_no"],
                "type": a["type"],
                "reason": a["reason"] or "",
                "amount": _money(a["amount"]),
                "status": a["status"],
                "handleNote": a["handle_note"] or "",
                "returnLogisticsCompany": a["return_logistics_company"] or "",
                "returnLogisticsNo": a["return_logistics_no"] or "",
                "createdAt": a["created_at"],
            }
            for a in as_rows
        ],
        "logistics": [
            {"action": l["action"], "content": l["content"] or "", "createdAt": l["created_at"]} for l in logs
        ],
    }


async def _cancel_inside(cur, row: dict, log_note: str, operator_name: str = "") -> None:
    await cur.execute(
        "SELECT goods_id,sku_id,quantity FROM order_items WHERE order_id=%s", (row["id"],)
    )
    items = await cur.fetchall()
    for it in items:
        if it["sku_id"]:
            await cur.execute(
                "UPDATE goods_sku SET stock=stock+%s,version=version+1 WHERE id=%s",
                (it["quantity"], it["sku_id"]),
            )
        await cur.execute(
            "UPDATE goods SET stock=stock+%s WHERE id=%s", (it["quantity"], it["goods_id"])
        )
    # 状态机必须在这里收口：只有真正把 1→5 更新成功才允许退回库存/券/积分。
    # 此前不检查 rowcount，同一订单重复触发取消会重复返还积分，可被用来凭空刷积分。
    canceled = await cur.execute(
        "UPDATE orders SET order_status=5,canceled_at=NOW() WHERE id=%s AND order_status=1", (row["id"],)
    )
    if not canceled:
        state_error("订单状态已变化，无法重复取消")
    if gt(row["coupon_amount"], 0):
        await cur.execute(
            "UPDATE coupon_receive SET status=1,order_id=NULL,used_at=NULL WHERE order_id=%s AND status=2",
            (row["id"],),
        )
    if gt(row["points_amount"], 0):
        used_points = money_to_points(row["points_amount"])
        await cur.execute(
            "UPDATE members SET points=points+%s WHERE id=%s", (used_points, row["member_id"])
        )
        await cur.execute(
            "INSERT INTO points_logs (member_id,change_value,reason,type,related_id) "
            "VALUES (%s,%s,%s,1,%s)",
            (row["member_id"], used_points, log_note, row["id"]),
        )
    await cur.execute(
        "INSERT INTO order_logs (order_id,operator_type,operator_id,operator_name,action,content) "
        "VALUES (%s,1,%s,%s,'取消订单',%s)",
        (row["id"], row["member_id"], operator_name, log_note),
    )


async def _is_expired_row(row: dict) -> bool:
    expired = await database.fetch_one(
        "SELECT (created_at < TIMESTAMPADD(MINUTE,-%s,NOW())) AS expired FROM orders WHERE id=%s",
        (config.order_pay_timeout_minutes, row["id"]),
    )
    return bool(expired and expired["expired"])


async def _maybe_expire_order(row: dict) -> None:
    if row["order_status"] != 1 or row["pay_status"] != 0:
        return
    if not await _is_expired_row(row):
        return
    async with database.transaction() as cur:
        await cur.execute(
            "SELECT * FROM orders WHERE id=%s AND order_status=1 FOR UPDATE", (row["id"],)
        )
        cur_row = await cur.fetchone()
        if not cur_row:
            return
        await _cancel_inside(cur, cur_row, f"订单超时未支付，系统自动取消（{row['order_no']}）", "系统")


async def cancel_order(member_id: int, order_id: int | str) -> None:
    row = await _find_order(member_id, order_id)
    if row["order_status"] != 1:
        state_error("当前订单状态不可取消")
    if row["pay_status"] != 0:
        state_error("已支付订单不可取消")
    member = await database.fetch_one(
        "SELECT nickname FROM members WHERE id=%s", (member_id,)
    )
    async with database.transaction() as cur:
        await cur.execute(
            "SELECT * FROM orders WHERE id=%s AND order_status=1 AND pay_status=0 FOR UPDATE",
            (row["id"],),
        )
        cur_row = await cur.fetchone()
        if not cur_row:
            state_error("订单状态已变化，请刷新后重试")
        await _cancel_inside(cur, cur_row, f"用户取消未付款订单（{row['order_no']}）", member["nickname"] or "")


async def pay_order(member_id: int, order_id: int | str, pay_type: int | None = None) -> dict:
    row = await _find_order(member_id, order_id)
    if pay_type and row["pay_type"] != pay_type:
        bad_request("支付方式与订单不一致，请重新选择")
    if row["order_status"] != 1:
        state_error("当前订单状态不可支付")
    if row["pay_status"] == 1:
        state_error("订单已支付，请勿重复支付")
    if await _is_expired_row(row):
        await _maybe_expire_order(row)
        order_timeout("订单已超时取消，请重新下单")
    member = await database.fetch_one(
        "SELECT id,nickname FROM members WHERE id=%s", (member_id,)
    )
    async with database.transaction() as cur:
        await cur.execute(
            "SELECT * FROM orders WHERE id=%s AND pay_status=0 AND order_status=1 FOR UPDATE",
            (row["id"],),
        )
        cur_row = await cur.fetchone()
        if not cur_row:
            state_error("订单状态已变化，请刷新后重试")
        await cur.execute(
            "UPDATE orders SET pay_status=1,order_status=2,paid_at=NOW() WHERE id=%s", (row["id"],)
        )
        await cur.execute(
            "SELECT goods_id,quantity FROM order_items WHERE order_id=%s", (row["id"],)
        )
        items = await cur.fetchall()
        for it in items:
            await cur.execute(
                "UPDATE goods SET sales=sales+%s WHERE id=%s", (it["quantity"], it["goods_id"])
            )
        await cur.execute(
            "INSERT INTO order_logs (order_id,operator_type,operator_id,operator_name,action,content) "
            "VALUES (%s,1,%s,%s,'支付成功','模拟支付成功')",
            (row["id"], member_id, member["nickname"] or ""),
        )
        await cur.execute(
            "INSERT INTO member_logs (member_id,action_type,action) VALUES (%s,'pay',%s)",
            (member_id, f"支付订单 {row['order_no']}"),
        )
    return {
        "orderId": row["id"],
        "orderNo": row["order_no"],
        "payAmount": _money(row["pay_amount"]),
    }


async def pay_status(member_id: int, order_id: int | str) -> dict:
    row = await _find_order(member_id, order_id)
    await _maybe_expire_order(row)
    row = await _find_order(member_id, order_id)
    return {
        "orderId": row["id"],
        "orderNo": row["order_no"],
        "payStatus": row["pay_status"],
        "orderStatus": row["order_status"],
        "orderStatusText": ORDER_STATUS_TEXT.get(row["order_status"], ""),
    }


async def confirm_order(member_id: int, order_id: int | str) -> None:
    row = await _find_order(member_id, order_id)
    if row["order_status"] != 3:
        state_error("当前订单状态不可确认收货")
    member = await database.fetch_one(
        "SELECT id,nickname FROM members WHERE id=%s", (member_id,)
    )
    async with database.transaction() as cur:
        updated = await cur.execute(
            "UPDATE orders SET order_status=4,completed_at=NOW() WHERE id=%s AND order_status=3",
            (row["id"],),
        )
        if not updated:
            state_error("订单状态已变化，请刷新后重试")
        await cur.execute(
            "INSERT INTO order_logs (order_id,operator_type,operator_id,operator_name,action,content) "
            "VALUES (%s,1,%s,%s,'确认收货','订单已完成')",
            (row["id"], member_id, member["nickname"] or ""),
        )


async def buy_again(member_id: int, order_id: int | str) -> dict:
    row = await _find_order(member_id, order_id)
    items = await database.fetch_all(
        "SELECT goods_id,sku_id,quantity FROM order_items WHERE order_id=%s ORDER BY id ASC",
        (row["id"],),
    )
    added = 0
    for it in items:
        sku = await get_sku(it["sku_id"])
        if not sku or sku["goods_id"] != it["goods_id"] or sku["goods_status"] != 1 or sku["sku_status"] != 1:
            continue
        if (sku["sku_stock"] or 0) <= 0:
            continue
        qty = min(it["quantity"], sku["sku_stock"])
        existing = await database.fetch_one(
            "SELECT * FROM member_cart WHERE member_id=%s AND sku_id=%s", (member_id, it["sku_id"])
        )
        if existing:
            new_qty = min(existing["quantity"] + qty, sku["sku_stock"])
            await database.execute(
                "UPDATE member_cart SET quantity=%s WHERE id=%s", (new_qty, existing["id"])
            )
        else:
            await database.execute_return_id(
                "INSERT INTO member_cart (member_id,goods_id,sku_id,quantity,selected) VALUES (%s,%s,%s,%s,1)",
                (member_id, it["goods_id"], it["sku_id"], qty),
            )
        added += 1
    return {"added": added, "skipped": len(items) - added}


async def logistics_info(member_id: int, order_id: int | str) -> dict:
    row = await _find_order(member_id, order_id)
    if row["order_status"] not in (3, 4):
        state_error("订单尚未发货，暂无物流信息")
    return {
        "logisticsCompany": row["logistics_company"] or "",
        "logisticsNo": row["logistics_no"] or "",
        "shippedAt": row["shipped_at"],
    }
