/* ============================================
   收货地址页脚本（specs/商城前台V1.2.spec.md §8.7）
   两种模式（由 URL 决定）：
     ?select=1 结算选地址模式 —— 点卡片写 sessionStorage.shop_checkout_address 后回退
     其余        地址管理模式 —— 列表 + 默认徽标 + 新增/编辑/删除/设默认
   依赖：ui.js / api.js / auth.js
   ============================================ */
(function (window, document) {
  'use strict';

  var S = window.ShopUtil;
  var U = window.ShopUI;
  var Api = window.ShopApi;
  var ADDR_KEY = 'shop_checkout_address';

  var state = { list: [], selectMode: false };

  function esc(t) { return S.esc(t); }
  function $(id) { return document.getElementById(id); }

  function fullText(a) {
    return [a.province, a.city, a.district, a.detail].filter(Boolean).join(' ');
  }

  function cardHtml(a) {
    return '<div class="address-card' + (a.isDefault && !state.selectMode ? ' active' : '') + '" data-id="' + a.id + '">'
      + '<div class="addr-top"><span class="addr-name">' + esc(a.receiverName) + '</span>'
      + '<span class="addr-phone">' + esc(a.receiverPhone) + '</span>'
      + (a.isDefault ? '<span class="addr-default">默认</span>' : '') + '</div>'
      + '<div class="addr-detail">' + esc(fullText(a)) + '</div>'
      + '<div class="addr-actions">'
      + (state.selectMode
        ? '<a href="javascript:;" data-act="choose">使用此地址</a>'
        : (a.isDefault ? '' : '<a href="javascript:;" data-act="default">设为默认</a>')
        + '<a href="address-edit.html?id=' + a.id + '&from=address.html" data-act="edit">修改</a>'
        + '<a href="javascript:;" data-act="delete">删除</a>')
      + '</div></div>';
  }

  function render() {
    var box = $('jsAddressList');
    if (!box) return;
    if (!state.list.length) {
      box.innerHTML = '<div class="empty-hint">暂无收货地址，请点击右下角「新增收货地址」</div>';
      return;
    }
    box.innerHTML = state.list.map(cardHtml).join('') ;
  }

  function reload() {
    return Api.addresses().then(function (data) {
      state.list = (data && data.list) || [];
      render();
    }).catch(function () {
      state.list = [];
      if ($('jsAddressList')) $('jsAddressList').innerHTML = '<div class="empty-hint">地址加载失败</div>';
    });
  }

  function choose(id) {
    window.sessionStorage.setItem(ADDR_KEY, String(id));
    if (window.history.length > 1) window.history.back();
    else window.location.href = 'checkout.html';
  }

  function setDefault(id) {
    Api.setDefaultAddress(id).then(function () {
      U.toast('已设为默认地址', 'success');
      reload();
    });
  }

  function remove(id) {
    if (!window.confirm('确定删除该收货地址吗？')) return;
    Api.deleteAddress(id).then(function () {
      U.toast('地址已删除', 'success');
      reload();
    });
  }

  function bindEvents() {
    document.addEventListener('click', function (e) {
      var act = e.target.closest('[data-act]');
      if (!act) {
        if (state.selectMode) {
          var card = e.target.closest('.address-card');
          if (card) choose(card.getAttribute('data-id'));
        }
        return;
      }
      var card = act.closest('.address-card');
      if (!card) return;
      var id = Number(card.getAttribute('data-id'));
      var kind = act.getAttribute('data-act');
      if (kind === 'choose') choose(id);
      else if (kind === 'default') setDefault(id);
      else if (kind === 'delete') remove(id);
    });
  }

  /* ---------- 入口 ---------- */
  var q = new URLSearchParams(window.location.search);
  state.selectMode = q.get('select') === '1';
  if (state.selectMode) {
    if ($('jsTitle')) $('jsTitle').textContent = '选择收货地址';
    if ($('jsTip')) $('jsTip').textContent = '结算过程中选择收货地址：点击卡片即可使用';
  } else if ($('jsTip')) {
    $('jsTip').textContent = '地址管理：可修改、删除或切换默认地址';
  }

  bindEvents();
  reload();
})(window, document);
