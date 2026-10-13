def snake_to_camel(name: str) -> str:
    if "_" not in name:
        return name
    head, *rest = name.split("_")
    return head + "".join(part[:1].upper() + part[1:] for part in rest)


def row_to_camel(row: dict | None) -> dict | None:
    if not row:
        return row
    return {snake_to_camel(k): v for k, v in row.items()}


def rows_to_camel(rows) -> list:
    if not rows:
        return []
    return [row_to_camel(r) for r in rows]


def child_rows(rows: list[dict]) -> dict[int, list[dict]]:
    groups: dict[int, list[dict]] = {}
    for row in rows:
        pid = row.get("parent_id") or 0
        groups.setdefault(pid, []).append(row)
    return groups


def build_tree(rows: list[dict], root_id: int = 0) -> list[dict]:
    groups = child_rows(rows)
    ordered = sorted(rows, key=lambda r: (r.get("sort") if r.get("sort") is not None else 0, r.get("id") or 0))

    def attach(parent_id: int) -> list[dict]:
        nodes = [r for r in ordered if (r.get("parent_id") or 0) == parent_id]
        for node in nodes:
            node["children"] = attach(node["id"])
        return nodes

    return attach(root_id)
