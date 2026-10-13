/* ============================================
   我的订单 orders.html（specs/商城前台V1.2.spec.md §8.12）
   - 会员资产快捷条：GET /points 积分摘要 + coupons/points/after-sale 入口（S6 新增页）
   - ?tab= → GET /orders?status= 分页渲染，tab 角标用接口返回的 orderStatusCounts
   - 订单卡按后端 actions 渲染操作按钮；状态变更 toast + 局部刷新
   依赖：ui.js / api.js / auth.js
   ============================================ */
(function (window, document) {
  'use strict';

  var U = window.ShopUI;
  var Api = window.ShopApi;
  var A = window.ShopAuth;
  var S = window.ShopUtil;

  var PAGE_SIZE = 10;

  var TABS = [
    { key: 'all', status: 0, label: '全部订单' },
    { key: 'pending', status: 1, label: '待付款' },
    { key: 'unshipped', status: 2, label: '待发货' },
    { key: 'shipped', status: 3, label: '待收货' },
    { key: 'completed', status: 4, label: '已完成' },
    { key: 'cancelled', status: 5, label: '已取消' },
    { key: 'aftersale', status: 6, label: '售后中' }
  ];

  var STATUS_CLASS = { 1: 'pending', 2: 'shipping', 3: 'shipping', 4: 'completed', 5: 'cancelled', 6: 'aftersale' };

  var state = { tab: 'all', status: 0, page: 1, counts: null };

  function $(id) { return document.getElementById(id); }
  function esc(t) { return S.esc(t); }
  function money(n) { return S.money(Number(n) || 0); }

  /* ---------- 会员资产快捷条 ---------- */
  function loadPoints() {
    var box = $('jsAssetPoints');
    if (!box) return;
    Api.points().then(function (data) {
      box.textContent = String(data.points || 0);
    }).catch(function () {});
  }

  /* ---------- tab ---------- */
  function tabByKey(key) {
    for (var i = 0; i < TABS.length; i++) if (TABS[i].key === key) return TABS[i];
    return TABS[0];
  }

  function renderTabs() {
    var nav = $('jsTabs');
    if (!nav) return;
    nav.innerHTML = TABS.map(function (t) {
      var cnt = state.counts ? (state.counts[String(t.status)] || 0) : 0;
      var label = t.label + (cnt > 0 ? '<span class="tab-count">(' + cnt + ')</span>' : '');
      return '<div class="order-tab' + (t.key === state.tab ? ' active' : '') + '" data-tab="' + t.key + '">' + label + '</div>';
    }).join('');
  }

  /* ---------- 订单卡 ---------- */
  function actionHtml(actions, orderNo) {
    if (!actions || !actions.length) return '';
    var html = [];
    actions.forEach(function (act) {
      var no = esc(orderNo);
      if (act === 'pay') {
        html.push('<a class="order-btn order-btn-primary" href="payment.html?orderNo=' + encodeURIComponent(orderNo) + '">立即付款</a>');
      } else if (act === 'cancel') {
        html.push('<button class="order-btn order-btn-outline" data-act="cancel" data-no="' + no + '">取消订单</button>');
      } else if (act === 'remindShip') {
        html.push('<button class="order-btn order-btn-outline" data-act="remind">提醒发货</button>');
      } else if (act === 'confirm') {
        html.push('<button class="order-btn order-btn-primary" data-act="confirm" data-no="' + no + '">确认收货</button>');
      } else if (act === 'logistics') {
        html.push('<button class="order-btn order-btn-outline" data-act="logistics" data-no="' + no + '">查看物流</button>');
      } else if (act === 'afterSale') {
        html.push('<a class="order-btn order-btn-outline" href="after-sale.html?view=apply&orderId=' + encodeURIComponent(orderNo) + '">申请售后</a>');
      } else if (act === 'again') {
        html.push('<button class="order-btn order-btn-outline" data-act="again" data-no="' + no + '">再次购买</button>');
      } else if (act === 'viewAfterSale') {
        html.push('<a class="order-btn order-btn-outline" href="after-sale.html">查看售后</a>');
      } else if (act === 'review') {
        html.push('<button class="order-btn order-btn-outline" data-act="review" data-no="' + no + '">评价</button>');
      }
    });
    return html.join('');
  }

  function cardHtml(o) {
    var cls = STATUS_CLASS[o.orderStatus] || 'pending';
    var acts = (o.actions || []).slice();
    if (Number(o.orderStatus) === 4 && acts.indexOf('review') < 0) acts.push('review');
    var products = '<div class="order-product">'
      + S.img(o.goodsImage, o.goodsName)
      + '<div class="op-info"><div class="op-name">' + esc(o.goodsName) + '</div>'
      + '<div class="op-spec">共 ' + (o.totalQuantity || 0) + ' 件</div></div></div>';
    if (Number(o.goodsCount) > 1) {
      products += '<div class="order-more">共' + o.goodsCount + '件</div>';
    }
    return '<div class="order-card" data-order-no="' + esc(o.orderNo) + '">'
      + '<div class="order-card-header">'
      + '<span class="order-time">' + esc(o.createdAt || '') + '</span>'
      + '<span class="order-no">订单号：<span>' + esc(o.orderNo) + '</span></span>'
      + '<span class="order-status status-' + cls + '">' + esc(o.orderStatusText) + '</span>'
      + '</div>'
      + '<div class="order-card-body">'
      + '<div class="order-products">' + products + '</div>'
      + '<div class="order-amount"><div class="amount-label">实付金额</div>'
      + '<div class="amount-value"><span class="yuan">¥</span>' + money(o.payAmount) + '</div></div>'
      + '<div class="order-actions">' + actionHtml(acts, o.orderNo) + '</div>'
      + '</div></div>';
  }

  function renderList(data) {
    var box = $('jsOrderList');
    if (!box) return;
    var list = (data && data.list) || [];
    if (!list.length) {
      box.innerHTML = '<div class="empty-orders"><div class="empty-icon">📦</div>'
        + '<div class="empty-text">暂无相关订单</div>'
        + '<a class="empty-btn" href="index.html">去逛逛</a></div>';
      renderPager(0, 1);
      return;
    }
    box.innerHTML = list.map(cardHtml).join('');
    renderPager(data.total || 0, data.page || 1);
  }

  function renderPager(total, page) {
    var el = $('jsPager');
    if (!el) return;
    var pages = Math.ceil(total / PAGE_SIZE);
    if (pages <= 1) { el.innerHTML = ''; return; }
    var html = '<span class="page-arrow' + (page <= 1 ? ' disabled' : '') + '" data-page="' + (page - 1) + '">‹</span>';
    for (var i = 1; i <= pages; i++) {
      html += '<span class="page-num' + (i === page ? ' active' : '') + '" data-page="' + i + '">' + i + '</span>';
    }
    html += '<span class="page-arrow' + (page >= pages ? ' disabled' : '') + '" data-page="' + (page + 1) + '">›</span>';
    el.innerHTML = html;
  }

  /* ---------- 加载 ---------- */
  function loadOrders() {
    Api.orders({ status: state.status, page: state.page, page_size: PAGE_SIZE }).then(function (data) {
      state.counts = data.orderStatusCounts || null;
      renderTabs();
      renderList(data);
    }).catch(function (err) {
      U.toast((err && err.message) || '订单加载失败', 'error');
    });
  }

  /* ---------- 物流弹层 ---------- */
  function showLogistics(orderNo) {
    Api.logistics(orderNo).then(function (data) {
      $('jsLogiCompany').textContent = data.logisticsCompany || '—';
      $('jsLogiNo').textContent = data.logisticsNo || '—';
      $('jsLogiTime').textContent = data.shippedAt ? String(data.shippedAt) : '—';
      $('jsLogisticsModal').style.display = 'block';
    }).catch(function (err) {
      U.toast((err && err.message) || '暂无物流信息', 'warn');
    });
  }

  /* ---------- 评价弹层（spec §10 规则 10） ---------- */
  function renderReviewItem(item) {
    var gid = item.goodsId || item.goods_id;
    var stars = '<div class="rm-stars" data-goods="' + gid + '">'
      + '<span data-score="1">★</span><span data-score="2">★</span><span data-score="3">★</span>'
      + '<span data-score="4">★</span><span data-score="5">★</span></div>';
    return '<div class="rm-item" data-goods="' + gid + '">'
      + S.img(item.goodsImage, item.goodsName)
      + '<div class="rm-info"><div class="rm-name">' + esc(item.goodsName) + '</div>'
      + stars
      + '<textarea class="rm-text" placeholder="说说使用感受（10~200字）" maxlength="200"></textarea>'
      + '<button class="rm-submit" data-goods="' + gid + '">提交评价</button></div></div>';
  }

  function openReview(orderNo) {
    Api.orderDetail(orderNo).then(function (detail) {
      var items = detail.items || detail.orderItems || detail.order_items || [];
      if (!items.length) { U.toast('订单无商品可评价', 'warn'); return; }
      $('jsReviewItems').innerHTML = items.map(renderReviewItem).join('');
      $('jsReviewModal').style.display = 'block';
    }).catch(function (err) {
      U.toast((err && err.message) || '订单加载失败', 'error');
    });
  }

  function submitReview(gid, rowEl) {
    var score = Number(rowEl.querySelector('.rm-stars').getAttribute('data-score') || '0');
    var content = rowEl.querySelector('.rm-text').value.trim();
    if (score < 1 || score > 5) { U.toast('请先打分（1~5 星）', 'warn'); return; }
    if (content.length < 10) { U.toast('评价内容至少 10 字', 'warn'); return; }
    var btn = rowEl.querySelector('.rm-submit');
    U.busy(btn, function () {
      return Api.addComment(gid, score, content).then(function () {
        U.toast('评价已提交，待商家审核后展示', 'success');
        rowEl.classList.add('rm-done');
      }).catch(function (err) {
        var code = err && err.code;
        if (code === 3002) { U.toast('该商品已评价过', 'warn'); rowEl.classList.add('rm-done'); return; }
        U.toast((err && err.message) || '评价失败', 'error');
        throw err;
      });
    });
  }

  /* ---------- 操作 ---------- */
  function handleAct(act, orderNo) {
    if (act === 'review') { openReview(orderNo); return; }
    if (act === 'remind') { U.toast('已提醒商家尽快发货（演示）', 'success'); return; }
    if (act === 'logistics') { showLogistics(orderNo); return; }
    if (act === 'cancel') {
      if (!window.confirm('确定取消该订单？')) return;
      Api.cancelOrder(orderNo).then(function () {
        U.toast('订单已取消', 'success'); loadOrders();
      }).catch(function (err) { U.toast((err && err.message) || '取消失败', 'error'); });
      return;
    }
    if (act === 'confirm') {
      if (!window.confirm('确认已收到商品？')) return;
      Api.confirmReceipt(orderNo).then(function () {
        U.toast('已确认收货', 'success'); loadOrders();
      }).catch(function (err) { U.toast((err && err.message) || '操作失败', 'error'); });
      return;
    }
    if (act === 'again') {
      Api.buyAgain(orderNo).then(function () {
        U.toast('已加入购物车', 'success');
        A.refreshCartBadge();
      }).catch(function (err) { U.toast((err && err.message) || '操作失败', 'error'); });
    }
  }

  /* ---------- 事件 ---------- */
  function bindEvents() {
    document.addEventListener('click', function (e) {
      var tab = e.target.closest('.order-tab');
      if (tab) {
        state.tab = tab.getAttribute('data-tab');
        var t = tabByKey(state.tab);
        state.status = t.status;
        state.page = 1;
        renderTabs();
        loadOrders();
        return;
      }
      var pg = e.target.closest('.page-num, .page-arrow');
      if (pg && !pg.classList.contains('disabled')) {
        var p = Number(pg.getAttribute('data-page'));
        if (p >= 1) { state.page = p; loadOrders(); window.scrollTo(0, 0); }
        return;
      }
      var actEl = e.target.closest('[data-act]');
      if (actEl) { handleAct(actEl.getAttribute('data-act'), actEl.getAttribute('data-no')); return; }
      var star = e.target.closest('.rm-stars span');
      if (star) {
        var sc = Number(star.getAttribute('data-score'));
        var box = star.closest('.rm-stars');
        box.setAttribute('data-score', String(sc));
        Array.prototype.forEach.call(box.children, function (s, i) {
          s.classList.toggle('on', i < sc);
        });
        return;
      }
      var submitBtn = e.target.closest('.rm-submit');
      if (submitBtn) {
        var row = submitBtn.closest('.rm-item');
        submitReview(Number(submitBtn.getAttribute('data-goods')), row);
        return;
      }
      if (e.target.closest('#jsReviewClose') || e.target === $('jsReviewModal')) {
        $('jsReviewModal').style.display = 'none';
        return;
      }
      if (e.target.closest('#jsLogiClose') || e.target === $('jsLogisticsModal')) {
        $('jsLogisticsModal').style.display = 'none';
        return;
      }
    });
  }

  function init() {
    var q = new URLSearchParams(window.location.search);
    var t = tabByKey(q.get('tab') || 'all');
    state.tab = t.key; state.status = t.status; state.page = 1;
    bindEvents();
    loadPoints();
    loadOrders();
  }

  init();
})(window, document);
