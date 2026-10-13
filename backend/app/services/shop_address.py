from core import database
from core.errors import bad_request, not_found


async def _address_item(r: dict) -> dict:
    return {
        "id": r["id"],
        "receiverName": r["receiver_name"],
        "receiverPhone": r["receiver_phone"],
        "province": r["province"] or "",
        "city": r["city"] or "",
        "district": r["district"] or "",
        "detail": r["detail"] or "",
        "isDefault": r["is_default"],
    }


async def list_addresses(member_id: int) -> dict:
    rows = await database.fetch_all(
        "SELECT * FROM member_address WHERE member_id=%s ORDER BY is_default DESC,id DESC",
        (member_id,),
    )
    return {"list": [await _address_item(r) for r in rows]}


async def create_address(member_id: int, body: dict) -> int:
    if not str(body.get("receiverPhone") or "").startswith("1"):
        bad_request("手机号格式不正确")
    count = await database.fetch_one(
        "SELECT COUNT(*) AS c FROM member_address WHERE member_id=%s", (member_id,)
    )
    wants_default = body.get("isDefault") in (1, "1", True)
    is_default = 1 if (wants_default or count["c"] == 0) else 0
    aid = await database.execute_return_id(
        "INSERT INTO member_address (member_id,receiver_name,receiver_phone,province,city,district,detail,is_default) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        (member_id, body["receiverName"], body["receiverPhone"], body.get("province", ""),
         body.get("city", ""), body.get("district", ""), body["detail"], is_default),
    )
    if is_default:
        await database.execute(
            "UPDATE member_address SET is_default=0 WHERE member_id=%s AND id<>%s", (member_id, aid)
        )
    return aid


async def update_address(member_id: int, address_id: int, body: dict) -> None:
    row = await database.fetch_one(
        "SELECT * FROM member_address WHERE id=%s AND member_id=%s", (address_id, member_id)
    )
    if not row:
        not_found("地址不存在")
    await database.execute(
        "UPDATE member_address SET receiver_name=%s,receiver_phone=%s,province=%s,city=%s,district=%s,detail=%s "
        "WHERE id=%s",
        (body["receiverName"], body["receiverPhone"], body.get("province", ""),
         body.get("city", ""), body.get("district", ""), body["detail"], address_id),
    )
    if body.get("isDefault") in (1, "1", True):
        await set_default(member_id, address_id)
    elif row["is_default"] and row["is_default"] == 1:
        await database.execute(
            "UPDATE member_address SET is_default=0 WHERE id=%s", (address_id,)
        )


async def set_default(member_id: int, address_id: int) -> None:
    row = await database.fetch_one(
        "SELECT id FROM member_address WHERE id=%s AND member_id=%s", (address_id, member_id)
    )
    if not row:
        not_found("地址不存在")
    await database.execute(
        "UPDATE member_address SET is_default=0 WHERE member_id=%s", (member_id,)
    )
    await database.execute(
        "UPDATE member_address SET is_default=1 WHERE id=%s", (address_id,)
    )


async def delete_address(member_id: int, address_id: int) -> None:
    row = await database.fetch_one(
        "SELECT * FROM member_address WHERE id=%s AND member_id=%s", (address_id, member_id)
    )
    if not row:
        not_found("地址不存在")
    await database.execute("DELETE FROM member_address WHERE id=%s", (address_id,))
    if row["is_default"]:
        remain = await database.fetch_one(
            "SELECT id FROM member_address WHERE member_id=%s ORDER BY id ASC LIMIT 1", (member_id,)
        )
        if remain:
            await database.execute(
                "UPDATE member_address SET is_default=1 WHERE id=%s", (remain["id"],)
            )


async def get_address(member_id: int, address_id: int) -> dict | None:
    row = await database.fetch_one(
        "SELECT * FROM member_address WHERE id=%s AND member_id=%s", (address_id, member_id)
    )
    return await _address_item(row) if row else None


async def get_default_address(member_id: int) -> dict | None:
    row = await database.fetch_one(
        "SELECT * FROM member_address WHERE member_id=%s ORDER BY is_default DESC,id DESC LIMIT 1",
        (member_id,),
    )
    return await _address_item(row) if row else None


async def list_regions(parent_code: str = "") -> dict:
    rows = await database.fetch_all(
        "SELECT code,name,parent_code,level FROM region WHERE status=1 AND parent_code=%s "
        "ORDER BY sort ASC,code ASC",
        (parent_code,),
    )
    return {"list": [
        {"code": r["code"], "name": r["name"], "parentCode": r["parent_code"], "level": r["level"]}
        for r in rows
    ]}
