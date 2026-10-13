from core import database
from core.errors import not_found, stock_not_enough
from core.money import f2 as _money, add_money, mul_money
from services.shop_common import get_goods_image, get_sku, get_sku_spec_text


async def _cart_rows(member_id: int) -> list[dict]:
    rows = await database.fetch_all(
        "SELECT c.id,c.goods_id,c.sku_id,c.quantity,c.selected,g.name AS goods_name,"
        "s.price AS sku_price,s.stock AS sku_stock,g.status AS goods_status,s.status AS sku_status "
        "FROM member_cart c JOIN goods g ON g.id=c.goods_id JOIN goods_sku s ON s.id=c.sku_id "
        "WHERE c.member_id=%s ORDER BY c.id DESC",
        (member_id,),
    )
    if not rows:
        return []
    sku_ids = [r["sku_id"] for r in rows]
    placeholders = ",".join(["%s"] * len(sku_ids))
    specs = await database.fetch_all(
        f"SELECT gsv.sku_id,sv.value FROM goods_sku_spec_values gsv "
        f"JOIN specification_values sv ON sv.id=gsv.spec_value_id "
        f"JOIN specifications s ON s.id=sv.spec_id WHERE gsv.sku_id IN ({placeholders}) "
        f"ORDER BY s.sort ASC,s.id ASC,sv.id ASC",
        tuple(sku_ids),
    )
    spec_texts: dict[int, list[str]] = {}
    for sp in specs:
        spec_texts.setdefault(sp["sku_id"], []).append(sp["value"])
    images = await database.fetch_all(
        "SELECT goods_id,url FROM goods_images WHERE goods_id IN (SELECT DISTINCT goods_id FROM member_cart WHERE member_id=%s) AND type=1",
        (member_id,),
    )
    image_map = {im["goods_id"]: im["url"] for im in images}
    result = []
    for r in rows:
        result.append({
            "id": r["id"],
            "goodsId": r["goods_id"],
            "skuId": r["sku_id"],
            "goodsName": r["goods_name"],
            "specText": " ".join(spec_texts.get(r["sku_id"], [])),
            "price": _money(r["sku_price"]),
            "image": image_map.get(r["goods_id"], ""),
            "quantity": r["quantity"],
            "stock": r["sku_stock"] or 0,
            "selected": r["selected"],
        })
    return result


async def cart_list(member_id: int) -> dict:
    rows = await _cart_rows(member_id)
    total_amount = _money(
        add_money(*[mul_money(r["price"], r["quantity"]) for r in rows if r["selected"]])
    )
    return {
        "list": rows,
        "totalCount": sum(r["quantity"] for r in rows),
        "selectedCount": sum(r["quantity"] for r in rows if r["selected"]),
        "totalAmount": total_amount,
    }


async def add_cart(member_id: int, goods_id: int, sku_id: int, quantity: int) -> None:
    if quantity < 1:
        stock_not_enough("数量必须大于 0")
    await _check_sku(goods_id, sku_id)
    row = await database.fetch_one(
        "SELECT * FROM member_cart WHERE member_id=%s AND sku_id=%s", (member_id, sku_id)
    )
    if row:
        new_qty = row["quantity"] + quantity
        sku = await get_sku(sku_id)
        if sku and new_qty > (sku["sku_stock"] or 0):
            stock_not_enough("加入数量超出库存")
        await database.execute(
            "UPDATE member_cart SET quantity=%s WHERE id=%s", (new_qty, row["id"])
        )
        return
    sku = await get_sku(sku_id)
    if sku and quantity > (sku["sku_stock"] or 0):
        stock_not_enough("加入数量超出库存")
    await database.execute_return_id(
        "INSERT INTO member_cart (member_id,goods_id,sku_id,quantity,selected) VALUES (%s,%s,%s,%s,1)",
        (member_id, goods_id, sku_id, quantity),
    )


async def update_quantity(member_id: int, cart_id: int, quantity: int) -> None:
    if quantity < 1:
        not_found("数量必须大于 0")
    row = await database.fetch_one(
        "SELECT * FROM member_cart WHERE id=%s AND member_id=%s", (cart_id, member_id)
    )
    if not row:
        not_found("购物车项不存在")
    sku = await get_sku(row["sku_id"])
    if sku and quantity > (sku["sku_stock"] or 0):
        stock_not_enough("数量超出库存")
    await database.execute(
        "UPDATE member_cart SET quantity=%s WHERE id=%s", (quantity, cart_id)
    )


async def update_selected(member_id: int, ids: list[int], selected: bool) -> None:
    value = 1 if selected else 0
    if ids:
        placeholders = ",".join(["%s"] * len(ids))
        await database.execute(
            f"UPDATE member_cart SET selected=%s WHERE member_id=%s AND id IN ({placeholders})",
            [value, member_id] + ids,
        )
    else:
        await database.execute(
            "UPDATE member_cart SET selected=%s WHERE member_id=%s", (value, member_id)
        )


async def delete_cart(member_id: int, cart_id: int) -> None:
    row = await database.fetch_one(
        "SELECT id FROM member_cart WHERE id=%s AND member_id=%s", (cart_id, member_id)
    )
    if not row:
        not_found("购物车项不存在")
    await database.execute("DELETE FROM member_cart WHERE id=%s", (cart_id,))


async def clear_cart(member_id: int) -> None:
    await database.execute("DELETE FROM member_cart WHERE member_id=%s", (member_id,))


async def merge_cart(member_id: int, items: list[dict]) -> None:
    for item in items:
        goods_id = int(item["goodsId"])
        sku_id = int(item["skuId"])
        quantity = max(int(item.get("quantity") or 1), 1)
        selected = 1 if item.get("selected") in (None, "", 1, "1", True) else 0
        sku = await get_sku(sku_id)
        if not sku or sku["sku_id"] != sku_id or sku["goods_id"] != goods_id:
            continue
        if sku["goods_status"] != 1 or sku["sku_status"] != 1:
            continue
        stock = sku["sku_stock"] or 0
        if stock <= 0:
            continue
        row = await database.fetch_one(
            "SELECT * FROM member_cart WHERE member_id=%s AND sku_id=%s", (member_id, sku_id)
        )
        if row:
            new_qty = min(row["quantity"] + quantity, stock)
            await database.execute(
                "UPDATE member_cart SET quantity=%s,selected=%s WHERE id=%s",
                (new_qty, selected, row["id"]),
            )
        else:
            await database.execute_return_id(
                "INSERT INTO member_cart (member_id,goods_id,sku_id,quantity,selected) "
                "VALUES (%s,%s,%s,%s,%s)",
                (member_id, goods_id, sku_id, min(quantity, stock), selected),
            )


async def clear_selected(member_id: int, cart_ids: list[int]) -> None:
    if not cart_ids:
        return
    placeholders = ",".join(["%s"] * len(cart_ids))
    await database.execute(
        f"DELETE FROM member_cart WHERE member_id=%s AND id IN ({placeholders})",
        [member_id] + cart_ids,
    )


async def _check_sku(goods_id: int, sku_id: int) -> dict:
    sku = await get_sku(sku_id)
    if not sku or sku["goods_id"] != goods_id:
        not_found("商品规格不存在")
    if sku["goods_status"] != 1 or sku["sku_status"] != 1:
        not_found("商品已下架")
    return sku
