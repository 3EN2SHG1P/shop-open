import io

from core import database

MODULE_TEXT = {
    "goods": "商品管理",
    "order": "订单管理",
    "member": "会员管理",
    "marketing": "营销管理",
    "content": "内容管理",
    "settings": "系统设置",
    "permission": "权限管理",
    "dashboard": "仪表盘",
}
ACTION_TEXT = {1: "登录", 2: "新增", 3: "编辑", 4: "删除", 5: "导出", 6: "登出", 7: "审核"}


async def _build_where(filters: dict) -> tuple[str, list]:
    where = ["1=1"]
    params: list = []
    if filters.get("admin_name"):
        where.append("au.username LIKE %s")
        params.append(f"%{filters['admin_name']}%")
    if filters.get("module"):
        where.append("al.module=%s")
        params.append(filters["module"])
    if filters.get("action_type") not in (None, ""):
        where.append("al.action_type=%s")
        params.append(int(filters["action_type"]))
    if filters.get("start_date"):
        where.append("DATE(al.created_at)>=%s")
        params.append(filters["start_date"])
    if filters.get("end_date"):
        where.append("DATE(al.created_at)<=%s")
        params.append(filters["end_date"])
    return " AND ".join(where), params


async def list_logs(page: int, page_size: int, filters: dict) -> dict:
    cond, params = await _build_where(filters)
    total = await database.fetch_one(
        f"SELECT COUNT(*) AS c FROM admin_logs al LEFT JOIN admin_users au ON au.id=al.admin_id WHERE {cond}", params
    )
    rows = await database.fetch_all(
        "SELECT al.id,al.module,al.action_type,al.target,al.ip,al.params_summary,al.created_at,au.username "
        f"FROM admin_logs al LEFT JOIN admin_users au ON au.id=al.admin_id WHERE {cond} "
        "ORDER BY al.id DESC LIMIT %s OFFSET %s",
        params + [page_size, (page - 1) * page_size],
    )
    return {
        "list": [
            {
                "id": r["id"],
                "module": r["module"],
                "moduleText": MODULE_TEXT.get(r["module"], r["module"] or "-"),
                "actionType": r["action_type"],
                "actionTypeText": ACTION_TEXT.get(r["action_type"], "-"),
                "target": r["target"] or "-",
                "summary": (r["params_summary"] or "").replace("demo:", ""),
                "ip": r["ip"] or "-",
                "adminName": r["username"] or f"管理员#{r['id']}",
                "createdAt": r["created_at"],
            }
            for r in rows
        ],
        "total": total["c"],
        "page": page,
        "page_size": page_size,
    }


async def export_logs(filters: dict) -> bytes:
    cond, params = await _build_where(filters)
    rows = await database.fetch_all(
        "SELECT al.id,al.module,al.action_type,al.target,al.ip,al.params_summary,al.created_at,au.username "
        f"FROM admin_logs al LEFT JOIN admin_users au ON au.id=al.admin_id WHERE {cond} "
        "ORDER BY al.id DESC LIMIT 50000",
        params,
    )
    buf = io.StringIO()
    buf.write("ID,操作人,模块,操作类型,目标,摘要,IP,操作时间\r\n")
    for r in rows:
        summary = (r["params_summary"] or "").replace("demo:", "").replace(",", "，").replace('"', "“")
        buf.write(
            ",".join(
                [
                    str(r["id"]),
                    r["username"] or f"管理员#{r['id']}",
                    MODULE_TEXT.get(r["module"], r["module"] or "-"),
                    ACTION_TEXT.get(r["action_type"], "-"),
                    (r["target"] or "-").replace(",", "，"),
                    summary,
                    r["ip"] or "-",
                    str(r["created_at"]),
                ]
            )
            + "\r\n"
        )
    return ("\ufeff" + buf.getvalue()).encode("utf-8")
