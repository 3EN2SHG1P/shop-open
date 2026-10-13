/* ============================================
   搜索结果页脚本（specs/商城前台V1.2.spec.md §8.2）
   依赖 ui.js / api.js / auth.js / main.js
   查询串：keyword&categoryId&brandId&minPrice&maxPrice&tag&sort&page
   ============================================ */
(function (window, document) {
  'use strict';

  var S = window.ShopUtil;
  var U = window.ShopUI;
  var $ = function (id) { return document.getElementById(id); };
  var PAGE_SIZE = 20;

  var TAG_OPTS = [
    { key: '', text: '全部商品' },
    { key: 'new', text: '新品首发' },
    { key: 'hot', text: '热销爆款' },
    { key: 'recommend', text: '人气推荐' },
    { key: 'instock', text: '现货抢购' }
  ];

  var PRICE_OPTS = [
    { min: '', max: '', text: '全部价格' },
    { min: 0, max: 999, text: '0 - 999元' },
    { min: 1000, max: 1999, text: '1000 - 1999元' },
    { min: 2000, max: 2999, text: '2000 - 2999元' },
    { min: 3000, max: 4999, text: '3000 - 4999元' },
    { min: 5000, max: '', text: '5000元以上' }
  ];

  var SORT_OPTS = [
    { key: 'default', text: '综合排序' },
    { key: 'sales', text: '销量优先' },
    { key: 'price-asc', text: '价格从低到高' },
    { key: 'price-desc', text: '价格从高到低' },
    { key: 'new', text: '上架时间' }
  ];

  var params = new URLSearchParams(window.location.search);
  var state = {
    keyword: params.get('keyword') || '',
    categoryId: params.get('categoryId') || '',
    brandId: params.get('brandId') || '',
    minPrice: params.get('minPrice') || '',
    maxPrice: params.get('maxPrice') || '',
    tag: TAG_OPTS.some(function (t) { return t.key === params.get('tag'); }) ? params.get('tag') : '',
    sort: SORT_OPTS.some(function (t) { return t.key === params.get('sort'); }) ? params.get('sort') : 'default',
    page: Math.max(1, parseInt(params.get('page'), 10) || 1)
  };

  var tree = [];
  var brands = [];
  var catNameMap = {};
  var catParent = {};
  var loading = false;

  function buildTreeMap(nodes, parentId) {
    nodes.forEach(function (n) {
      catNameMap[n.id] = n.name;
      catParent[n.id] = parentId || null;
      if (n.children && n.children.length) buildTreeMap(n.children, n.id);
    });
  }

  // 当前分类沿父链上溯到一级分类 id（侧栏只表达产品线；深链叶子也高亮其一级）
  function rootIdOf(id) {
    var cur = id != null && id !== '' ? String(id) : '';
    if (!cur || catParent[cur] === undefined) return cur || null;
    while (catParent[cur]) cur = String(catParent[cur]);
    return cur;
  }

  function esc(t) { return S.esc(t); }

  function act() {
    state.page = 1;
    syncUrl();
    load();
  }

  function syncUrl() {
    var q = {
      keyword: state.keyword,
      categoryId: state.categoryId,
      brandId: state.brandId,
      minPrice: state.minPrice,
      maxPrice: state.maxPrice,
      tag: state.tag,
      sort: state.sort === 'default' ? '' : state.sort,
      page: state.page > 1 ? state.page : ''
    };
    var url = window.location.pathname + S.buildQuery(q);
    window.history.replaceState(null, '', url);
  }

  function apiParams() {
    var p = {
      page: state.page,
      page_size: PAGE_SIZE,
      keyword: state.keyword,
      category_id: state.categoryId,
      brand_id: state.brandId,
      min_price: state.minPrice,
      max_price: state.maxPrice
    };
    p.is_new = state.tag === 'new' ? 1 : undefined;
    p.is_hot = state.tag === 'hot' ? 1 : undefined;
    p.is_recommend = state.tag === 'recommend' ? 1 : undefined;
    p.in_stock = state.tag === 'instock' ? true : undefined;
    if (state.sort === 'price-asc') { p.sort_field = 'price'; p.sort_order = 'asc'; }
    else if (state.sort === 'price-desc') { p.sort_field = 'price'; p.sort_order = 'desc'; }
    else if (state.sort === 'sales') { p.sort_field = 'sales'; p.sort_order = 'desc'; }
    else if (state.sort === 'new') { p.sort_field = 'created_at'; p.sort_order = 'desc'; }
    return p;
  }

  function crumbText() {
    if (state.keyword) return '“' + state.keyword + '” 的搜索结果';
    if (state.categoryId && catNameMap[state.categoryId]) {
      var p = catParent[state.categoryId];
      return p && catNameMap[p] ? catNameMap[p] + ' / ' + catNameMap[state.categoryId] : catNameMap[state.categoryId];
    }
    return '全部商品';
  }

  function findNode(nodes, id) {
    for (var i = 0; i < (nodes || []).length; i++) {
      if (String(nodes[i].id) === String(id)) return nodes[i];
      var hit = findNode(nodes[i].children, id);
      if (hit) return hit;
    }
    return null;
  }

  /* ---------- 二级分类横排（产品线页给直属子分类细选入口） ---------- */
  function renderSubCat() {
    var bar = $('jsSubCatBar');
    if (!bar) return;
    if (!state.categoryId) { bar.style.display = 'none'; bar.innerHTML = ''; return; }
    var node = findNode(tree, state.categoryId);
    var group = (node && node.children && node.children.length) ? node : (catParent[state.categoryId] ? findNode(tree, catParent[state.categoryId]) : null);
    if (!group || !group.children || !group.children.length) { bar.style.display = 'none'; bar.innerHTML = ''; return; }
    var html = '<span class="subcat' + (String(state.categoryId) === String(group.id) ? ' active' : '') + '" data-role="subcat" data-id="' + group.id + '">全部</span>';
    group.children.forEach(function (c) {
      html += '<span class="subcat' + (String(state.categoryId) === String(c.id) ? ' active' : '') + '" data-role="subcat" data-id="' + c.id + '">' + esc(c.name) + '</span>';
    });
    bar.innerHTML = html;
    bar.style.display = 'flex';
  }

  /* ---------- 侧栏渲染（只保留 全部商品 + 一级父分类；子分类细选走二级横排） ---------- */
  function catMenuHtml(nodes) {
    var activeRoot = state.categoryId ? rootIdOf(state.categoryId) : '';
    var rows = (nodes || []).map(function (n) {
      var active = activeRoot !== '' && String(n.id) === String(activeRoot);
      return '<div class="cat-menu-item" data-id="' + n.id + '">'
        + '<div class="cat-menu-row' + (active ? ' active' : '') + '" data-role="cat" data-id="' + n.id + '">'
        + '<span class="name">' + esc(n.name) + '</span>'
        + '</div></div>';
    }).join('');
    return '<div class="cat-menu">'
      + '<div class="cat-menu-item" data-id="">'
      + '<div class="cat-menu-row' + (activeRoot === '' ? ' active' : '') + '" data-role="cat" data-id="">'
      + '<span class="name">全部商品</span></div></div>'
      + rows
      + '</div>';
  }

  function renderSidebars() {
    $('jsCatBox').innerHTML = catMenuHtml(tree);
    $('jsBrandBox').innerHTML =
      '<a class="filter-item' + (state.brandId === '' ? ' active' : '') + '" data-role="brand" data-id=""><span>全部品牌</span></a>'
      + brands.map(function (b) {
        return '<a class="filter-item' + (String(state.brandId) === String(b.id) ? ' active' : '') + '" data-role="brand" data-id="' + b.id + '"><span>' + esc(b.name) + '</span></a>';
      }).join('');
    $('jsTagBox').innerHTML = TAG_OPTS.map(function (t) {
      return '<a class="filter-item' + (state.tag === t.key ? ' active' : '') + '" data-role="tag" data-val="' + t.key + '"><span>' + t.text + '</span>'
        + (t.key === state.tag ? '<span class="cnt">×</span>' : '') + '</a>';
    }).join('');
    $('jsPriceBox').innerHTML = PRICE_OPTS.map(function (p) {
      var on = String(state.minPrice) === String(p.min) && String(state.maxPrice) === String(p.max === '' ? '' : p.max);
      return '<a class="filter-item' + (on ? ' active' : '') + '" data-role="price" data-min="' + p.min + '" data-max="' + p.max + '"><span>' + p.text + '</span></a>';
    }).join('');
    $('jsSortBar').innerHTML = SORT_OPTS.map(function (s) {
      return '<span class="sort-option' + (state.sort === s.key ? ' active' : '') + '" data-sort="' + s.key + '">' + s.text + '</span>';
    }).join('');
    renderSubCat();
  }

  /* ---------- 结果渲染 ---------- */
  function itemHtml(g) {
    return '<a class="search-item" href="detail.html?id=' + g.id + '">'
      + '<div class="item-img">' + S.img(g.image, g.name) + '</div>'
      + '<div class="item-name">' + esc(g.name) + '</div>'
      + '<div class="item-desc">' + esc(g.subtitle || '') + '</div>'
      + '<div class="item-price">¥' + S.money(Number(g.price)) + '</div>'
      + '<div class="item-meta"><span class="reviews">已售' + (g.sales || 0) + '件</span>'
      + '<span class="shop">演示商品</span></div></a>';
  }

  function load() {
    if (loading) return;
    loading = true;
    $('jsGrid').innerHTML = '<div class="empty-state"><p class="empty-text">正在加载…</p></div>';
    ShopApi.goods(apiParams()).then(function (res) {
      loading = false;
      var d = res;
      var list = d.list || [];
      renderList(list, d.total);
    }).catch(function () {
      loading = false;
      $('jsGrid').innerHTML = '<div class="empty-state"><p class="empty-text">加载失败，请稍后重试</p></div>';
      U.toast('商品列表加载失败', 'error');
    });
  }

  function renderList(list, total) {
    var grid = $('jsGrid');
    if (!list.length) {
      grid.innerHTML = '<div class="empty-state"><p class="empty-text">未找到相关商品，试试清空筛选条件</p>'
        + '<a class="js-reset-all" href="search.html" style="display:inline-block;padding:6px 18px;border:1px solid var(--primary);border-radius:20px;color:var(--primary);font-size:13px;">查看全部商品</a></div>';
    } else {
      grid.innerHTML = list.map(itemHtml).join('');
    }
    $('jsCrumb').textContent = crumbText();
    var onAll = !state.keyword && !state.categoryId;
    $('jsCrumbAll').style.display = onAll ? 'none' : '';
    $('jsCrumbAllSep').style.display = onAll ? 'none' : '';
    $('jsCount').textContent = '共找到 ' + total + ' 件商品';
    renderPager(total);
  }

  function renderPager(total) {
    var pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
    var pager = $('jsPager');
    if (pages <= 1) { pager.style.display = 'none'; pager.innerHTML = ''; return; }
    var nums = [];
    for (var i = 1; i <= pages; i++) {
      if (pages <= 9 || i === 1 || i === pages || Math.abs(i - state.page) <= 2) {
        nums.push(i);
      } else if (nums[nums.length - 1] !== -1) {
        nums.push(-1);
      }
    }
    var html = '<span class="page-arrow' + (state.page <= 1 ? ' disabled' : '') + '" data-goto="' + (state.page - 1) + '">‹</span>';
    nums.forEach(function (n) {
      if (n === -1) { html += '<span class="page-num more">…</span>'; return; }
      html += '<span class="page-num' + (n === state.page ? ' active' : '') + '" data-goto="' + n + '">' + n + '</span>';
    });
    html += '<span class="page-arrow' + (state.page >= pages ? ' disabled' : '') + '" data-goto="' + (state.page + 1) + '">›</span>';
    pager.innerHTML = html;
    pager.style.display = 'flex';
  }

  /* ---------- 事件 ---------- */
  function bindEvents() {
    document.querySelector('.filter-sidebar').addEventListener('click', function (e) {
      // 侧栏只表达产品线：点任何行（含父分类/全部商品）即选中筛选；子分类细选在二级横排
      var row = e.target.closest('.cat-menu-row');
      if (row) {
        if (row.dataset.role !== 'cat') return;
        var item = row.closest('.cat-menu-item');
        state.categoryId = item.getAttribute('data-id');
        renderSidebars();
        act();
        return;
      }
      var a = e.target.closest('.filter-item');
      if (!a) return;
      var role = a.dataset.role;
      if (role === 'brand') state.brandId = a.dataset.id;
      else if (role === 'price') { state.minPrice = a.dataset.min; state.maxPrice = a.dataset.max; }
      else if (role === 'tag') { state.tag = state.tag === a.dataset.val ? '' : a.dataset.val; }
      renderSidebars();
      act();
    });

    $('jsPriceGo').addEventListener('click', function () {
      state.minPrice = $('jsMin').value.trim();
      state.maxPrice = $('jsMax').value.trim();
      renderSidebars();
      act();
    });

    $('jsSortBar').addEventListener('click', function (e) {
      var span = e.target.closest('.sort-option');
      if (!span) return;
      state.sort = span.dataset.sort;
      renderSidebars();
      act();
    });

    $('jsPager').addEventListener('click', function (e) {
      var n = e.target.closest('[data-goto]');
      if (!n || n.classList.contains('disabled')) return;
      state.page = parseInt(n.dataset.goto, 10);
      syncUrl();
      window.scrollTo(0, 0);
      load();
    });

    document.addEventListener('click', function (e) {
      var sp = e.target.closest ? e.target.closest('.subcat') : null;
      if (sp && sp.dataset.role === 'subcat') {
        state.categoryId = sp.dataset.id;
        renderSidebars();
        act();
        return;
      }
      if (e.target.classList.contains('js-reset-all')) {
        state.page = 1;
        state.keyword = state.categoryId = state.brandId = state.minPrice = state.maxPrice = state.tag = '';
        state.sort = 'default';
        syncUrl();
        renderSidebars();
        load();
      }
    });
  }

  var input = $('jsKeywordInput');
  if (input) input.value = state.keyword;

  Promise.all([ShopApi.categories(), ShopApi.brands()]).then(function (rs) {
    tree = ((rs[0] || {}).list) || [];
    brands = ((rs[1] || {}).list) || [];
    buildTreeMap(tree);
    renderSidebars();
    load();
  }).catch(function () {
    U.toast('筛选条件加载失败', 'error');
    renderSidebars();
    load();
  });

  bindEvents();
})(window, document);
