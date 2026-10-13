/* ============================================
   首页脚本（specs/商城前台V1.2.spec.md §8.1）
   依赖 ui.js / api.js / auth.js / main.js
   ============================================ */
(function (window, document) {
  'use strict';

  var S = window.ShopUtil;
  var $ = function (id) { return document.getElementById(id); };
  var U = window.ShopUI;

  function esc(t) { return S.esc(t); }

  /* ---------- 侧栏分类树（一级在左，悬浮时右侧弹出子分类面板） ---------- */
  var CHIP_COLORS = ['#1E9E96', '#2196F3', '#00BCD4', '#8BC34A', '#9C27B0', '#35B5AC', '#E91E63', '#607D8B'];

  function renderCategories(tree) {
    var box = $('jsCatMenu');
    if (!tree || !tree.length) {
      box.innerHTML = '<div class="js-cat-empty">暂无分类</div>';
      return;
    }

    // 逐级摊平，面板内以条目（图标+名称）平铺展示二、三级分类
    function flatten(nodes, out) {
      (nodes || []).forEach(function (n) {
        out.push(n);
        flatten(n.children, out);
      });
    }

    function thumbOf(n) {
      if (n.icon) {
        return '<img class="sub-thumb" src="' + esc(n.icon) + '" alt="">';
      }
      var c = CHIP_COLORS[(n.id || 0) % CHIP_COLORS.length];
      return '<i class="sub-thumb chip" style="background:' + c + '">' + esc(String(n.name || '?').charAt(0)) + '</i>';
    }

    function entryHtml(n) {
      var kids = n.children || [];
      var inner = thumbOf(n) + '<span class="sub-name">' + esc(n.name) + '</span>';
      if (kids.length) return '<span class="sub-entry">' + inner + '</span>';
      return '<a class="sub-entry" href="search.html?categoryId=' + n.id + '">' + inner + '</a>';
    }

    function subHtml(children) {
      if (!children || !children.length) return '';
      var list = [];
      flatten(children, list);
      return '<div class="category-submenu"><div class="sub-body">'
        + list.map(entryHtml).join('')
        + '</div></div>';
    }

    var html = tree.map(function (n) {
      var kids = n.children || [];
      return '<div class="menu-item' + (kids.length ? ' has-children' : '') + '">'
        + (kids.length
          ? '<span class="cat-name">' + esc(n.name) + '</span>'
          : '<a class="cat-name" href="search.html?categoryId=' + n.id + '">' + esc(n.name) + '</a>')
        + (kids.length ? '<span class="arrow">›</span>' : '')
        + subHtml(kids)
        + '</div>';
    }).join('');
    box.innerHTML = html;
    if (window.ShopCategory && window.ShopCategory.init) window.ShopCategory.init();
  }

  /* ---------- 轮播 ---------- */
  var PALETTES = [
    'linear-gradient(120deg,#FCF6EF,#F3E7DC)',
    'linear-gradient(120deg,#EFF5FB,#DCEAF7)',
    'linear-gradient(120deg,#EFF8F0,#D9EFDC)',
    'linear-gradient(120deg,#F6F1FB,#E8DDF4)'
  ];

  function btnOf(link) {
    var h = S.bannerLink(link);
    return h ? '<a class="banner-btn" href="' + esc(h) + '">立即查看</a>' : '';
  }

  function bannerHtml(ads) {
    var out = '';
    if (!ads.length) {
      out += '<div class="banner-slide active" style="' + PALETTES[0] + '">'
        + '<div class="banner-text"><div class="banner-tag">欢迎</div>'
        + '<h2 class="banner-title">随心商城 · 好物随心，品质随行</h2></div></div>';
    } else {
      ads.forEach(function (a, i) {
        var txt = a.text || '欢迎光临 随心商城';
        var cls = 'banner-slide' + (i === 0 ? ' active' : '');
        var bg = PALETTES[i % PALETTES.length];
        if (a.image) {
          out += '<div class="' + cls + '" style="' + bg + '">'
            + '<div class="banner-text"><div class="banner-tag">广告</div>'
            + '<h2 class="banner-title">' + esc(txt) + '</h2>' + btnOf(a.link) + '</div>'
            + '<div class="banner-image">' + S.img(a.image, txt) + '</div></div>';
        } else {
          out += '<div class="' + cls + '" style="' + bg + '">'
            + '<div class="banner-text"><div class="banner-tag">活动</div>'
            + '<h2 class="banner-title">' + esc(txt) + '</h2>' + btnOf(a.link) + '</div></div>';
        }
      });
    }
    var dots = '';
    ads.forEach(function (_, i) {
      dots += '<span class="dot' + (i === 0 ? ' active' : '') + '"></span>';
    });
    return out
      + '<span class="banner-arrow prev">‹</span>'
      + '<span class="banner-arrow next">›</span>'
      + '<div class="banner-dots">' + dots + '</div>';
  }

  function renderBanner(ads) {
    var banner = $('jsBanner');
    var imageAds = ads.filter(function (a) { return a.image; });
    var textAds = ads.filter(function (a) { return !a.image; });
    banner.innerHTML = bannerHtml(imageAds.length ? imageAds : textAds.slice(0, 1));
    window.ShopBanner && window.ShopBanner.init();
    return textAds;
  }

  /* ---------- 中部运营横幅（取文字类广告首条） ---------- */
  function renderPromo(textAds) {
    var box = $('jsPromo');
    if (!textAds.length) return;
    var a = textAds[0];
    var h = S.bannerLink(a.link);
    box.style.display = '';
    box.innerHTML = '<div class="promo-text"><h3>' + esc(a.text || '限时活动') + '</h3>'
      + (h ? '<a class="promo-btn" href="' + esc(h) + '">去看看</a>' : '') + '</div>';
  }

  /* ---------- 公告 ---------- */
  function renderNotice(notices) {
    var box = $('jsNotice');
    if (!notices || !notices.length) {
      if (box) box.style.display = 'none';
      return;
    }
    box.style.display = 'flex';
    box.innerHTML = '<span class="notice-tag">公告</span>'
      + '<span class="notice-title">' + esc(notices[0].title || '') + '</span>';
  }

  /* ---------- 楼层商品 ---------- */
  function productCard(g) {
    return '<a class="product-card" href="detail.html?id=' + g.id + '">'
      + '<div class="product-image">' + S.img(g.image, g.name) + '</div>'
      + '<div class="product-name">' + esc(g.name) + '</div>'
      + (g.subtitle ? '<div class="product-desc">' + esc(g.subtitle) + '</div>' : '')
      + '<div class="product-price price">' + S.money(Number(g.price)) + '<span class="yuan">元起</span></div>'
      + '</a>';
  }

  var FLOORS = [
    { key: 'hot', title: '热销爆款', tag: 'hot' },
    { key: 'newArrival', title: '新品首发', tag: 'new' },
    { key: 'recommend', title: '人气推荐', tag: 'recommend' }
  ];

  function renderFloors(home) {
    var box = $('jsFloors');
    var html = '';
    FLOORS.forEach(function (def) {
      var list = home[def.key] || [];
      if (!list.length) return;
      html += '<div class="category-section">'
        + '<div class="section-header"><h2 class="section-title">' + def.title + '</h2>'
        + '<a class="section-more" href="search.html?tag=' + def.tag + '">查看更多 '
        + '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m9 18 6-6-6-6"/></svg>'
        + '</a></div><div class="product-grid">'
        + list.map(productCard).join('') + '</div></div>';
    });
    box.innerHTML = html || '<div class="empty-hint">暂无在售商品</div>';
  }

  Promise.all([ShopApi.home(), ShopApi.categories()]).then(function (rs) {
    var home = rs[0];
    var tree = ((rs[1] || {}).list) || [];
    renderCategories(tree);
    renderNotice(home.notices || []);
    var textAds = renderBanner(home.banners || []);
    renderPromo(textAds);
    renderFloors(home);
  }).catch(function () {
    $('jsCatMenu').innerHTML = '<div class="js-cat-empty">首页加载失败，请刷新重试</div>';
    U.toast('首页数据加载失败', 'error');
  });
})(window, document);
