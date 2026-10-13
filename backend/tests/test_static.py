import glob
import os
import re

import pytest


def test_manager_login_page_served(client):
    resp = client.get("/manager/login.html")
    assert resp.status_code == 200
    assert "商城后台管理系统" in resp.text


def test_manager_dashboard_assets_served(client):
    resp = client.get("/manager/js/common.js")
    assert resp.status_code == 200
    assert "mall_admin_session" in resp.text


def test_front_not_served_by_backend(client):
    resp = client.get("/front/index.html")
    assert resp.status_code == 404


def test_root_redirects_to_manager_login(client):
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code in (301, 302, 307, 308)
    assert "/manager/login.html" in resp.headers.get("location", "")


def test_api_docs_still_available(client):
    resp = client.get("/api/docs")
    assert resp.status_code == 200


@pytest.fixture
def manager_pages():
    # tests/ → backend/ → 仓库根（manager/ 在仓库根，不在 backend/ 下）
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    pattern = os.path.join(repo_root, "manager", "**", "*.html")
    pages = glob.glob(pattern, recursive=True)
    # 路径一旦算错会静默空跑（历史 bug），这里显式兜底，避免"零文件 = 永远通过"
    assert pages, f"未扫描到任何 manager 页面，请检查路径：{pattern}"
    return pages


MODAL_OVERLAY_RE = re.compile(
    r'<div\b[^>]*class="([^"]*\bmodal-overlay\b[^"]*)"[^>]*id="([^"]+)"', re.I
)
DRAWER_OVERLAY_RE = re.compile(
    r'<div\b[^>]*class="([^"]*\bdrawer-overlay\b[^"]*)"[^>]*id="([^"]+)"', re.I
)
OPEN_MODAL_RE = re.compile(r"\.openModal\(\s*['\"]([^'\"]+)['\"]\s*\)")
OPEN_DRAWER_RE = re.compile(r"\.openDrawer\(\s*['\"]([^'\"]+)['\"]\s*\)")


def _audit_manager_ui(path):
    text = open(path, encoding="utf-8").read()
    rel = os.path.relpath(path, os.path.dirname(os.path.dirname(__file__)))
    issues = []

    ids = re.findall(r'\bid="([^"]+)"', text)
    for dup in sorted({i for i in ids if ids.count(i) > 1}):
        issues.append(f"{rel}: 页面存在重复 id #{dup}")

    modals = []
    for m in MODAL_OVERLAY_RE.finditer(text):
        modals.append((m.group(2), m.start()))
    modal_ids = {mid for mid, _ in modals}

    for mid, start in modals:
        end = next((s for _, s in modals if s > start), len(text))
        block = text[start:end]
        close_x = "modal-close" in block
        close_data = re.search(rf'data-close-modal="{re.escape(mid)}"', block) is not None
        if not (close_x or close_data):
            issues.append(f"{rel}: 弹窗 #{mid} 无任何关闭途径（✕/取消/data-close-modal）")

    for ref in OPEN_MODAL_RE.findall(text):
        if ref not in modal_ids:
            issues.append(f"{rel}: openModal 引用不存在的弹窗 #{ref}")

    for btn_m in re.finditer(
        r'<button\b[^>]*onclick="([^"]*openModal\([^)]*\)[^"]*)"[^>]*>[^<]*(?:新增|编辑)[^<]*</button>',
        text,
        re.I,
    ):
        onclick = btn_m.group(1)
        ref = re.search(r"openModal\(\s*['\"]([^'\"]+)['\"]\s*\)", onclick)
        if not ref:
            continue
        mid = ref.group(1)
        if mid not in modal_ids:
            continue
        start = next((s for m2, s in modals if m2 == mid), None)
        if start is None:
            continue
        end = next((s for _, s in modals if s > start), len(text))
        block = text[start:end]
        has_cancel = re.search(
            r'<button\b[^>]*data-close-modal=["\']' + re.escape(mid) + r'["\'][^>]*>[^<]*取消</button>',
            block,
            re.I,
        )
        has_x = "modal-close" in block
        if not (has_cancel and has_x):
            issues.append(f"{rel}: 新增/编辑弹窗 #{mid} 需同时具备 ✕ 与「取消」")

    drawers = []
    for m in DRAWER_OVERLAY_RE.finditer(text):
        drawers.append((m.group(2), m.start()))
    for did_overlay, _ in drawers:
        if not did_overlay.endswith("-overlay"):
            continue
        base = did_overlay[: -len("-overlay")]
        if base not in ids:
            issues.append(f"{rel}: 抽屉遮罩 #{did_overlay} 缺本体 #{base}")
            continue
        has_close = re.search(
            rf'data-close-drawer="\s*{re.escape(base)}\s*"', text
        ) is not None
        if not has_close:
            issues.append(f"{rel}: 抽屉 #{base} 缺 data-close-drawer 关闭钮")
    for ref in OPEN_DRAWER_RE.findall(text):
        if ref not in ids or (ref + "-overlay") not in ids:
            issues.append(f"{rel}: openDrawer 引用不存在的抽屉 #{ref}")

    for dm in re.finditer(r'data-close-drawer="([^"]+)"', text):
        if dm.group(1) + "-overlay" not in ids:
            issues.append(f"{rel}: data-close-drawer 目标 #{dm.group(1)} 不存在")

    return issues


def test_manager_modals_drawers_well_formed(manager_pages):
    """全量审计 manager 页面的弹窗/抽屉结构：引用存在、可关闭、无重复 id，防 SPA 换页后同类失效。"""
    issues = []
    for path in manager_pages:
        issues.extend(_audit_manager_ui(path))
    assert not issues, "\n".join(issues)
