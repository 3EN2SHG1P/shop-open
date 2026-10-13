(function (window) {
  'use strict';
  var S = window.ShopUtil, Api = window.ShopApi, U = window.ShopUI;
  function $(id) { return document.getElementById(id); }

  var state = { status: 1, page: 1, available: false };

  function fmtScope(c) {
    if (c.scope === 'all' || !c.scopeIds || !c.scopeIds.length) return '全场通用';
    if (c.scope === 'category') return '指定分类可用';
    if (c.scope === 'goods') return '指定商品可用';
    return '指定范围';
  }
  function fmtTime(t) {
    if (!t) return '—';
    return String(t).replace('T', ' ');
  }
  function leftHtml(c) {
    if (c.type === 2) return '<div class="cp-rate">' + (Number(c.rate) || 0) + '折</div>';
    return '<div class="cp-amount"><span class="y">¥</span>' + S.money(c.amount) + '</div>';
  }

  function cardHtml(c) {
    var cls = c.status === 2 ? ' used' : (c.status === 3 ? ' expired' : '');
    var tag = c.status === 2 ? '已使用' : (c.status === 3 ? '已过期' : '');
    var getBtn = state.available ? '<button class="cp-get" data-id="' + c.id + '"' + (c.received ? ' disabled' : '') + '>' + (c.received ? '已领取' : '立即领取') + '</button>' : '';
    return '<div class="cp-card' + cls + '">'
      + '<div class="cp-left">' + leftHtml(c) + '<div class="cp-cond">' + (c.type === 2 ? '' : ('满' + S.money(c.minAmount) + '可用')) + '</div></div>'
      + '<div class="cp-right"><div class="cp-name">' + S.esc(c.name) + '</div>'
      + '<div class="cp-scope">' + fmtScope(c) + '</div>'
      + '<div class="cp-time">' + fmtTime(c.startTime) + ' ~ ' + fmtTime(c.endTime) + '</div>'
      + getBtn + '</div>'
      + (tag ? '<span class="cp-tag">' + tag + '</span>' : '')
      + '</div>';
  }

  function loadMine() {
    state.available = false;
    Api.coupons.mine({ status: state.status, page: state.page }).then(function (data) {
      var list = data.list || [];
      if (!list.length) { $('jsList').innerHTML = '<div class="cp-empty">暂无' + tabText(state.status) + '的优惠券</div>'; $('jsPager').innerHTML = ''; return; }
      $('jsList').innerHTML = list.map(cardHtml).join('');
      renderPager(data);
    }).catch(function (err) { U.toast((err && err.message) || '加载失败', 'error'); });
  }

  function loadAvailable() {
    state.available = true;
    Api.coupons.available().then(function (data) {
      var list = data.list || [];
      if (!list.length) { $('jsList').innerHTML = '<div class="cp-empty">暂无可领取的优惠券</div>'; $('jsPager').innerHTML = ''; return; }
      $('jsList').innerHTML = list.map(cardHtml).join('');
      $('jsPager').innerHTML = '';
    }).catch(function (err) { U.toast((err && err.message) || '加载失败', 'error'); });
  }

  function tabText(s) { return s === 2 ? '已使用' : (s === 3 ? '已过期' : '未使用'); }

  function renderPager(data) {
    var total = data.total || 0, pageSize = data.page_size || 10, cur = data.page || 1;
    var pages = Math.ceil(total / pageSize) || 1;
    if (pages <= 1) { $('jsPager').innerHTML = ''; return; }
    var html = '';
    if (cur > 1) html += '<span class="page-arrow" data-page="' + (cur - 1) + '">‹</span>';
    for (var i = 1; i <= pages; i++) html += '<span class="page-num' + (i === cur ? ' active' : '') + '" data-page="' + i + '">' + i + '</span>';
    if (cur < pages) html += '<span class="page-arrow" data-page="' + (cur + 1) + '">›</span>';
    $('jsPager').innerHTML = html;
  }

  function bindEvents() {
    document.addEventListener('click', function (e) {
      var tab = e.target.closest('.cp-tab');
      if (tab) {
        state.status = Number(tab.getAttribute('data-status')); state.page = 1; state.available = false;
        Array.prototype.forEach.call($('jsTabs').querySelectorAll('.cp-tab'), function (t) { t.classList.toggle('active', t === tab); });
        loadMine(); return;
      }
      var pg = e.target.closest('.page-num, .page-arrow');
      if (pg && !pg.classList.contains('disabled')) { state.page = Number(pg.getAttribute('data-page')); loadMine(); window.scrollTo(0, 0); return; }
      if (e.target.closest('#jsGetEntry')) {
        if (state.available) { state.available = false; state.page = 1; loadMine(); }
        else { loadAvailable(); }
        return;
      }
      var gb = e.target.closest('.cp-get');
      if (gb && !gb.disabled) {
        var id = Number(gb.getAttribute('data-id'));
        U.busy(gb, function () {
          return Api.coupons.receive(id).then(function () {
            U.toast('领取成功', 'success'); loadAvailable();
          }).catch(function (err) { U.toast((err && err.message) || '领取失败', 'error'); throw err; });
        });
        return;
      }
    });
  }

  function init() {
    bindEvents();
    loadMine();
  }
  init();
})(window);
