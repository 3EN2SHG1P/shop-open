from core import audit, database
from core.errors import bad_request, duplicate, not_found, referenced


async def get_configs(group: str) -> dict:
    rows = await database.fetch_all(
        "SELECT config_key,config_value,remark FROM system_configs WHERE config_group=%s ORDER BY id ASC",
        (group,),
    )
    return {
        "group": group,
        "items": {r["config_key"]: (r["config_value"] or "") for r in rows},
    }


async def save_configs(group: str, items: dict, user) -> None:
    if not items:
        bad_request("没有可保存的配置项")
    exist_rows = await database.fetch_all(
        "SELECT config_key,config_value FROM system_configs WHERE config_group=%s", (group,)
    )
    exist_map = {r["config_key"]: r["config_value"] for r in exist_rows}
    for key, value in items.items():
        if not key.startswith(f"{group}."):
            bad_request(f"配置项 {key} 不属于 {group} 分组")
        value_str = str(value) if value is not None else ""
        if key in exist_map:
            if exist_map[key] != value_str:
                await database.execute(
                    "UPDATE system_configs SET config_value=%s WHERE config_key=%s",
                    (value_str, key),
                )
        else:
            await database.execute(
                "INSERT INTO system_configs (config_key,config_value,config_group) VALUES (%s,%s,%s)",
                (key, value_str, group),
            )
    await audit.log_action(user.id, "settings", audit.ACTION_EDIT, f"settings/{group}", f"修改「{group}」分组配置")


# ==================== 运费模板 ====================

FREIGHT_TYPE_TEXT = {1: "包邮", 2: "按重量", 3: "按件数"}


def _freight_item(r: dict) -> dict:
    return {
        "id": r["id"],
        "name": r["name"],
        "type": r["type"],
        "typeText": FREIGHT_TYPE_TEXT.get(r["type"], ""),
        "isFreeShipping": r["is_free_shipping"],
        "regionsJson": r["regions_json"] or "[]",
        "createdAt": r["created_at"],
    }


async def list_freight_templates() -> list[dict]:
    rows = await database.fetch_all("SELECT * FROM freight_templates ORDER BY id DESC")
    return [_freight_item(r) for r in rows]


async def save_freight_template(template_id: int | None, body, user) -> int:
    name = body.name.strip()
    if not name:
        bad_request("模板名称不能为空")
    if body.type == 1:
        body.is_free_shipping = 1
    if template_id:
        row = await database.fetch_one("SELECT id FROM freight_templates WHERE id=%s", (template_id,))
        if not row:
            not_found("运费模板不存在")
        await database.execute(
            "UPDATE freight_templates SET name=%s,type=%s,is_free_shipping=%s,regions_json=%s WHERE id=%s",
            (name, body.type, body.is_free_shipping, body.regions_json, template_id),
        )
        await audit.log_action(user.id, "settings", audit.ACTION_EDIT, f"freight:{template_id}", f"编辑运费模板「{name}」")
        return template_id
    tid = await database.execute_return_id(
        "INSERT INTO freight_templates (name,type,is_free_shipping,regions_json,created_by) "
        "VALUES (%s,%s,%s,%s,%s)",
        (name, body.type, body.is_free_shipping, body.regions_json, user.id),
    )
    await audit.log_action(user.id, "settings", audit.ACTION_ADD, f"freight:{tid}", f"新增运费模板「{name}」")
    return tid


async def delete_freight_template(template_id: int, user) -> None:
    row = await database.fetch_one("SELECT id,name FROM freight_templates WHERE id=%s", (template_id,))
    if not row:
        not_found("运费模板不存在")
    used = await database.fetch_one(
        "SELECT COUNT(*) AS c FROM goods WHERE freight_template_id=%s", (template_id,)
    )
    if used and used["c"]:
        referenced("已有商品使用该运费模板，不可删除")
    await database.execute("DELETE FROM freight_templates WHERE id=%s", (template_id,))
    await audit.log_action(user.id, "settings", audit.ACTION_DELETE, f"freight:{template_id}", f"删除运费模板「{row['name']}」")
