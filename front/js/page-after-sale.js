(function (window) {
  'use strict';
  var S = window.ShopUtil, Api = window.ShopApi, U = window.ShopUI;
  function $(id) { return document.getElementById(id); }
  function qs(p) { var s = []; Object.keys(p || {}).forEach(function (k) { if (p[k] !== undefined && p[k] !== null && p[k] !== '') s.push(k + '=' + encodeURIComponent(p[k])); }); return s.length ? '?' + s.join('&') : ''; }

  var STATUS_TEXT = { 1: '待审核', 2: '处理中', 3: '已完成', 4: '已拒绝' };
  var TYPE_TEXT = { 1: '仅退款', 2: '退货退款' };
  var state = { view: 'list', status: null, page: 1, detail: null, order: null };

  function showView(v) {
    state.view = v;
    $('jsListView').style.display = v === 'list' ? 'block' : 'none';
    $('jsApplyView').style.display = v === 'apply' ? 'block' : 'none';
    $('jsDetailView').style.display = v === 'detail' ? 'block' : 'none';
    $('jsBack').style.display = v === 'list' ? 'none' : 'inline-block';
  }

  /* ---------- 列表 ---------- */
  function renderTabs() {
    var tabs = [
      { k: '', t: '全部' }, { k: 1, t: '待审核' }, { k: 2, t: '处理中' }, { k: 3, t: '已完成' }, { k: 4, t: '已拒绝' }
    ];
    $('jsTabs').innerHTML = tabs.map(function (x) {
      var act = (state.status === x.k || (state.status === null && x.k === '')) ? ' active' : '';
      return '<div class="as-tab' + act + '" data-status="' + x.k + '">' + x.t + '</div>';
    }).join('');
  }

  function loadList() {
    showView('list');
    renderTabs();
    Api.afterSales.list({ status: state.status, page: state.page }).then(function (data) {
      var list = data.list || [];
      if (!list.length) {
        $('jsList').innerHTML = '<div class="empty-orders"><div class="empty-icon">🛠️</div><div class="empty-text">暂无售后申请</div><a class="empty-btn" href="orders.html">去我的订单</a></div>';
        $('jsPager').innerHTML = '';
        return;
      }
      $('jsList').innerHTML = list.map(cardHtml).join('');
      renderPager(data);
    }).catch(function (err) { U.toast((err && err.message) || '加载失败', 'error'); });
  }

  function cardHtml(o) {
    var st = STATUS_TEXT[o.status] || '';
    var cls = 'status-' + o.status;
    var actions = '';
    if (o.status === 1) actions += '<button class="as-btn as-btn-outline" data-act="cancel" data-id="' + o.id + '">撤销</button>';
    if (o.type === 2 && o.status === 2 && !o.returnLogisticsNo) actions += '<button class="as-btn as-btn-outline" data-act="logi" data-id="' + o.id + '">填退货运单</button>';
    actions += '<a class="as-btn-text" href="after-sale.html?view=detail&id=' + o.id + '">查看详情</a>';
    return '<div class="as-card" data-id="' + o.id + '">'
      + '<div class="as-card-header"><span class="as-no">售后单：' + S.esc(o.afterSaleNo || '') + '</span>'
      + '<span class="as-status ' + cls + '">' + st + '</span></div>'
      + '<div class="as-body">' + S.img(o.goodsImage, o.goodsName)
      + '<div class="as-info"><div class="as-name">' + S.esc(o.goodsName) + '</div>'
      + '<div class="as-meta">' + (TYPE_TEXT[o.type] || '') + ' · ' + S.esc(o.reason || '') + '</div></div>'
      + '<div class="as-amount">¥' + S.money(o.amount) + '</div>'
      + '<div class="as-actions">' + actions + '</div></div>'
      + (o.handleNote ? '<div class="as-handle">处理说明：' + S.esc(o.handleNote) + '</div>' : '')
      + '</div>';
  }

  function renderPager(data) {
    var total = data.total || 0, pageSize = data.page_size || 10, cur = data.page || 1;
    var pages = Math.ceil(total / pageSize) || 1;
    if (pages <= 1) { $('jsPager').innerHTML = ''; return; }
    var html = '';
    if (cur > 1) html += '<span class="page-arrow" data-page="' + (cur - 1) + '">‹</span>';
    for (var i = 1; i <= pages; i++) {
      html += '<span class="page-num' + (i === cur ? ' active' : '') + '" data-page="' + i + '">' + i + '</span>';
    }
    if (cur < pages) html += '<span class="page-arrow" data-page="' + (cur + 1) + '">›</span>';
    $('jsPager').innerHTML = html;
  }

  /* ---------- 申请 ---------- */
  function loadApply(orderId) {
    showView('apply');
    Api.orderDetail(orderId).then(function (d) {
      state.order = d;
      var max = Number(d.payAmount || 0);
      var os = Number(d.orderStatus);
      // 2 待发货仅 type=1；3/4 可选 1/2
      var canRefundOnly = os === 2 || os === 3 || os === 4;
      var canReturn = os === 3 || os === 4;
      var html = '<h3>发起售后 · 订单 ' + S.esc(d.orderNo || '') + '</h3>'
        + '<div class="as-field"><label>售后类型</label><div class="as-types">'
        + '<div class="as-type' + (canRefundOnly ? '' : ' disabled') + '" data-type="1">仅退款</div>'
        + '<div class="as-type' + (canReturn ? '' : ' disabled') + '" data-type="2">退货退款</div>'
        + '</div><div class="as-hint">仅退款：退款不退货；退货退款：寄回商品后退款（按 §10 规则 8 边界）</div></div>'
        + '<div class="as-field"><label>退款金额（元，不可超过 ¥' + S.money(max) + '）</label>'
        + '<input class="as-input" id="jsAsAmount" type="number" step="0.01" value="' + max + '" max="' + max + '"></div>'
        + '<div class="as-field"><label>售后原因</label><textarea class="as-textarea" id="jsAsReason" placeholder="请描述售后原因（10~200字）"></textarea></div>'
        + '<button class="as-submit" id="jsAsSubmit">提交申请</button>';
      $('jsApplyForm').innerHTML = html;
      var type = canReturn ? 2 : 1;
      setType(type);
    }).catch(function (err) { U.toast((err && err.message) || '订单加载失败', 'error'); showView('list'); });
  }

  function setType(t) {
    state.applyType = t;
    Array.prototype.forEach.call($('jsApplyForm').querySelectorAll('.as-type'), function (el) {
      var v = Number(el.getAttribute('data-type'));
      el.classList.toggle('active', v === t && !el.classList.contains('disabled'));
    });
  }

  function submitApply() {
    if (!state.order) return;
    var type = state.applyType;
    if (!type) { U.toast('请选择售后类型', 'warn'); return; }
    var reason = $('jsAsReason').value.trim();
    if (reason.length < 10) { U.toast('售后原因至少 10 字', 'warn'); return; }
    var max = Number(state.order.payAmount || 0);
    var amount = Number($('jsAsAmount').value);
    if (!(amount > 0) || amount > max + 0.001) { U.toast('退款金额需在 0~¥' + S.money(max) + ' 之间', 'warn'); return; }
    var btn = $('jsAsSubmit');
    U.busy(btn, function () {
      return Api.afterSales.apply({ orderId: state.order.id, type: type, reason: reason, amount: amount }).then(function () {
        U.toast('售后申请已提交', 'success');
        state.status = null; state.page = 1;
        loadList();
      }).catch(function (err) {
        U.toast((err && err.message) || '提交失败', 'error');
        throw err;
      });
    });
  }

  /* ---------- 详情 ---------- */
  function loadDetail(id) {
    showView('detail');
    Api.afterSales.detail(id).then(function (d) {
      state.detail = d;
      var rows = [
        ['售后单号', d.afterSaleNo || ''],
        ['类型', TYPE_TEXT[d.type] || ''],
        ['状态', STATUS_TEXT[d.status] || ''],
        ['退款金额', '¥' + S.money(d.amount)],
        ['原因', d.reason || ''],
        ['处理说明', d.handleNote || '—']
      ];
      if (d.type === 2) {
        rows.push(['退货运单', d.returnLogisticsNo ? (d.returnLogisticsCompany + ' ' + d.returnLogisticsNo) : '待填写']);
      }
      var html = '<h3>售后详情</h3>'
        + rows.map(function (r) { return '<div class="as-detail-row"><span class="k">' + r[0] + '</span><span class="v">' + S.esc(r[1]) + '</span></div>'; }).join('');
      // 商品
      html += '<div class="as-detail-row"><span class="k">商品</span><span class="v">'
        + (d.items || []).map(function (it) { return S.esc(it.goodsName) + ' ×' + it.quantity; }).join('；') + '</span></div>';
      // 时间线
      var tl = [];
      if (d.createdAt) tl.push('发起申请 · ' + S.esc(d.createdAt));
      if (d.handleTime) tl.push('平台处理 · ' + S.esc(d.handleTime));
      if (tl.length) html += '<div class="as-timeline">' + tl.map(function (t) { return '<div class="tl-item">' + S.esc(t) + '</div>'; }).join('') + '</div>';
      // 操作
      var act = '';
      if (d.status === 1) act += '<button class="as-btn as-btn-outline" id="jsAsCancel" data-id="' + d.id + '">撤销申请</button>';
      if (d.type === 2 && d.status === 2 && !d.returnLogisticsNo) {
        act += '<div style="margin-top:16px;"><input class="as-input" id="jsLogiCompany" placeholder="退货物流公司"><input class="as-input" id="jsLogiNo" placeholder="退货物流单号" style="margin-top:8px;"><button class="as-submit" id="jsLogiSubmit" style="margin-top:8px;">提交退货运单</button></div>';
      }
      if (act) html += '<div style="margin-top:16px;">' + act + '</div>';
      $('jsDetail').innerHTML = html;
    }).catch(function (err) { U.toast((err && err.message) || '加载失败', 'error'); showView('list'); });
  }

  function cancel(id) {
    if (!window.confirm('确定撤销该售后申请？')) return;
    Api.afterSales.cancel(id).then(function () { U.toast('已撤销', 'success'); loadDetail(id); }).catch(function (err) { U.toast((err && err.message) || '撤销失败', 'error'); });
  }

  function submitLogi(id) {
    var company = $('jsLogiCompany').value.trim();
    var no = $('jsLogiNo').value.trim();
    if (!company || !no) { U.toast('请填写物流公司与单号', 'warn'); return; }
    Api.afterSales.logistics(id, company, no).then(function () { U.toast('退货运单已填写', 'success'); loadDetail(id); }).catch(function (err) { U.toast((err && err.message) || '提交失败', 'error'); });
  }

  /* ---------- 事件 ---------- */
  function bindEvents() {
    document.addEventListener('click', function (e) {
      var tab = e.target.closest('.as-tab');
      if (tab) { state.status = tab.getAttribute('data-status') === '' ? null : Number(tab.getAttribute('data-status')); state.page = 1; loadList(); return; }
      var pg = e.target.closest('.page-num, .page-arrow');
      if (pg && !pg.classList.contains('disabled')) { state.page = Number(pg.getAttribute('data-page')); loadList(); window.scrollTo(0, 0); return; }
      var tp = e.target.closest('.as-type');
      if (tp && !tp.classList.contains('disabled')) { setType(Number(tp.getAttribute('data-type'))); return; }
      var sb = e.target.closest('#jsAsSubmit');
      if (sb) { submitApply(); return; }
      var cb = e.target.closest('#jsAsCancel');
      if (cb) { cancel(Number(cb.getAttribute('data-id'))); return; }
      var lb = e.target.closest('#jsLogiSubmit');
      if (lb) { submitLogi(Number(state.detail && state.detail.id)); return; }
      var ab = e.target.closest('[data-act="cancel"]');
      if (ab) { cancel(Number(ab.getAttribute('data-id'))); return; }
      var lg = e.target.closest('[data-act="logi"]');
      if (lg) { window.location.href = 'after-sale.html?view=detail&id=' + lg.getAttribute('data-id'); return; }
    });
  }

  function init() {
    var q = new URLSearchParams(window.location.search);
    bindEvents();
    var view = q.get('view') || 'list';
    if (view === 'apply') { loadApply(Number(q.get('orderId'))); }
    else if (view === 'detail') { loadDetail(Number(q.get('id'))); }
    else { loadList(); }
  }

  init();
})(window);
