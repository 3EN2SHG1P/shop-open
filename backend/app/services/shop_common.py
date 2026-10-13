from core import database


async def get_sku(sku_id: int) -> dict | None:
    row = await database.fetch_one(
        "SELECT s.id AS sku_id,s.goods_id,s.sku_code,s.price AS sku_price,s.stock AS sku_stock,"
        "s.status AS sku_status,g.name AS goods_name,g.status AS goods_status,g.stock AS goods_stock "
        "FROM goods_sku s JOIN goods g ON g.id=s.goods_id WHERE s.id=%s",
        (sku_id,),
    )
    return row


async def get_sku_spec_text(sku_id: int) -> str:
    rows = await database.fetch_all(
        "SELECT sv.value FROM goods_sku_spec_values gsv "
        "JOIN specification_values sv ON sv.id=gsv.spec_value_id "
        "JOIN specifications s ON s.id=sv.spec_id "
        "WHERE gsv.sku_id=%s ORDER BY s.sort ASC,s.id ASC,sv.id ASC",
        (sku_id,),
    )
    return " ".join(r["value"] for r in rows)


async def get_goods_image(goods_id: int) -> str:
    row = await database.fetch_one(
        "SELECT url FROM goods_images WHERE goods_id=%s AND type=1 ORDER BY sort ASC,id ASC LIMIT 1",
        (goods_id,),
    )
    return row["url"] if row else ""
