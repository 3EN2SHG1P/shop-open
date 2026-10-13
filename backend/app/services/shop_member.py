from core import database
from core.errors import not_found
from services.shop_order import POINTS_RATIO

POINTS_TYPE_TEXT = {1: "获得", 2: "支出", 3: "兑换支出"}


async def points_summary(member_id: int) -> dict:
    row = await database.fetch_one(
        "SELECT m.id,m.points,m.total_consume,m.level_id,"
        "l.level_name,l.discount_rate,l.benefits "
        "FROM members m LEFT JOIN member_level l ON l.id=m.level_id WHERE m.id=%s AND m.status=1",
        (member_id,),
    )
    if not row:
        not_found("会员不存在")
    return {
        "points": row["points"] or 0,
        "levelId": row["level_id"] or 0,
        "levelName": row["level_name"] or "普通会员",
        "levelDiscountRate": float(row["discount_rate"] or 10.00),
        "totalConsume": float(row["total_consume"] or 0),
        "exchangeRatio": POINTS_RATIO,
        "ruleText": f"{POINTS_RATIO} 积分抵 1 元，下单时可抵扣现金，抵扣后积分为负不可再抵",
    }


async def points_logs(member_id: int, page: int, page_size: int) -> dict:
    total = await database.fetch_one(
        "SELECT COUNT(*) AS c FROM points_logs WHERE member_id=%s", (member_id,)
    )
    rows = await database.fetch_all(
        "SELECT id,change_value,reason,type,related_id,created_at FROM points_logs "
        "WHERE member_id=%s ORDER BY id DESC LIMIT %s OFFSET %s",
        (member_id, page_size, (page - 1) * page_size),
    )
    return {
        "list": [
            {
                "id": r["id"],
                "changeValue": r["change_value"],
                "income": r["change_value"] > 0,
                "type": r["type"],
                "typeText": POINTS_TYPE_TEXT.get(r["type"], "获得" if r["change_value"] > 0 else "支出"),
                "reason": r["reason"],
                "relatedId": r["related_id"],
                "createdAt": r["created_at"],
            }
            for r in rows
        ],
        "total": total["c"],
        "page": page,
        "page_size": page_size,
    }
