from core import database
from core.errors import bad_request, not_found, state_error
from core.money import f2 as _money
from core.response import page_data

IMAGE_SUBQUERY = (
    "(SELECT gi.url FROM goods_images gi WHERE gi.goods_id=g.id AND gi.type=1 "
    "ORDER BY gi.sort ASC, gi.id ASC LIMIT 1) AS image"
)

GOODS_LIST_SELECT = (
    f"SELECT g.id,g.name,g.subtitle,g.price,g.market_price,g.stock,g.sales,"
    f"g.is_recommend,g.is_hot,g.is_new,{IMAGE_SUBQUERY} FROM goods g"
)


def _goods_item(r: dict) -> dict:
    return {
        "id": r["id"],
        "name": r["name"],
        "subtitle": r["subtitle"] or "",
        "price": float(r["price"] or 0),
        "marketPrice": float(r["market_price"] or 0),
        "stock": r["stock"] or 0,
        "sales": r["sales"] or 0,
        "image": r["image"] or "",
        "isHot": r["is_hot"],
        "isNew": r["is_new"],
        "isRecommend": r["is_recommend"],
    }


async def _ads(position_id: int | None = None, limit: int = 50) -> list[dict]:
    where = ["a.status=1", "(a.start_time IS NULL OR a.start_time<=NOW())", "(a.end_time IS NULL OR a.end_time>=NOW())"]
    params: list = []
    if position_id:
        where.append("a.position_id=%s")
        params.append(position_id)
    rows = await database.fetch_all(
        f"SELECT a.id,a.image,a.video,a.link,a.text,a.sort,p.name AS position_name "
        f"FROM ads a LEFT JOIN ad_positions p ON p.id=a.position_id "
        f"WHERE {' AND '.join(where)} ORDER BY a.sort ASC,a.id ASC LIMIT {int(limit)}",
        params,
    )
    return [
        {"id": r["id"], "image": r["image"] or "", "video": r["video"] or "", "link": r["link"] or "",
         "text": r["text"] or ""}
        for r in rows
    ]


async def home() -> dict:
    banners = await _ads(limit=10)
    cat_rows = await database.fetch_all(
        "SELECT id,name,icon FROM goods_category WHERE is_show=1 ORDER BY sort ASC,id ASC"
    )
    recommend = await database.fetch_all(
        f"{GOODS_LIST_SELECT} WHERE g.status=1 AND g.is_recommend=1 ORDER BY g.id DESC LIMIT 8"
    )
    hot = await database.fetch_all(
        f"{GOODS_LIST_SELECT} WHERE g.status=1 AND g.is_hot=1 ORDER BY g.sales DESC,g.id DESC LIMIT 8"
    )
    new_arrival = await database.fetch_all(
        f"{GOODS_LIST_SELECT} WHERE g.status=1 AND g.is_new=1 ORDER BY g.created_at DESC,g.id DESC LIMIT 8"
    )
    notices = await database.fetch_all(
        "SELECT id,title,publish_time FROM notices WHERE status=1 AND "
        "(publish_time IS NULL OR publish_time<=NOW()) ORDER BY publish_time DESC,id DESC LIMIT 5"
    )
    categories = [
        {"id": c["id"], "name": c["name"], "icon": c["icon"] or ""} for c in cat_rows
    ]
    return {
        "banners": banners,
        "categories": categories,
        "recommend": [_goods_item(r) for r in recommend],
        "hot": [_goods_item(r) for r in hot],
        "newArrival": [_goods_item(r) for r in new_arrival],
        "notices": [
            {"id": n["id"], "title": n["title"], "publishTime": n["publish_time"]} for n in notices
        ],
    }


async def list_notices() -> dict:
    rows = await database.fetch_all(
        "SELECT id,title,content,publish_time FROM notices WHERE status=1 AND "
        "(publish_time IS NULL OR publish_time<=NOW()) ORDER BY publish_time DESC,id DESC"
    )
    return {"list": [
        {"id": r["id"], "title": r["title"], "content": r["content"] or "",
         "publishTime": r["publish_time"]} for r in rows
    ]}


async def list_ads(position_id: int | None = None) -> dict:
    return {"list": await _ads(position_id)}


async def _category_subtree_ids(category_id: int) -> list[int]:
    if not category_id:
        return []
    rows = await database.fetch_all("SELECT id,parent_id FROM goods_category")
    children: dict[int, list[int]] = {}
    for r in rows:
        children.setdefault(r["parent_id"], []).append(r["id"])
    ids = [category_id]
    queue = [category_id]
    while queue:
        nxt = []
        for pid in queue:
            for cid in children.get(pid, []):
                ids.append(cid)
                nxt.append(cid)
        queue = nxt
    return ids


async def list_goods(page: int, page_size: int, filters: dict) -> dict:
    where = ["g.status=1"]
    params: list = []
    if filters.get("keyword"):
        where.append("(g.name LIKE %s OR g.subtitle LIKE %s)")
        params += [f"%{filters['keyword']}%", f"%{filters['keyword']}%"]
    if filters.get("category_id"):
        ids = await _category_subtree_ids(int(filters["category_id"]))
        if not ids:
            return page_data([], 0, page, page_size)
        placeholders = ",".join(["%s"] * len(ids))
        where.append(f"g.category_id IN ({placeholders})")
        params += ids
    if filters.get("brand_id"):
        where.append("g.brand_id=%s")
        params.append(int(filters["brand_id"]))
    if filters.get("min_price") not in (None, ""):
        where.append("g.price>=%s")
        params.append(float(filters["min_price"]))
    if filters.get("max_price") not in (None, ""):
        where.append("g.price<=%s")
        params.append(float(filters["max_price"]))
    if filters.get("is_hot") not in (None, ""):
        where.append("g.is_hot=%s")
        params.append(int(filters["is_hot"]))
    if filters.get("is_new") not in (None, ""):
        where.append("g.is_new=%s")
        params.append(int(filters["is_new"]))
    if filters.get("is_recommend") not in (None, ""):
        where.append("g.is_recommend=%s")
        params.append(int(filters["is_recommend"]))
    if filters.get("in_stock"):
        where.append("g.stock>0")
    sort_field = filters.get("sort_field") or "default"
    # 排序方向来自外部入参，必须白名单化，禁止直接拼进 SQL
    order = "ASC" if str(filters.get("sort_order") or "").lower() == "asc" else "DESC"
    sort_map = {
        "default": "g.id DESC",
        "price": f"g.price {order}",
        "sales": f"g.sales {order}",
        "created_at": f"g.created_at {order}",
    }
    order_sql = sort_map.get(sort_field, "g.id DESC")
    total = await database.fetch_one(
        f"SELECT COUNT(*) AS c FROM goods g WHERE {' AND '.join(where)}", params
    )
    rows = await database.fetch_all(
        f"{GOODS_LIST_SELECT} WHERE {' AND '.join(where)} ORDER BY {order_sql},g.id DESC "
        f"LIMIT %s OFFSET %s",
        params + [page_size, (page - 1) * page_size],
    )
    return page_data([_goods_item(r) for r in rows], total["c"], page, page_size)


async def goods_detail(goods_id: int) -> dict:
    row = await database.fetch_one(
        f"{GOODS_LIST_SELECT} WHERE g.id=%s AND g.status=1", (goods_id,)
    )
    if not row:
        not_found("商品不存在或已下架")
    detail_row = await database.fetch_one("SELECT detail_html FROM goods WHERE id=%s", (goods_id,))
    images = await database.fetch_all(
        "SELECT id,url FROM goods_images WHERE goods_id=%s AND type=1 ORDER BY sort ASC,id ASC",
        (goods_id,),
    )
    sku_rows = await database.fetch_all(
        "SELECT id,sku_code,price,stock,image FROM goods_sku WHERE goods_id=%s AND status=1 ORDER BY id ASC",
        (goods_id,),
    )
    spec_rows = await database.fetch_all(
        "SELECT gsv.sku_id,gsv.spec_id,gsv.spec_value_id,sv.value,s.name AS spec_name "
        "FROM goods_sku_spec_values gsv "
        "JOIN goods_sku sku ON sku.id=gsv.sku_id AND sku.goods_id=%s "
        "JOIN specification_values sv ON sv.id=gsv.spec_value_id "
        "JOIN specifications s ON s.id=gsv.spec_id ORDER BY s.sort ASC,s.id ASC,sv.id ASC",
        (goods_id,),
    )
    sku_values: dict[int, list[tuple[int, str]]] = {}
    for sr in spec_rows:
        sku_values.setdefault(sr["sku_id"], []).append((sr["spec_value_id"], sr["value"]))
    spec_order: dict[int, str] = {}
    for sr in spec_rows:
        spec_order.setdefault(sr["spec_id"], sr["spec_name"])
    spec_tree: dict[int, list[int]] = {}
    for sr in spec_rows:
        spec_tree.setdefault(sr["spec_id"], [])
        if sr["spec_value_id"] not in spec_tree[sr["spec_id"]]:
            spec_tree[sr["spec_id"]].append(sr["spec_value_id"])
    sku_map = {r["id"]: r for r in sku_rows}
    skus = []
    for sku_id, sku in sku_map.items():
        vals = sku_values.get(sku_id, [])
        skus.append({
            "id": sku["id"],
            "skuCode": sku["sku_code"],
            "price": _money(sku["price"]),
            "stock": sku["stock"] or 0,
            "image": sku["image"] or "",
            "specValueIds": [v[0] for v in vals],
            "specText": " ".join(v[1] for v in vals),
        })
    specs = []
    for spec_id, name in spec_order.items():
        value_rows = await database.fetch_all(
            "SELECT id,value FROM specification_values WHERE id IN (%s)" % (
                ",".join(["%s"] * len(spec_tree[spec_id]))
            ),
            spec_tree[spec_id],
        )
        vmap = {v["id"]: v["value"] for v in value_rows}
        specs.append({
            "id": spec_id,
            "name": name,
            "values": [{"id": vid, "value": vmap[vid]} for vid in spec_tree[spec_id] if vid in vmap],
        })
    stat = await database.fetch_one(
        "SELECT COUNT(*) AS c, SUM(CASE WHEN score>=4 THEN 1 ELSE 0 END) AS good "
        "FROM goods_comments WHERE goods_id=%s AND status=1",
        (goods_id,),
    )
    good_rate = 100 if stat["c"] else 0
    if stat["c"] and stat["good"] is not None:
        good_rate = round((stat["good"] or 0) / stat["c"] * 100)
    return {
        "id": row["id"],
        "name": row["name"],
        "subtitle": row["subtitle"] or "",
        "price": _money(row["price"]),
        "marketPrice": _money(row["market_price"]),
        "stock": row["stock"] or 0,
        "sales": row["sales"] or 0,
        "images": [{"id": im["id"], "url": im["url"]} for im in images],
        "skus": skus,
        "specs": specs,
        "detailHtml": (detail_row["detail_html"] if detail_row else "") or "",
        "commentCount": stat["c"] or 0,
        "goodRate": good_rate,
    }


async def list_comments(goods_id: int, page: int, page_size: int) -> dict:
    total = await database.fetch_one(
        "SELECT COUNT(*) AS c,SUM(CASE WHEN score>=4 THEN 1 ELSE 0 END) AS good "
        "FROM goods_comments WHERE goods_id=%s AND status=1",
        (goods_id,),
    )
    rows = await database.fetch_all(
        "SELECT gc.id,gc.score,gc.content,gc.images,gc.reply,gc.created_at,m.nickname AS member_name "
        "FROM goods_comments gc LEFT JOIN members m ON m.id=gc.member_id "
        "WHERE gc.goods_id=%s AND gc.status=1 ORDER BY gc.id DESC LIMIT %s OFFSET %s",
        (goods_id, page_size, (page - 1) * page_size),
    )
    c = total["c"] or 0
    good_rate = 100 if c else 0
    if c and total["good"] is not None:
        good_rate = round((total["good"] or 0) / c * 100)
    return page_data([
        {
            "id": r["id"],
            "memberName": r["member_name"] or "匿名用户",
            "score": r["score"],
            "content": r["content"] or "",
            "images": r["images"] or "",
            "reply": r["reply"] or "",
            "createdAt": r["created_at"],
        }
        for r in rows
    ], c, page, page_size)


async def post_comment(member_id: int, goods_id: int, score: int, content: str) -> int:
    if not (1 <= score <= 5):
        bad_request("评分需在 1~5 之间")
    order = await database.fetch_one(
        "SELECT o.id FROM orders o JOIN order_items oi ON oi.order_id=o.id "
        "WHERE o.member_id=%s AND oi.goods_id=%s AND o.order_status=4 "
        "ORDER BY o.id DESC LIMIT 1",
        (member_id, goods_id),
    )
    if not order:
        state_error("仅已完成订单的本人可评价该商品")
    exists = await database.fetch_one(
        "SELECT id FROM goods_comments WHERE member_id=%s AND goods_id=%s AND order_id=%s LIMIT 1",
        (member_id, goods_id, order["id"]),
    )
    if exists:
        state_error("该订单商品已评价，不可重复评价")
    goods = await database.fetch_one("SELECT id FROM goods WHERE id=%s AND status=1", (goods_id,))
    if not goods:
        not_found("商品不存在或已下架")
    cid = await database.execute_return_id(
        "INSERT INTO goods_comments (goods_id,member_id,order_id,score,content,status) "
        "VALUES (%s,%s,%s,%s,%s,0)",
        (goods_id, member_id, order["id"], score, content),
    )
    return cid


async def list_categories() -> dict:
    rows = await database.fetch_all(
        "SELECT id,name,icon,parent_id FROM goods_category WHERE is_show=1 ORDER BY sort ASC,id ASC"
    )
    nodes: dict[int, dict] = {}
    for r in rows:
        nodes[r["id"]] = {
            "id": r["id"],
            "name": r["name"],
            "icon": r["icon"] or "",
            "parentId": r["parent_id"],
            "children": [],
        }
    tree: list[dict] = []
    for node in nodes.values():
        if node["parentId"] and node["parentId"] in nodes:
            nodes[node["parentId"]]["children"].append(node)
        elif not node["parentId"]:
            tree.append(node)
    return {"list": tree}


async def list_brands() -> dict:
    rows = await database.fetch_all(
        "SELECT id,name,logo FROM brands WHERE status=1 ORDER BY sort ASC,id ASC"
    )
    return {"list": [{"id": r["id"], "name": r["name"], "logo": r["logo"] or ""} for r in rows]}


async def list_specs() -> dict:
    rows = await database.fetch_all(
        "SELECT gsv.spec_id,s.name AS spec_name,gsv.spec_value_id,sv.value "
        "FROM goods_sku_spec_values gsv "
        "JOIN goods_sku sku ON sku.id=gsv.sku_id "
        "JOIN goods g ON g.id=sku.goods_id AND g.status=1 "
        "JOIN specification_values sv ON sv.id=gsv.spec_value_id "
        "JOIN specifications s ON s.id=gsv.spec_id "
        "ORDER BY s.sort ASC,s.id ASC,sv.id ASC"
    )
    specs: dict[int, dict] = {}
    for r in rows:
        node = specs.setdefault(r["spec_id"], {"id": r["spec_id"], "name": r["spec_name"], "values": {}})
        node["values"].setdefault(r["spec_value_id"], r["value"])
    return {"list": [
        {"id": sid, "name": node["name"],
         "values": [{"id": vid, "value": val} for vid, val in node["values"].items()]}
        for sid, node in specs.items()
    ]}


async def visit(goods_id: int) -> None:
    goods = await database.fetch_one("SELECT id FROM goods WHERE id=%s AND status=1", (goods_id,))
    if not goods:
        not_found("商品不存在或已下架")
