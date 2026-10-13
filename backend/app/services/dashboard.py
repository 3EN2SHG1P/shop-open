from datetime import timedelta

from core.timezone import now

from core import database
from core.money import f2 as _money

ORDER_STATUS_TEXT = {1: "待付款", 2: "待发货", 3: "已发货", 4: "已完成", 5: "已取消", 6: "售后中"}
STATUS_COLORS = {1: "warning", 2: "primary", 3: "info", 4: "success", 5: "secondary", 6: "danger"}
PAY_STATUS_TEXT = {0: "未支付", 1: "已支付"}


async def overview(days: int = 1) -> dict:
    if days not in (7, 30):
        days = 1
    start = f"(CURDATE() - INTERVAL {days - 1} DAY)"
    stats = {}
    stats["orders"] = (await database.fetch_one(
        f"SELECT COUNT(*) AS c FROM orders WHERE DATE(created_at)>= {start}"
    ))["c"]
    stats["gmv"] = _money((await database.fetch_one(
        f"SELECT COALESCE(SUM(pay_amount),0) AS s FROM orders WHERE pay_status=1 AND DATE(paid_at)>= {start}"
    ))["s"])
    stats["newMembers"] = (await database.fetch_one(
        f"SELECT COUNT(*) AS c FROM members WHERE DATE(registered_at)>= {start}"
    ))["c"]
    stats["totalGoods"] = (await database.fetch_one(
        "SELECT COUNT(*) AS c FROM goods WHERE status=1"
    ))["c"]
    stats["totalMembers"] = (await database.fetch_one(
        "SELECT COUNT(*) AS c FROM members"
    ))["c"]
    stats["pendingPayment"] = (await database.fetch_one(
        "SELECT COUNT(*) AS c FROM orders WHERE order_status=1"
    ))["c"]
    stats["pendingShip"] = (await database.fetch_one(
        "SELECT COUNT(*) AS c FROM orders WHERE order_status=2"
    ))["c"]
    stats["lowStock"] = (await database.fetch_one(
        "SELECT COUNT(*) AS c FROM goods WHERE status=1 AND warn_stock>0 AND stock<=warn_stock"
    ))["c"]

    dist_rows = await database.fetch_all(
        "SELECT order_status AS s,COUNT(*) AS c FROM orders GROUP BY order_status"
    )
    status_count = {i: 0 for i in range(1, 7)}
    for r in dist_rows:
        if r["s"] in status_count:
            status_count[r["s"]] = r["c"]
    total = sum(status_count.values())
    status_dist = [
        {
            "status": s,
            "statusText": ORDER_STATUS_TEXT[s],
            "count": status_count[s],
            "percent": round(status_count[s] * 100 / total, 1) if total else 0.0,
            "color": STATUS_COLORS[s],
        }
        for s in range(1, 7)
    ]

    recent = await database.fetch_all(
        "SELECT o.id,o.order_no,o.pay_amount,o.order_status,m.nickname AS member_name,o.created_at "
        "FROM orders o LEFT JOIN members m ON m.id=o.member_id "
        "ORDER BY o.id DESC LIMIT 6"
    )
    recent_orders = [
        {
            "orderNo": r["order_no"],
            "memberName": r["member_name"] or f"会员#{r['id']}",
            "payAmount": _money(r["pay_amount"]),
            "orderStatus": r["order_status"],
            "orderStatusText": ORDER_STATUS_TEXT.get(r["order_status"], ""),
        }
        for r in recent
    ]
    return {"stats": stats, "statusDist": status_dist, "recentOrders": recent_orders}


async def trend(days: int) -> list[dict]:
    if days not in (7, 30):
        days = 7
    start = now() - timedelta(days=days - 1)
    start_date = start.strftime("%Y-%m-%d")
    rows = await database.fetch_all(
        "SELECT DATE(paid_at) AS d,COUNT(*) AS c,COALESCE(SUM(pay_amount),0) AS s "
        "FROM orders WHERE pay_status=1 AND DATE(paid_at)>=%s GROUP BY DATE(paid_at) ORDER BY d ASC",
        (start_date,),
    )
    day_map = {}
    for r in rows:
        day_map[str(r["d"])] = (r["c"], _money(r["s"]))
    result = []
    for i in range(days):
        day = (start + timedelta(days=i)).strftime("%Y-%m-%d")
        c, s = day_map.get(day, (0, 0.0))
        result.append({"date": day, "day": day[5:], "amount": s, "orders": c})
    return result


async def hot_goods(days: int) -> list[dict]:
    if days not in (7, 30, 90):
        days = 30
    rows = await database.fetch_all(
        "SELECT g.name AS goods_name,SUM(oi.quantity) AS sales,COALESCE(SUM(oi.subtotal),0) AS s "
        "FROM order_items oi JOIN orders o ON o.id=oi.order_id INNER JOIN goods g ON g.id=oi.goods_id "
        "WHERE o.pay_status=1 AND o.order_status IN (3,4) AND DATE(o.paid_at)>=DATE_SUB(CURDATE(),INTERVAL %s DAY) "
        "GROUP BY oi.goods_id,g.name ORDER BY sales DESC, s DESC LIMIT 10",
        (days,),
    )
    return [
        {
            "rank": i + 1,
            "goodsName": r["goods_name"],
            "sales": r["sales"] or 0,
            "amount": _money(r["s"]),
        }
        for i, r in enumerate(rows)
    ]
