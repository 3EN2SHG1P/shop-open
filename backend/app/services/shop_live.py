"""前台实时更新：内容/资源版本指纹（specs/商城前台V1.2.spec.md §9.5）。
- assets 指纹：扫描 config.front_dir 下 html/css/js 的 (相对路径, size, mtime_ns)
- data 指纹：白名单内容表 COUNT(*)+MAX(id)+MAX(updated_at)（无 updated_at 列时自动降级）
- 两级结果合并为一个 version 串，前端轮询发现变化即自动刷新
"""
import hashlib
import time
from pathlib import Path

from core import database
from core.config import config

# 前台可见内容表白名单：内容变更会反映到前台页面
DATA_TABLES = [
    "goods",
    "goods_sku",
    "goods_category",
    "brands",
    "specifications",
    "specification_values",
    "goods_images",
    "goods_comments",
    "ad_positions",
    "ads",
    "notices",
    "articles",
    "article_categories",
    "coupons",
    "seckill_activities",
    "full_discount_activities",
    "group_buy_activities",
]

ASSET_EXTS = (".html", ".css", ".js")

_cache = {"assets": None, "data": None, "ts": 0.0}
_has_upd_cache = {"tables": None, "ts": 0.0}
_CACHE_TTL = 2.0
_PROBE_TTL = 60.0


def _hex(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()[:32]


def _assets_fingerprint() -> dict:
    root = Path(config.front_dir)
    groups = {".css": [], ".html": [], ".js": []}
    if root.is_dir():
        for p in root.rglob("*"):
            if p.is_file():
                ext = p.suffix.lower()
                if ext in groups:
                    st = p.stat()
                    groups[ext].append(
                        f"{p.relative_to(root).as_posix()}|{st.st_size}|{st.st_mtime_ns}"
                    )
    return {
        ext.lstrip("."): _hex("|".join(sorted(v)).encode())
        for ext, v in groups.items()
    }


async def _tables_with_updated() -> set:
    now = time.time()
    if _has_upd_cache["tables"] is None or now - _has_upd_cache["ts"] > _PROBE_TTL:
        placeholders = ",".join(["%s"] * len(DATA_TABLES))
        rows = await database.fetch_all(
            "SELECT TABLE_NAME FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA=%s AND TABLE_NAME IN (" + placeholders + ") AND COLUMN_NAME='updated_at'",
            (config.db_name,) + tuple(DATA_TABLES),
        )
        _has_upd_cache["tables"] = {r["TABLE_NAME"] for r in rows}
        _has_upd_cache["ts"] = now
    return _has_upd_cache["tables"]


async def _data_fingerprint() -> str:
    with_upd = await _tables_with_updated()
    parts = []
    for name in DATA_TABLES:
        has_upd = name in with_upd
        if has_upd:
            row = await database.fetch_one(
                f"SELECT COUNT(*) AS c, COALESCE(MAX(id),0) AS m, COALESCE(MAX(updated_at),'') AS u FROM `{name}`"
            )
        else:
            row = await database.fetch_one(
                f"SELECT COUNT(*) AS c, COALESCE(MAX(id),0) AS m, '' AS u FROM `{name}`"
            )
        parts.append(f"{name}:{row['c']}:{row['m']}:{row['u']}")
    return _hex("|".join(parts).encode())


async def version() -> dict:
    now = time.time()
    if _cache["assets"] is None or _cache["data"] is None or now - _cache["ts"] > _CACHE_TTL:
        assets = _assets_fingerprint()
        data = await _data_fingerprint()
        _cache["assets"] = assets
        _cache["data"] = data
        _cache["ts"] = now
    assets = _cache["assets"]
    data = _cache["data"]
    combined = _hex(f"{assets['css']}|{assets['html']}|{assets['js']}|{data}".encode())
    return {"version": combined, "assets": assets, "data": data}
