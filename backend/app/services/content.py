from core import audit, database
from core.errors import bad_request, duplicate, not_found, referenced
from core.money import f2 as _money

ARTICLE_STATUS_TEXT = {1: "已发布", 0: "草稿"}
AD_TYPE_TEXT = {1: "图片", 2: "视频", 3: "文字"}


# ==================== 文章分类 ====================


async def list_article_categories() -> list[dict]:
    rows = await database.fetch_all(
        "SELECT * FROM article_categories ORDER BY sort ASC, id ASC"
    )
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "sort": r["sort"],
            "status": r["status"],
            "articleCount": 0,
        }
        for r in rows
    ]


async def list_article_categories_with_count() -> list[dict]:
    rows = await database.fetch_all(
        "SELECT ac.*,COALESCE(cc.c,0) AS article_count FROM article_categories ac "
        "LEFT JOIN (SELECT category_id,COUNT(*) AS c FROM articles GROUP BY category_id) cc "
        "ON cc.category_id=ac.id ORDER BY ac.sort ASC,ac.id ASC"
    )
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "sort": r["sort"],
            "status": r["status"],
            "articleCount": r["article_count"],
        }
        for r in rows
    ]


async def save_article_category(category_id: int | None, body, user) -> int:
    name = body.name.strip()
    if not name:
        bad_request("分类名称不能为空")
    dup_sql = "SELECT id FROM article_categories WHERE name=%s"
    dup_params: list = [name]
    if category_id:
        dup_sql += " AND id<>%s"
        dup_params.append(category_id)
    if await database.fetch_one(dup_sql, dup_params):
        duplicate("分类名称已存在")
    if category_id:
        row = await database.fetch_one("SELECT id FROM article_categories WHERE id=%s", (category_id,))
        if not row:
            not_found("文章分类不存在")
        await database.execute(
            "UPDATE article_categories SET name=%s,sort=%s,status=%s WHERE id=%s",
            (name, body.sort, body.status, category_id),
        )
        await audit.log_action(user.id, "content", audit.ACTION_EDIT, f"article-category:{category_id}", f"编辑文章分类「{name}」")
        return category_id
    cid = await database.execute_return_id(
        "INSERT INTO article_categories (name,sort,status) VALUES (%s,%s,%s)",
        (name, body.sort, body.status),
    )
    await audit.log_action(user.id, "content", audit.ACTION_ADD, f"article-category:{cid}", f"新增文章分类「{name}」")
    return cid


async def delete_article_category(category_id: int, user) -> None:
    row = await database.fetch_one("SELECT id,name FROM article_categories WHERE id=%s", (category_id,))
    if not row:
        not_found("文章分类不存在")
    used = await database.fetch_one("SELECT COUNT(*) AS c FROM articles WHERE category_id=%s", (category_id,))
    if used and used["c"]:
        referenced("该分类下存在文章，不可删除")
    await database.execute("DELETE FROM article_categories WHERE id=%s", (category_id,))
    await audit.log_action(user.id, "content", audit.ACTION_DELETE, f"article-category:{category_id}", f"删除文章分类「{row['name']}」")


# ==================== 文章 ====================


def _article_item(r: dict) -> dict:
    return {
        "id": r["id"],
        "title": r["title"],
        "categoryId": r["category_id"],
        "categoryName": r["category_name"] or "",
        "author": r["author"] or "",
        "cover": r["cover"] or "",
        "summary": r["summary"] or "",
        "content": r["content"] or "",
        "seoTitle": r["seo_title"] or "",
        "seoKeywords": r["seo_keywords"] or "",
        "seoDesc": r["seo_desc"] or "",
        "status": r["status"],
        "statusText": ARTICLE_STATUS_TEXT.get(r["status"], ""),
        "publishTime": r["publish_time"],
        "createdAt": r["created_at"],
    }


async def list_articles(page: int, page_size: int, filters: dict) -> dict:
    where = ["1=1"]
    params: list = []
    if filters.get("keyword"):
        where.append("a.title LIKE %s")
        params.append(f"%{filters['keyword']}%")
    if filters.get("category_id") not in (None, "", "0"):
        where.append("a.category_id=%s")
        params.append(int(filters["category_id"]))
    if filters.get("status") not in (None, ""):
        where.append("a.status=%s")
        params.append(int(filters["status"]))
    cond = " AND ".join(where)
    total = await database.fetch_one(
        f"SELECT COUNT(*) AS c FROM articles a WHERE {cond}", params
    )
    rows = await database.fetch_all(
        "SELECT a.*,ac.name AS category_name FROM articles a LEFT JOIN article_categories ac ON ac.id=a.category_id "
        f"WHERE {cond} ORDER BY a.id DESC LIMIT %s OFFSET %s",
        params + [page_size, (page - 1) * page_size],
    )
    return {
        "list": [_article_item(r) for r in rows],
        "total": total["c"],
        "page": page,
        "page_size": page_size,
    }


async def save_article(article_id: int | None, body, user) -> int:
    title = body.title.strip()
    if not title:
        bad_request("文章标题不能为空")
    if body.category_id:
        cat = await database.fetch_one("SELECT id FROM article_categories WHERE id=%s", (body.category_id,))
        if not cat:
            not_found("所选文章分类不存在")
    data = (
        title, body.category_id, body.author.strip(), body.cover.strip(), body.summary.strip(), body.content,
        body.seo_title.strip(), body.seo_keywords.strip(), body.seo_desc.strip(), body.status, body.publish_time,
    )
    if article_id:
        row = await database.fetch_one("SELECT id,title FROM articles WHERE id=%s", (article_id,))
        if not row:
            not_found("文章不存在")
        await database.execute(
            "UPDATE articles SET title=%s,category_id=%s,author=%s,cover=%s,summary=%s,content=%s,seo_title=%s,"
            "seo_keywords=%s,seo_desc=%s,status=%s,publish_time=%s WHERE id=%s",
            data + (article_id,),
        )
        await audit.log_action(user.id, "content", audit.ACTION_EDIT, f"article:{article_id}", f"编辑文章「{title}」")
        return article_id
    aid = await database.execute_return_id(
        "INSERT INTO articles (title,category_id,author,cover,summary,content,seo_title,seo_keywords,seo_desc,"
        "status,publish_time,created_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        data + (user.id,),
    )
    await audit.log_action(user.id, "content", audit.ACTION_ADD, f"article:{aid}", f"新增文章「{title}」")
    return aid


async def delete_article(article_id: int, user) -> None:
    row = await database.fetch_one("SELECT id,title FROM articles WHERE id=%s", (article_id,))
    if not row:
        not_found("文章不存在")
    await database.execute("DELETE FROM articles WHERE id=%s", (article_id,))
    await audit.log_action(user.id, "content", audit.ACTION_DELETE, f"article:{article_id}", f"删除文章「{row['title']}」")


# ==================== 广告位 ====================


async def list_ad_positions() -> list[dict]:
    rows = await database.fetch_all(
        "SELECT ap.*,COALESCE(cc.c,0) AS ad_count FROM ad_positions ap "
        "LEFT JOIN (SELECT position_id,COUNT(*) AS c FROM ads GROUP BY position_id) cc "
        "ON cc.position_id=ap.id ORDER BY ap.id ASC"
    )
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "size": r["size"] or "",
            "status": r["status"],
            "adCount": r["ad_count"],
        }
        for r in rows
    ]


async def save_ad_position(position_id: int | None, body, user) -> int:
    name = body.name.strip()
    if not name:
        bad_request("广告位名称不能为空")
    if position_id:
        row = await database.fetch_one("SELECT id FROM ad_positions WHERE id=%s", (position_id,))
        if not row:
            not_found("广告位不存在")
        await database.execute(
            "UPDATE ad_positions SET name=%s,size=%s,status=%s WHERE id=%s",
            (name, body.size.strip(), body.status, position_id),
        )
        await audit.log_action(user.id, "content", audit.ACTION_EDIT, f"ad-position:{position_id}", f"编辑广告位「{name}」")
        return position_id
    pid = await database.execute_return_id(
        "INSERT INTO ad_positions (name,size,status) VALUES (%s,%s,%s)",
        (name, body.size.strip(), body.status),
    )
    await audit.log_action(user.id, "content", audit.ACTION_ADD, f"ad-position:{pid}", f"新增广告位「{name}」")
    return pid


async def delete_ad_position(position_id: int, user) -> None:
    row = await database.fetch_one("SELECT id,name FROM ad_positions WHERE id=%s", (position_id,))
    if not row:
        not_found("广告位不存在")
    used = await database.fetch_one("SELECT COUNT(*) AS c FROM ads WHERE position_id=%s", (position_id,))
    if used and used["c"]:
        referenced("该广告位下存在广告，不可删除")
    await database.execute("DELETE FROM ad_positions WHERE id=%s", (position_id,))
    await audit.log_action(user.id, "content", audit.ACTION_DELETE, f"ad-position:{position_id}", f"删除广告位「{row['name']}」")


# ==================== 广告 ====================


def _ad_item(r: dict) -> dict:
    return {
        "id": r["id"],
        "positionId": r["position_id"],
        "positionName": r["position_name"] or "",
        "type": r["type"],
        "typeText": AD_TYPE_TEXT.get(r["type"], ""),
        "image": r["image"] or "",
        "video": r["video"] or "",
        "link": r["link"] or "",
        "text": r["text"] or "",
        "sort": r["sort"],
        "startTime": r["start_time"],
        "endTime": r["end_time"],
        "status": r["status"],
        "statusText": "启用" if r["status"] else "停用",
        "createdAt": r["created_at"],
    }


async def list_ads(page: int, page_size: int, filters: dict) -> dict:
    where = ["1=1"]
    params: list = []
    if filters.get("keyword"):
        where.append("a.text LIKE %s")
        params.append(f"%{filters['keyword']}%")
    if filters.get("position_id") not in (None, "", "0"):
        where.append("a.position_id=%s")
        params.append(int(filters["position_id"]))
    if filters.get("status") not in (None, ""):
        where.append("a.status=%s")
        params.append(int(filters["status"]))
    cond = " AND ".join(where)
    total = await database.fetch_one(
        f"SELECT COUNT(*) AS c FROM ads a WHERE {cond}", params
    )
    rows = await database.fetch_all(
        "SELECT a.*,ap.name AS position_name FROM ads a LEFT JOIN ad_positions ap ON ap.id=a.position_id "
        f"WHERE {cond} ORDER BY a.id DESC LIMIT %s OFFSET %s",
        params + [page_size, (page - 1) * page_size],
    )
    return {
        "list": [_ad_item(r) for r in rows],
        "total": total["c"],
        "page": page,
        "page_size": page_size,
    }


async def save_ad(ad_id: int | None, body, user) -> int:
    pos = await database.fetch_one("SELECT id,name FROM ad_positions WHERE id=%s", (body.position_id,))
    if not pos:
        not_found("所选广告位不存在")
    if body.start_time and body.end_time and str(body.end_time) <= str(body.start_time):
        bad_request("广告结束时间必须晚于开始时间")
    data = (
        body.position_id, body.type, body.image.strip(), body.video.strip(), body.link.strip(), body.text.strip(),
        body.sort, body.start_time, body.end_time, body.status,
    )
    if ad_id:
        row = await database.fetch_one("SELECT id FROM ads WHERE id=%s", (ad_id,))
        if not row:
            not_found("广告不存在")
        await database.execute(
            "UPDATE ads SET position_id=%s,type=%s,image=%s,video=%s,link=%s,text=%s,sort=%s,start_time=%s,"
            "end_time=%s,status=%s WHERE id=%s",
            data + (ad_id,),
        )
        await audit.log_action(user.id, "content", audit.ACTION_EDIT, f"ad:{ad_id}", f"编辑广告「{body.text.strip() or ad_id}」")
        return ad_id
    aid = await database.execute_return_id(
        "INSERT INTO ads (position_id,type,image,video,link,text,sort,start_time,end_time,status) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        data,
    )
    await audit.log_action(user.id, "content", audit.ACTION_ADD, f"ad:{aid}", f"新增广告「{body.text.strip() or aid}」")
    return aid


async def delete_ad(ad_id: int, user) -> None:
    row = await database.fetch_one("SELECT id,text FROM ads WHERE id=%s", (ad_id,))
    if not row:
        not_found("广告不存在")
    await database.execute("DELETE FROM ads WHERE id=%s", (ad_id,))
    await audit.log_action(user.id, "content", audit.ACTION_DELETE, f"ad:{ad_id}", f"删除广告「{row['text'] or ad_id}」")


# ==================== 公告 ====================


def _notice_item(r: dict) -> dict:
    return {
        "id": r["id"],
        "title": r["title"],
        "content": r["content"] or "",
        "target": r["target"],
        "targetLevelId": r["target_level_id"],
        "publishTime": r["publish_time"],
        "status": r["status"],
        "statusText": "已发布" if r["status"] else "未发布",
        "createdAt": r["created_at"],
    }


async def list_notices(page: int, page_size: int, filters: dict) -> dict:
    where = ["1=1"]
    params: list = []
    if filters.get("keyword"):
        where.append("n.title LIKE %s")
        params.append(f"%{filters['keyword']}%")
    if filters.get("status") not in (None, ""):
        where.append("n.status=%s")
        params.append(int(filters["status"]))
    cond = " AND ".join(where)
    total = await database.fetch_one(
        f"SELECT COUNT(*) AS c FROM notices n WHERE {cond}", params
    )
    rows = await database.fetch_all(
        f"SELECT * FROM notices n WHERE {cond} ORDER BY n.id DESC LIMIT %s OFFSET %s",
        params + [page_size, (page - 1) * page_size],
    )
    return {
        "list": [_notice_item(r) for r in rows],
        "total": total["c"],
        "page": page,
        "page_size": page_size,
    }


async def save_notice(notice_id: int | None, body, user) -> int:
    title = body.title.strip()
    if not title:
        bad_request("公告标题不能为空")
    data = (
        title, body.content, body.target, body.target_level_id, body.publish_time, body.status,
    )
    if notice_id:
        row = await database.fetch_one("SELECT id FROM notices WHERE id=%s", (notice_id,))
        if not row:
            not_found("公告不存在")
        await database.execute(
            "UPDATE notices SET title=%s,content=%s,target=%s,target_level_id=%s,publish_time=%s,status=%s WHERE id=%s",
            data + (notice_id,),
        )
        await audit.log_action(user.id, "content", audit.ACTION_EDIT, f"notice:{notice_id}", f"编辑公告「{title}」")
        return notice_id
    nid = await database.execute_return_id(
        "INSERT INTO notices (title,content,target,target_level_id,publish_time,status,created_by) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s)",
        data + (user.id,),
    )
    await audit.log_action(user.id, "content", audit.ACTION_ADD, f"notice:{nid}", f"新增公告「{title}」")
    return nid


async def delete_notice(notice_id: int, user) -> None:
    row = await database.fetch_one("SELECT id,title FROM notices WHERE id=%s", (notice_id,))
    if not row:
        not_found("公告不存在")
    await database.execute("DELETE FROM notices WHERE id=%s", (notice_id,))
    await audit.log_action(user.id, "content", audit.ACTION_DELETE, f"notice:{notice_id}", f"删除公告「{row['title']}」")


async def level_options() -> list[dict]:
    rows = await database.fetch_all(
        "SELECT id,level_name,upgrade_amount FROM member_level WHERE status=1 ORDER BY upgrade_amount ASC,id ASC"
    )
    return [
        {"id": r["id"], "name": r["level_name"], "threshold": _money(r["upgrade_amount"])}
        for r in rows
    ]
