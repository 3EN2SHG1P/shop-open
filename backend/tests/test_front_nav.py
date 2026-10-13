"""前台分类导航口径固化测试（防止顶层/叶子级映射、二级细选、高亮被改坏）。

口径见 specs/商城前台V1.2.spec.md v1.14 §8.1/§8.2：
- 顶栏主导航项固定映射到它所属的一级分类（产品线入口），不允许落到二级/叶子；
- 列表页当前分类所在产品线对应顶栏项自动高亮；
- 列表页二级子分类横向细选（全部XX + 直属子分类），选中态与两处分类菜单同视觉语言。
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # 项目根
FRONT = os.path.join(ROOT, "front")


def _read(rel):
    with open(os.path.join(FRONT, rel), encoding="utf-8") as f:
        return f.read()


def test_main_nav_maps_to_root_category():
    js = _read(os.path.join("js", "main.js"))
    assert "NAV_ALIAS" in js
    # 必须存在“上溯一级分类”的实现，否则会退化成任意层级匹配
    assert "function rootOf" in js
    assert "function currentRootId" in js
    # 写入 href 用的是根分类 id，并带上点了哪个导航项（供刷新/回退后还原高亮）
    assert "a.setAttribute('href', 'search.html?categoryId=' + root.id + '&nav=' + encodeURIComponent(label))" in js
    # 当前产品线高亮
    assert "classList.add('active')" in js
    assert "a.dataset.catId" in js


def test_nav_highlight_follows_clicked_item():
    """同一产品线存在多入口（手机 / 智能手机）时不许高亮串位：点谁高亮谁。"""
    js = _read(os.path.join("js", "main.js"))
    assert "function navParam" in js
    # 同 root 多入口只保留首个，避免后写入者覆盖前者
    assert "if (!linked[String(root.id)]) linked[String(root.id)] = a;" in js
    # 高亮优先按 URL 记录的 nav 还原，其次回落该产品线的首个入口
    assert "var wanted = navParam();" in js
    assert "if (rid && linked[rid]) target = linked[rid];" in js


def test_search_page_has_subcat_bar():
    html = _read("search.html")
    assert 'id="jsSubCatBar"' in html
    assert ".subcat-bar" in html
    assert ".subcat.active" in html
    # 二级横排选中态=透明底+阴影浮起；父分类选中保留渐变主色
    assert ".subcat.active { background-color:transparent;" in html
    assert "box-shadow:0 2px 4px rgba(30,158,150,.22), 0 4px 12px rgba(0,0,0,.10);" in html
    assert ".subcat:hover:not(.active) { background-color:#EFF9F8; color:var(--primary); }" in html
    assert ".cat-menu-row.active { color:#FFFFFF; background-image:linear-gradient(135deg,var(--primary-active) 0%,var(--primary-deep) 100%);" in html


def test_search_page_renders_subcat_and_binds_click():
    js = _read(os.path.join("js", "page-search.js"))
    assert "function renderSubCat" in js
    assert "function findNode" in js
    assert "renderSubCat();" in js          # renderSidebars 内同步刷新
    assert "data-role=\"subcat\"" in js
    assert "state.categoryId = sp.dataset.id" in js


def test_sidebar_flat_roots_only():
    """侧栏只保留 全部商品+一级父分类：无展开态/箭头/子级树，active 按上溯根判定。"""
    js = _read(os.path.join("js", "page-search.js"))
    html = _read("search.html")
    assert "function rootIdOf" in js
    assert "expandedIds" not in js
    assert "catHasKids" not in js
    assert "expandAncestors" not in js
    assert "cat-menu-arrow" not in js
    assert "cat-menu-arrow" not in html
    assert "cat-menu-children" not in html


def test_nav_active_style_defined():
    css = _read(os.path.join("css", "style.css"))
    assert ".main-nav a.active" in css


def test_service_center_entry_linked():
    """顶栏「服务中心」必须有真实落地页，不能是 href="#" 死链。"""
    for page in ("index.html", "search.html", "detail.html"):
        html = _read(page)
        assert '<a href="service.html">服务中心</a>' in html
    # 全站不得残留「服务中心」死链（顶栏与页脚）
    for name in sorted(os.listdir(FRONT)):
        if name.endswith(".html"):
            assert '<a href="#">服务中心</a>' not in _read(name), name
    svc = _read("service.html")
    assert "自助服务" in svc
    assert 'href="after-sale.html"' in svc
    assert 'href="orders.html"' in svc
    assert 'href="address.html"' in svc


def test_category_name_matches_children():
    """一级分类名不得包含其没有的子分类（名实一致，避免侧栏/flyout 缺项）。"""
    with open(os.path.join(ROOT, "backend", "seed", "demo.py"), encoding="utf-8") as f:
        seed = f.read()
    assert '(10, 0, "笔记本 平板"),' in seed
    assert "笔记本 平板 显示器" not in seed
