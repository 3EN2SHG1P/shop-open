import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
APP_DIR = BACKEND_DIR / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))
# backend 根也要入 path：test_seed_demo 等需要 import seed 包（seed/ 与 app/ 平级）
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pytest
from fastapi.testclient import TestClient

from core.deps import clear_permission_cache


@pytest.fixture(scope="session")
def client():
    import main

    with TestClient(main.app) as c:
        yield c
    clear_permission_cache()


@pytest.fixture(scope="session")
def admin_password():
    """管理员口令：必须由环境变量显式提供，不做任何默认值兜底。

    这样仓库里不会出现任何「可用弱口令」。未设置时相关用例 skip，
    而不是拿一个猜来的密码去撞库——后者会掩盖「本机还没 seed」这类真实问题。
    本地用法：backend/.env 里设置 ADMIN_INIT_PASSWORD 后执行 `python -m seed.runner base`。
    """
    pwd = os.getenv("ADMIN_INIT_PASSWORD", "").strip()
    if not pwd:
        pytest.skip(
            "未设置 ADMIN_INIT_PASSWORD：请在 backend/.env 中设置一个本机测试口令 "
            "（ADMIN_INIT_PASSWORD=<你的口令>）并执行 `uv run python -m seed.runner base` 后重跑测试"
        )
    return pwd


@pytest.fixture(scope="session")
def admin_token(client, admin_password):
    """登录取 token。

    失败必须是 skip 而不是 assert 失败：一旦这里硬失败，session 级 fixture 会级联成几十条
    ERROR，报错信息还完全看不出真正原因（口令不匹配 / admin 没建 / 被锁定）。
    这里给出可直接照做的修复步骤。
    """
    r = client.post("/api/v1/auth/login", json={"username": "admin", "password": admin_password})
    if r.status_code != 200 or r.json().get("code") != 0:
        pytest.skip(
            f"用 ADMIN_INIT_PASSWORD 登录 admin 失败（响应：{(r.json() or {}).get('message', r.text[:200])}）。\n"
            "常见原因：seed base 只在 admin **首次创建** 时使用该口令，账号已存在则不会重置密码。\n"
            "修复二选一：\n"
            "  1) 删掉 admin 后重跑 base：DELETE FROM admin_users WHERE username='admin'; "
            "然后 uv run python -m seed.runner base\n"
            "  2) 把 backend/.env 的 ADMIN_INIT_PASSWORD 改成你本机 admin 的当前口令"
        )
    return r.json()["data"]["token"]


@pytest.fixture(scope="session")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}
