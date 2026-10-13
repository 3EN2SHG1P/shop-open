(function (window) {
  'use strict';
  var S = window.ShopUtil, Api = window.ShopApi, U = window.ShopUI;
  function $(id) { return document.getElementById(id); }

  var state = { page: 1 };

  function loadSummary() {
    Api.points().then(function (d) {
      var discount = Number(d.levelDiscountRate || 10);
      $('jsBanner').innerHTML =
        '<div><div class="pt-main">当前可用积分</div>'
        + '<div class="pt-value">' + Number(d.points || 0) + '</div>'
        + '<div class="pt-level">' + S.esc(d.levelName || '普通会员') + ' · 累计消费 ¥' + S.money(d.totalConsume || 0) + ' · 会员折扣 ' + (discount / 10).toFixed(1) + ' 折</div></div>'
        + '<div class="pt-rule">' + S.esc(d.ruleText || '') + '</div>';
    }).catch(function (err) { U.toast((err && err.message) || '加载失败', 'error'); });
  }

  function loadLogs() {
    Api.pointsLogs({ page: state.page }).then(function (data) {
      var list = data.list || [];
      if (!list.length) { $('jsLogs').innerHTML = '<div class="pt-empty">暂无积分流水</div>'; $('jsPager').innerHTML = ''; return; }
      $('jsLogs').innerHTML = list.map(function (l) {
        var sign = l.income ? '+' : '';
        return '<div class="pt-row">'
          + '<span class="pt-reason">' + S.esc(l.reason || '') + '</span>'
          + '<span class="pt-rel">' + (l.relatedId ? ('#' + l.relatedId) : '') + '</span>'
          + '<span class="pt-time">' + String(l.createdAt || '').replace('T', ' ') + '</span>'
          + '<span class="pt-val ' + (l.income ? 'income' : 'outcome') + '">' + sign + l.changeValue + '</span>'
          + '</div>';
      }).join('');
      renderPager(data);
    }).catch(function (err) { U.toast((err && err.message) || '加载失败', 'error'); });
  }

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
      var pg = e.target.closest('.page-num, .page-arrow');
      if (pg && !pg.classList.contains('disabled')) { state.page = Number(pg.getAttribute('data-page')); loadLogs(); window.scrollTo(0, 0); }
    });
  }

  function init() { bindEvents(); loadSummary(); loadLogs(); }
  init();
})(window);
