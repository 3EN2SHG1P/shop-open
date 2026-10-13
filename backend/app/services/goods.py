import csv
import io

from core import audit, database
from core.common import build_tree, row_to_camel, rows_to_camel, snake_to_camel
from core.deps import created_by_scope_condition
from core.errors import bad_request, duplicate, no_permission, referenced, state_error, not_found
from schemas.goods import (AuditReq, BrandSave, CategorySave, CommentAudit, CommentReply,
                           GoodsSave, SpecAttrSave)


async def _audit_enabled() -> bool:
    row = await database.fetch_one("SELECT config_value FROM system_configs WHERE config_key='goods.audit_enabled'")
    if not row:
        return False
    return row["config_value"] in ("1", "true", "True")


# ---------- 分类 ----------

async def category_tree() -> list[dict]:
    rows = await database.fetch_all(
        "SELECT id, parent_id, name, icon, sort, is_show, seo_title, seo_keywords, seo_desc, created_at "
        "FROM goods_category ORDER BY sort ASC, id ASC"
    )
    for r in rows:
        r["isShow"] = r.pop("is_show")
        r["seoTitle"] = r.pop("seo_title")
        r["seoKeywords"] = r.pop("seo_keywords")
        r["seoDesc"] = r.pop("seo_desc")
        r["createdAt"] = r.pop("created_at")
    return build_tree(rows)


async def create_category(body: CategorySave, operator) -> int:
    if body.parent_id:
        parent = await database.fetch_one("SELECT id FROM goods_category WHERE id=%s", (body.parent_id,))
        if not parent:
            not_found("父分类不存在")
    cid = await database.execute_return_id(
        "INSERT INTO goods_category (parent_id,name,icon,sort,is_show,seo_title,seo_keywords,seo_desc,created_by) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (body.parent_id, body.name, body.icon or None, body.sort, body.is_show,
         body.seo_title or None, body.seo_keywords or None, body.seo_desc or None, operator.id),
    )
    await audit.log_action(operator.id, "goods", audit.ACTION_ADD, f"category:{body.name}", "新增商品分类")
    return cid


async def update_category(cid: int, body: CategorySave, operator) -> None:
    row = await database.fetch_one("SELECT id,name FROM goods_category WHERE id=%s", (cid,))
    if not row:
        not_found("分类不存在")
    if body.parent_id:
        if body.parent_id == cid:
            state_error("不能将自身设为父级")
        child = await database.fetch_one("SELECT id FROM goods_category WHERE parent_id=%s LIMIT 1", (cid,))
        if child and body.parent_id == child["id"]:
            state_error("不能将父级设为子级")
    await database.execute(
        "UPDATE goods_category SET parent_id=%s,name=%s,icon=%s,sort=%s,is_show=%s,seo_title=%s,seo_keywords=%s,seo_desc=%s WHERE id=%s",
        (body.parent_id, body.name, body.icon or None, body.sort, body.is_show,
         body.seo_title or None, body.seo_keywords or None, body.seo_desc or None, cid),
    )
    await audit.log_action(operator.id, "goods", audit.ACTION_EDIT, f"category:{row['name']}", "编辑商品分类")


async def delete_category(cid: int, operator) -> None:
    row = await database.fetch_one("SELECT id,name FROM goods_category WHERE id=%s", (cid,))
    if not row:
        not_found("分类不存在")
    child = await database.fetch_one("SELECT id FROM goods_category WHERE parent_id=%s LIMIT 1", (cid,))
    if child:
        referenced("存在子分类，不可删除")
    goods = await database.fetch_one("SELECT id FROM goods WHERE category_id=%s LIMIT 1", (cid,))
    if goods:
        referenced("分类下存在商品，不可删除")
    await database.execute("DELETE FROM goods_category WHERE id=%s", (cid,))
    await audit.log_action(operator.id, "goods", audit.ACTION_DELETE, f"category:{row['name']}", "删除商品分类")


# ---------- 品牌 ----------

async def list_brands(keyword: str, status: int | None, page: int, page_size: int) -> dict:
    where = ["1=1"]
    params: list = []
    if keyword:
        where.append("name LIKE %s")
        params.append(f"%{keyword}%")
    if status is not None:
        where.append("b.status=%s")
        params.append(status)
    cond = " AND ".join(where)
    total = await database.fetch_one(f"SELECT COUNT(*) AS c FROM brands b WHERE {cond}", params)
    rows = await database.fetch_all(
        # goods_count 用相关子查询而非 JOIN+GROUP BY：品牌数量小且要保证分页行数=页数
        f"SELECT b.id,b.name,b.logo,b.description,b.sort,b.status,b.created_at,"
        f"(SELECT COUNT(*) FROM goods g WHERE g.brand_id=b.id) AS goods_count "
        f"FROM brands b WHERE {cond} "
        f"ORDER BY b.sort ASC,b.id DESC LIMIT %s OFFSET %s",
        params + [page_size, (page - 1) * page_size],
    )
    return {"list": rows_to_camel(rows), "total": total["c"], "page": page, "page_size": page_size}


async def create_brand(body: BrandSave, operator) -> int:
    existed = await database.fetch_one("SELECT id FROM brands WHERE name=%s", (body.name,))
    if existed:
        duplicate("品牌已存在")
    bid = await database.execute_return_id(
        "INSERT INTO brands (name,logo,description,sort,created_by) VALUES (%s,%s,%s,%s,%s)",
        (body.name, body.logo or None, body.description or None, body.sort, operator.id),
    )
    await audit.log_action(operator.id, "goods", audit.ACTION_ADD, f"brand:{body.name}", "新增品牌")
    return bid


async def update_brand(bid: int, body: BrandSave, operator) -> None:
    row = await database.fetch_one("SELECT id,name FROM brands WHERE id=%s", (bid,))
    if not row:
        not_found("品牌不存在")
    await database.execute(
        "UPDATE brands SET name=%s,logo=%s,description=%s,sort=%s WHERE id=%s",
        (body.name, body.logo or None, body.description or None, body.sort, bid),
    )
    await audit.log_action(operator.id, "goods", audit.ACTION_EDIT, f"brand:{row['name']}", "编辑品牌")


async def set_brand_status(bid: int, status: int, operator) -> None:
    row = await database.fetch_one("SELECT id,name FROM brands WHERE id=%s", (bid,))
    if not row:
        not_found("品牌不存在")
    await database.execute("UPDATE brands SET status=%s WHERE id=%s", (status, bid))
    await audit.log_action(operator.id, "goods", audit.ACTION_EDIT, f"brand:{row['name']}", "启禁用品牌")


async def delete_brand(bid: int, operator) -> None:
    row = await database.fetch_one("SELECT id,name FROM brands WHERE id=%s", (bid,))
    if not row:
        not_found("品牌不存在")
    goods = await database.fetch_one("SELECT id FROM goods WHERE brand_id=%s LIMIT 1", (bid,))
    if goods:
        referenced("品牌下存在商品，不可删除")
    await database.execute("DELETE FROM brands WHERE id=%s", (bid,))
    await audit.log_action(operator.id, "goods", audit.ACTION_DELETE, f"brand:{row['name']}", "删除品牌")


# ---------- 规格/属性 ----------

async def list_specs(category_id: int | None) -> list[dict]:
    cond = "1=1"
    params: list = []
    if category_id:
        # 必须整体加括号：OR 优先级低于 AND，一旦后续再追加条件就会静默改变语义
        cond = "(category_id=%s OR category_id=0)"
        params.append(category_id)
    rows = await database.fetch_all(f"SELECT id,name,category_id,sort,created_at FROM specifications WHERE {cond} ORDER BY sort ASC,id ASC", params)
    if not rows:
        return []
    ids = [r["id"] for r in rows]
    ph = ",".join(["%s"] * len(ids))
    vals = await database.fetch_all(f"SELECT id,spec_id,value FROM specification_values WHERE spec_id IN ({ph}) ORDER BY id ASC", ids)
    grouped: dict = {}
    for v in vals:
        grouped.setdefault(v["spec_id"], []).append({"id": v["id"], "value": v["value"]})
    result = []
    for r in rows:
        result.append({
            "id": r["id"],
            "name": r["name"],
            "categoryId": r["category_id"],
            "sort": r["sort"],
            "createdAt": r["created_at"],
            "values": grouped.get(r["id"], []),
        })
    return result


async def create_spec(body: SpecAttrSave, operator) -> int:
    sid = await database.execute_return_id(
        "INSERT INTO specifications (name,category_id,sort,created_by) VALUES (%s,%s,%s,%s)",
        (body.name, body.category_id, body.sort, operator.id),
    )
    for v in body.values:
        await database.execute("INSERT INTO specification_values (spec_id,value) VALUES (%s,%s)", (sid, v.value))
    await audit.log_action(operator.id, "goods", audit.ACTION_ADD, f"spec:{body.name}", "新增规格")
    return sid


async def update_spec(sid: int, body: SpecAttrSave, operator) -> None:
    row = await database.fetch_one("SELECT id,name FROM specifications WHERE id=%s", (sid,))
    if not row:
        not_found("规格不存在")
    await database.execute("UPDATE specifications SET name=%s,category_id=%s,sort=%s WHERE id=%s",
                           (body.name, body.category_id, body.sort, sid))
    await _sync_named_values("specification_values", "spec_id", sid, body.values, operator)
    await audit.log_action(operator.id, "goods", audit.ACTION_EDIT, f"spec:{row['name']}", "编辑规格")


async def delete_spec(sid: int, operator) -> None:
    row = await database.fetch_one("SELECT id,name FROM specifications WHERE id=%s", (sid,))
    if not row:
        not_found("规格不存在")
    used = await database.fetch_one("SELECT id FROM goods_sku_spec_values WHERE spec_id=%s LIMIT 1", (sid,))
    if used:
        referenced("规格已被商品SKU使用，不可删除")
    await database.execute("DELETE FROM specification_values WHERE spec_id=%s", (sid,))
    await database.execute("DELETE FROM specifications WHERE id=%s", (sid,))
    await audit.log_action(operator.id, "goods", audit.ACTION_DELETE, f"spec:{row['name']}", "删除规格")


async def list_attrs(category_id: int | None) -> list[dict]:
    cond = "1=1"
    params: list = []
    if category_id:
        # 同上：OR 必须整体加括号，否则后续追加 AND 条件时优先级出错
        cond = "(category_id=%s OR category_id=0)"
        params.append(category_id)
    rows = await database.fetch_all(f"SELECT id,name,category_id,sort,created_at FROM attributes WHERE {cond} ORDER BY sort ASC,id ASC", params)
    if not rows:
        return []
    ids = [r["id"] for r in rows]
    ph = ",".join(["%s"] * len(ids))
    vals = await database.fetch_all(f"SELECT id,attr_id,value FROM attribute_values WHERE attr_id IN ({ph}) ORDER BY id ASC", ids)
    grouped: dict = {}
    for v in vals:
        grouped.setdefault(v["attr_id"], []).append({"id": v["id"], "value": v["value"]})
    result = []
    for r in rows:
        result.append({
            "id": r["id"],
            "name": r["name"],
            "categoryId": r["category_id"],
            "sort": r["sort"],
            "createdAt": r["created_at"],
            "values": grouped.get(r["id"], []),
        })
    return result


async def create_attr(body: SpecAttrSave, operator) -> int:
    aid = await database.execute_return_id(
        "INSERT INTO attributes (name,category_id,sort,created_by) VALUES (%s,%s,%s,%s)",
        (body.name, body.category_id, body.sort, operator.id),
    )
    for v in body.values:
        await database.execute("INSERT INTO attribute_values (attr_id,value) VALUES (%s,%s)", (aid, v.value))
    await audit.log_action(operator.id, "goods", audit.ACTION_ADD, f"attr:{body.name}", "新增属性")
    return aid


async def update_attr(aid: int, body: SpecAttrSave, operator) -> None:
    row = await database.fetch_one("SELECT id,name FROM attributes WHERE id=%s", (aid,))
    if not row:
        not_found("属性不存在")
    await database.execute("UPDATE attributes SET name=%s,category_id=%s,sort=%s WHERE id=%s",
                           (body.name, body.category_id, body.sort, aid))
    await _sync_named_values("attribute_values", "attr_id", aid, body.values, operator)
    await audit.log_action(operator.id, "goods", audit.ACTION_EDIT, f"attr:{row['name']}", "编辑属性")


async def delete_attr(aid: int, operator) -> None:
    row = await database.fetch_one("SELECT id,name FROM attributes WHERE id=%s", (aid,))
    if not row:
        not_found("属性不存在")
    await database.execute("DELETE FROM attribute_values WHERE attr_id=%s", (aid,))
    await database.execute("DELETE FROM attributes WHERE id=%s", (aid,))
    await audit.log_action(operator.id, "goods", audit.ACTION_DELETE, f"attr:{row['name']}", "删除属性")


async def _sync_named_values(table: str, fk: str, owner_id: int, values: list, operator) -> None:
    old_rows = await database.fetch_all(f"SELECT id,value FROM {table} WHERE {fk}=%s", (owner_id,))
    old_map = {r["value"]: r["id"] for r in old_rows}
    keep_ids = []
    for v in values:
        if v.value in old_map:
            keep_ids.append(old_map[v.value])
        else:
            new_id = await database.execute_return_id(
                f"INSERT INTO {table} ({fk},value) VALUES (%s,%s)", (owner_id, v.value)
            )
            keep_ids.append(new_id)
    if keep_ids:
        ph = ",".join(["%s"] * len(keep_ids))
        await database.execute(f"DELETE FROM {table} WHERE {fk}=%s AND id NOT IN ({ph})", [owner_id] + keep_ids)
    else:
        await database.execute(f"DELETE FROM {table} WHERE {fk}=%s", (owner_id,))


# ---------- 商品 ----------

async def _build_goods_where(filters: dict, user) -> tuple[str, list]:
    cond = ["g.status >= 0"]
    params: list = []
    keyword = filters.get("keyword")
    if keyword:
        cond.append("(g.name LIKE %s OR g.subtitle LIKE %s OR g.spu_code LIKE %s)")
        params += [f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"]
    if filters.get("category_id"):
        cond.append("g.category_id=%s")
        params.append(filters["category_id"])
    if filters.get("brand_id"):
        cond.append("g.brand_id=%s")
        params.append(filters["brand_id"])
    if filters.get("status") is not None:
        if int(filters["status"]) == 2:
            cond.append("g.audit_status=1")
        else:
            cond.append("g.status=%s")
            params.append(int(filters["status"]))
    if filters.get("audit_status") is not None:
        cond.append("g.audit_status=%s")
        params.append(int(filters["audit_status"]))
    min_p, max_p = filters.get("min_price"), filters.get("max_price")
    if min_p is not None:
        cond.append("g.price>=%s")
        params.append(float(min_p))
    if max_p is not None:
        cond.append("g.price<=%s")
        params.append(float(max_p))
    if filters.get("start_date"):
        cond.append("g.created_at>=%s")
        params.append(filters["start_date"] + " 00:00:00")
    if filters.get("end_date"):
        cond.append("g.created_at<=%s")
        params.append(filters["end_date"] + " 23:59:59")
    scope_sql, scope_params = await created_by_scope_condition(user, "g")
    if scope_sql:
        cond.append(scope_sql)
        params.extend(scope_params)
    return " AND ".join(cond), params


async def list_goods(page: int, page_size: int, filters: dict, user) -> dict:
    cond, params = await _build_goods_where(filters, user)
    total = await database.fetch_one(f"SELECT COUNT(*) AS c FROM goods g WHERE {cond}", params)
    rows = await database.fetch_all(
        f"SELECT g.id,g.name,g.subtitle,g.category_id,g.brand_id,g.spu_code,g.unit,g.price,g.market_price,"
        f"g.stock,g.warn_stock,g.sales,g.status,g.audit_status,g.is_recommend,g.is_hot,g.is_new,"
        f"g.created_at,g.updated_at, c.name AS category_name, b.name AS brand_name, "
        # 主图口径与其他三处保持一致（shop_common.get_goods_image / shop_catalog.IMAGE_SUBQUERY / shop_cart）：type=1
        f"(SELECT gi.url FROM goods_images gi WHERE gi.goods_id=g.id AND gi.type=1 "
        f"ORDER BY gi.sort ASC, gi.id ASC LIMIT 1) AS main_image "
        f"FROM goods g LEFT JOIN goods_category c ON c.id=g.category_id "
        f"LEFT JOIN brands b ON b.id=g.brand_id WHERE {cond} ORDER BY g.id DESC LIMIT %s OFFSET %s",
        params + [page_size, (page - 1) * page_size],
    )
    items = []
    for r in rows:
        d = row_to_camel(r)
        d["categoryId"] = d.pop("categoryId", r["category_id"])
        d["brandId"] = d.pop("brandId", r["brand_id"])
        d["categoryName"] = r.get("category_name")
        d["brandName"] = r.get("brand_name")
        d["statusText"] = {0: "下架", 1: "上架", 2: "待审核"}.get(r["status"], "未知")
        items.append(d)
    return {"list": items, "total": total["c"], "page": page, "page_size": page_size}


async def _require_goods_owner(goods_id: int, user) -> None:
    """单条商品的数据权限校验。

    列表早已按 data_scope 收敛，但读详情 / 改 / 删 / 审核过去只按 id 查，
    导致 data_scope=1 的管理员可以直接越权操作他人商品。列表限权必须下沉到单条读写。
    """
    scope_sql, scope_params = await created_by_scope_condition(user, "g")
    if not scope_sql:
        return
    row = await database.fetch_one(
        f"SELECT g.id FROM goods g WHERE g.id=%s AND {scope_sql}", [goods_id] + scope_params
    )
    if not row:
        no_permission("无权操作该商品")


async def get_goods(goods_id: int, user) -> dict:
    await _require_goods_owner(goods_id, user)
    row = await database.fetch_one("SELECT * FROM goods WHERE id=%s", (goods_id,))
    if not row:
        not_found("商品不存在")
    images = await database.fetch_all("SELECT id,url,sort,type FROM goods_images WHERE goods_id=%s ORDER BY sort ASC,id ASC", (goods_id,))
    skus = await database.fetch_all("SELECT id,sku_code,price,stock,image,status FROM goods_sku WHERE goods_id=%s ORDER BY id ASC", (goods_id,))
    spec_rows = []
    if skus:
        sku_ids = [s["id"] for s in skus]
        ph = ",".join(["%s"] * len(sku_ids))
        spec_rows = await database.fetch_all(
            f"SELECT sku_id,spec_id,spec_value_id FROM goods_sku_spec_values WHERE sku_id IN ({ph})", sku_ids
        )
    spec_map: dict = {}
    for s in spec_rows:
        spec_map.setdefault(s["sku_id"], []).append({"specId": s["spec_id"], "specValueId": s["spec_value_id"]})
    sku_list = []
    for s in skus:
        sku_list.append({
            "id": s["id"],
            "skuCode": s["sku_code"],
            "price": float(s["price"]),
            "stock": s["stock"],
            "image": s["image"],
            "status": s["status"],
            "specValues": spec_map.get(s["id"], []),
        })
    data = row_to_camel(row)
    data["images"] = rows_to_camel(images)
    data["skus"] = sku_list
    data["seo"] = {"title": data.pop("seoTitle", None), "keywords": data.pop("seoKeywords", None), "desc": data.pop("seoDesc", None)}
    return data


async def create_goods(body: GoodsSave, operator) -> int:
    audit_on = await _audit_enabled()
    status = body.status
    audit_status = 0
    if audit_on:
        status = 2
        audit_status = 1
    if not body.skus:
        bad_request("至少需要一个SKU")
    if body.category_id:
        cat = await database.fetch_one("SELECT id FROM goods_category WHERE id=%s", (body.category_id,))
        if not cat:
            not_found("分类不存在")
    min_price = min((s.price for s in body.skus), default=0.00)
    price = body.price if body.price and float(body.price) > 0 else min_price
    async with database.transaction() as cur:
        await cur.execute(
            "INSERT INTO goods (name,subtitle,category_id,brand_id,spu_code,unit,market_price,price,cost_price,"
            "stock,warn_stock,status,is_recommend,is_hot,is_new,detail_html,freight_template_id,seo_title,seo_keywords,"
            "seo_desc,is_presale,presale_start,presale_end,buy_limit,points_discount_ratio,on_sale_time,audit_status,audit_note,created_by) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,0,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NULL,%s)",
            (body.name, body.subtitle or None, body.category_id, body.brand_id, body.spu_code or None, body.unit,
             body.market_price, price, body.cost_price, body.warn_stock, status, body.is_recommend, body.is_hot,
             body.is_new, body.detail_html or None, body.freight_template_id, body.seo_title or None,
             body.seo_keywords or None, body.seo_desc or None, body.is_presale, body.presale_start,
             body.presale_end, body.buy_limit, body.points_discount_ratio, body.on_sale_time if hasattr(body, "on_sale_time") else None,
             audit_status, operator.id),
        )
        goods_id = cur.lastrowid
        total_stock = 0
        for img in body.images:
            await cur.execute("INSERT INTO goods_images (goods_id,url,sort,type) VALUES (%s,%s,%s,%s)",
                              (goods_id, img.url, img.sort, img.type))
        for sku in body.skus:
            await cur.execute(
                "INSERT INTO goods_sku (goods_id,sku_code,price,stock,image,status) VALUES (%s,%s,%s,%s,%s,1)",
                (goods_id, sku.sku_code or f"SKU{goods_id}", sku.price, sku.stock, sku.image or None),
            )
            sku_id = cur.lastrowid
            total_stock += sku.stock
            for sv in sku.spec_values:
                await cur.execute(
                    "INSERT INTO goods_sku_spec_values (sku_id,spec_id,spec_value_id) VALUES (%s,%s,%s)",
                    (sku_id, sv.spec_id, sv.spec_value_id),
                )
        await cur.execute("UPDATE goods SET stock=%s WHERE id=%s", (total_stock, goods_id))
    await audit.log_action(operator.id, "goods", audit.ACTION_ADD, f"goods:{body.name}", "新增商品")
    return goods_id


async def update_goods(goods_id: int, body: GoodsSave, operator) -> None:
    await _require_goods_owner(goods_id, operator)
    row = await database.fetch_one("SELECT id,name,audit_status FROM goods WHERE id=%s", (goods_id,))
    if not row:
        not_found("商品不存在")
    if not body.skus:
        bad_request("至少需要一个SKU")
    audit_on = await _audit_enabled()
    status = body.status
    audit_status = row["audit_status"]
    if audit_on and audit_status != 2:
        status = 2
        audit_status = 1
    min_price = min((s.price for s in body.skus), default=0.00)
    price = body.price if body.price and float(body.price) > 0 else min_price
    old_skus = await database.fetch_all("SELECT id,sku_code FROM goods_sku WHERE goods_id=%s", (goods_id,))
    old_map = {s["sku_code"]: s["id"] for s in old_skus}
    new_codes = set()
    async with database.transaction() as cur:
        await cur.execute(
            "UPDATE goods SET name=%s,subtitle=%s,category_id=%s,brand_id=%s,spu_code=%s,unit=%s,market_price=%s,"
            "price=%s,cost_price=%s,warn_stock=%s,status=%s,is_recommend=%s,is_hot=%s,is_new=%s,detail_html=%s,"
            "freight_template_id=%s,seo_title=%s,seo_keywords=%s,seo_desc=%s,is_presale=%s,presale_start=%s,"
            "presale_end=%s,buy_limit=%s,points_discount_ratio=%s,audit_status=%s,audit_note=NULL WHERE id=%s",
            (body.name, body.subtitle or None, body.category_id, body.brand_id, body.spu_code or None, body.unit,
             body.market_price, price, body.cost_price, body.warn_stock, status, body.is_recommend, body.is_hot,
             body.is_new, body.detail_html or None, body.freight_template_id, body.seo_title or None,
             body.seo_keywords or None, body.seo_desc or None, body.is_presale, body.presale_start,
             body.presale_end, body.buy_limit, body.points_discount_ratio, audit_status, goods_id),
        )
        await cur.execute("DELETE FROM goods_images WHERE goods_id=%s", (goods_id,))
        for img in body.images:
            await cur.execute("INSERT INTO goods_images (goods_id,url,sort,type) VALUES (%s,%s,%s,%s)",
                              (goods_id, img.url, img.sort, img.type))
        total_stock = 0
        for sku in body.skus:
            code = sku.sku_code or f"SKU{goods_id}"
            new_codes.add(code)
            if code in old_map:
                sku_id = old_map[code]
                if sku.original_stock is not None:
                    # 乐观锁：只有库存仍等于"编辑页打开时的快照"才允许覆盖。
                    # 管理员打开编辑页到提交之间可能已有订单产生，若用表单里的库存快照
                    # 直接覆盖，会把这段时间的销量凭空调回，导致库存虚高 → 超卖。
                    await cur.execute(
                        "UPDATE goods_sku SET price=%s,stock=%s,image=%s WHERE id=%s AND stock=%s",
                        (sku.price, sku.stock, sku.image or None, sku_id, sku.original_stock),
                    )
                    if not cur.rowcount:
                        state_error(f"SKU「{code}」库存已被新订单变更，请刷新后重试")
                else:
                    await cur.execute(
                        "UPDATE goods_sku SET price=%s,stock=%s,image=%s WHERE id=%s",
                        (sku.price, sku.stock, sku.image or None, sku_id),
                    )
                await cur.execute("DELETE FROM goods_sku_spec_values WHERE sku_id=%s", (sku_id,))
            else:
                await cur.execute(
                    "INSERT INTO goods_sku (goods_id,sku_code,price,stock,image,status) VALUES (%s,%s,%s,%s,%s,1)",
                    (goods_id, code, sku.price, sku.stock, sku.image or None),
                )
                sku_id = cur.lastrowid
            total_stock += sku.stock
            for sv in sku.spec_values:
                await cur.execute(
                    "INSERT INTO goods_sku_spec_values (sku_id,spec_id,spec_value_id) VALUES (%s,%s,%s)",
                    (sku_id, sv.spec_id, sv.spec_value_id),
                )
        for code, sid in old_map.items():
            if code not in new_codes:
                used = await cur.execute("SELECT id FROM order_items WHERE sku_id=%s LIMIT 1", (sid,))
                if used:
                    raise referenced("SKU已产生订单，不能删除，请保持其存在于规格中")
                await cur.execute("DELETE FROM goods_sku_spec_values WHERE sku_id=%s", (sid,))
                await cur.execute("DELETE FROM goods_sku WHERE id=%s", (sid,))
        await cur.execute("UPDATE goods SET stock=%s WHERE id=%s", (total_stock, goods_id))
    await audit.log_action(operator.id, "goods", audit.ACTION_EDIT, f"goods:{row['name']}", "编辑商品")


async def delete_goods(goods_id: int, operator) -> None:
    await _require_goods_owner(goods_id, operator)
    row = await database.fetch_one("SELECT id,name FROM goods WHERE id=%s", (goods_id,))
    if not row:
        not_found("商品不存在")
    used = await database.fetch_one("SELECT id FROM order_items WHERE goods_id=%s LIMIT 1", (goods_id,))
    if used:
        referenced("商品已产生订单，不可删除")
    async with database.transaction() as cur:
        await cur.execute("DELETE FROM goods_images WHERE goods_id=%s", (goods_id,))
        await cur.execute("SELECT id FROM goods_sku WHERE goods_id=%s", (goods_id,))
        skus = await cur.fetchall()
        for s in skus:
            await cur.execute("DELETE FROM goods_sku_spec_values WHERE sku_id=%s", (s["id"],))
        await cur.execute("DELETE FROM goods_sku WHERE goods_id=%s", (goods_id,))
        await cur.execute("DELETE FROM goods WHERE id=%s", (goods_id,))
    await audit.log_action(operator.id, "goods", audit.ACTION_DELETE, f"goods:{row['name']}", "删除商品")


async def batch_operate(ids: list[int], action: str, status: int | None, operator) -> None:
    if not ids:
        bad_request("请选择商品")
    ph = ",".join(["%s"] * len(ids))
    scope_sql, scope_params = await created_by_scope_condition(operator, "g")
    scope_clause = f" AND {scope_sql}" if scope_sql else ""
    rows = await database.fetch_all(f"SELECT id,name FROM goods g WHERE g.id IN ({ph}){scope_clause}", ids + scope_params)
    if not rows:
        not_found("商品不存在")
    if scope_sql and len(rows) != len(set(ids)):
        # 传进来的 id 里有不属于当前管理员的数据——整体拒绝，避免"部分成功"掩住越权
        no_permission("所选商品中包含无权操作的商品")
    if action == "delete":
        # 先整体校验再逐条删除，避免中途失败造成「删了一半」
        used = await database.fetch_all(
            f"SELECT DISTINCT goods_id FROM order_items WHERE goods_id IN ({ph})", ids
        )
        if used:
            referenced("所选商品中包含已产生订单的商品，不可删除")
        for r in rows:
            await delete_goods(r["id"], operator)
        return
    if status == 2:
        await database.execute(f"UPDATE goods SET status=0, audit_status=1, audit_note=NULL WHERE id IN ({ph})", ids)
    else:
        await database.execute(f"UPDATE goods SET status=%s WHERE id IN ({ph})", [status] + ids)
    await audit.log_action(operator.id, "goods", audit.ACTION_EDIT, f"goods:batch[{action}]", f"批量{'上架' if status == 1 else '下架'}商品")


async def audit_goods(goods_id: int, body: AuditReq, operator) -> None:
    await _require_goods_owner(goods_id, operator)
    row = await database.fetch_one("SELECT id,name,status,audit_status FROM goods WHERE id=%s", (goods_id,))
    if not row:
        not_found("商品不存在")
    if row["audit_status"] != 1:
        state_error("商品不在待审核状态")
    if body.pass_flag:
        new_status, new_audit = 1, 2
    else:
        new_status, new_audit = 0, 3
    await database.execute(
        "UPDATE goods SET status=%s,audit_status=%s,audit_note=%s WHERE id=%s",
        (new_status, new_audit, body.note or None, goods_id),
    )
    await audit.log_action(operator.id, "goods", audit.ACTION_AUDIT, f"goods:{row['name']}", f"商品审核{'通过' if body.pass_flag else '驳回'}")


async def export_goods(filters: dict, user) -> bytes:
    cond, params = await _build_goods_where(filters, user)
    rows = await database.fetch_all(
        f"SELECT g.id,g.spu_code,g.name,g.price,g.market_price,g.stock,g.sales,g.status,g.audit_status,"
        f"g.created_at,c.name AS category_name,b.name AS brand_name "
        f"FROM goods g LEFT JOIN goods_category c ON c.id=g.category_id LEFT JOIN brands b ON b.id=g.brand_id "
        f"WHERE {cond} ORDER BY g.id DESC LIMIT 50000",
        params,
    )
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["ID", "SPU编码", "商品名称", "分类", "品牌", "销售价", "市场价", "库存", "销量", "状态", "审核状态", "创建时间"])
    for r in rows:
        writer.writerow([
            r["id"], r["spu_code"], r["name"], r["category_name"] or "", r["brand_name"] or "",
            r["price"], r["market_price"], r["stock"], r["sales"],
            {0: "下架", 1: "上架", 2: "待审核"}.get(r["status"], ""),
            {0: "无需审核", 1: "待审核", 2: "已通过", 3: "已驳回"}.get(r["audit_status"], ""),
            r["created_at"],
        ])
    return ("\ufeff" + buf.getvalue()).encode("utf-8")


# ---------- 评论 ----------

async def list_comments(page: int, page_size: int, filters: dict) -> dict:
    where = ["1=1"]
    params: list = []
    if filters.get("goods_id"):
        where.append("gc.goods_id=%s")
        params.append(filters["goods_id"])
    if filters.get("member_id"):
        where.append("gc.member_id=%s")
        params.append(filters["member_id"])
    if filters.get("status") is not None:
        where.append("gc.status=%s")
        params.append(filters["status"])
    if filters.get("score"):
        where.append("gc.score=%s")
        params.append(filters["score"])
    if filters.get("keyword"):
        where.append("(gc.content LIKE %s OR g.name LIKE %s)")
        params += [f"%{filters['keyword']}%", f"%{filters['keyword']}%"]
    cond = " AND ".join(where)
    total = await database.fetch_one(f"SELECT COUNT(*) AS c FROM goods_comments gc JOIN goods g ON g.id=gc.goods_id WHERE {cond}", params)
    rate = await database.fetch_one(
        f"SELECT COUNT(*) AS t, SUM(CASE WHEN gc.score>=4 THEN 1 ELSE 0 END) AS good, "
        f"SUM(CASE WHEN gc.score<=2 THEN 1 ELSE 0 END) AS bad FROM goods_comments gc JOIN goods g ON g.id=gc.goods_id WHERE {cond}",
        params,
    )
    rows = await database.fetch_all(
        f"SELECT gc.id,gc.goods_id,gc.member_id,gc.order_id,gc.score,gc.content,gc.images,gc.status,gc.reply,"
        f"gc.reply_time,gc.created_at,g.name AS goods_name,m.nickname AS member_name "
        f"FROM goods_comments gc JOIN goods g ON g.id=gc.goods_id "
        f"LEFT JOIN members m ON m.id=gc.member_id WHERE {cond} ORDER BY gc.id DESC LIMIT %s OFFSET %s",
        params + [page_size, (page - 1) * page_size],
    )
    items = []
    for r in rows:
        d = row_to_camel(r)
        d["goodsId"] = r["goods_id"]
        d["memberId"] = r["member_id"]
        d["orderId"] = r["order_id"]
        d["replyTime"] = d.pop("replyTime", None)
        items.append(d)
    t = rate["t"] or 0
    return {
        "list": items,
        "total": total["c"],
        "page": page,
        "page_size": page_size,
        "goodRate": round((rate["good"] or 0) / t * 100, 2) if t else 0,
        "badRate": round((rate["bad"] or 0) / t * 100, 2) if t else 0,
    }


async def audit_comment(cid: int, body: CommentAudit, operator) -> None:
    row = await database.fetch_one("SELECT id FROM goods_comments WHERE id=%s", (cid,))
    if not row:
        not_found("评论不存在")
    await database.execute("UPDATE goods_comments SET status=%s WHERE id=%s", (2 if not body.pass_flag else 1, cid))
    await audit.log_action(operator.id, "goods", audit.ACTION_AUDIT, f"comment:{cid}", f"评论审核{'通过' if body.pass_flag else '驳回'}")


async def reply_comment(cid: int, body: CommentReply, operator) -> None:
    row = await database.fetch_one("SELECT id FROM goods_comments WHERE id=%s", (cid,))
    if not row:
        not_found("评论不存在")
    await database.execute("UPDATE goods_comments SET reply=%s, reply_time=NOW() WHERE id=%s", (body.content, cid))
    await audit.log_action(operator.id, "goods", audit.ACTION_EDIT, f"comment:{cid}", "回复评论")


async def delete_comment(cid: int, operator) -> None:
    row = await database.fetch_one("SELECT id FROM goods_comments WHERE id=%s", (cid,))
    if not row:
        not_found("评论不存在")
    await database.execute("DELETE FROM goods_comments WHERE id=%s", (cid,))
    await audit.log_action(operator.id, "goods", audit.ACTION_DELETE, f"comment:{cid}", "删除评论")
