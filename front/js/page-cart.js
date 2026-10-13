/* ============================================
   购物车页脚本（specs/商城前台V1.2.spec.md §8.5）
   两态：会员 → 服务端 /api/v1/shop/cart；游客 → localStorage shop_cart_guest
   勾选/数量/删除/全选均本地即时更新（乐观），接口失败回滚重取服务端真相
   依赖：ui.js / api.js / auth.js
   ============================================ */
(function (window, document) {
  'use strict';

  var S = window.ShopUtil;
  var U = window.ShopUI;
  var A = window.ShopAuth;
  var Api = window.ShopApi;

  var state = { rows: [] };

  function esc(t) { return S.esc(t); }
  function isServer() { return !!A.isLogin(); }
  function indexOfKey(key) {
    for (var i = 0; i < state.rows.length; i++) {
      if (state.rows[i].key === key) return i;
    }
    return -1;
  }
  function rowOf(key) {
    var i = indexOfKey(key);
    return i < 0 ? null : state.rows[i];
  }
  function rowIndex(el) {
    var tr = el.closest('.cart-row');
    return tr ? rowOf(tr.getAttribute('data-key')) : null;
  }
  function selectedRows() {
    return state.rows.filter(function (r) { return r.selected; });
  }

  /* ---------- 数据归一 ---------- */
  function viewOf(r, idx) {
    return {
      key: (r.id !== undefined && r.id !== null) ? ('s' + r.id) : ('g' + idx),
      id: r.id,
      goodsId: Number(r.goodsId || 0) || 0,
      skuId: Number(r.skuId || 0) || 0,
      name: r.goodsName || r.name || '商品',
      specText: r.specText || [r.version, r.color].filter(Boolean).join(' '),
      price: Number(r.price) || 0,
      image: r.image || '',
      quantity: Math.max(1, Number(r.quantity) || 1),
      stock: Number(r.stock) || 0,
      selected: !(r.selected === 0 || r.selected === false)
    };
  }

  function loadServer() {
    return Api.cart().then(function (data) {
      state.rows = ((data && data.list) || []).map(viewOf);
      state.amount = Number((data && data.totalAmount) || 0);
    });
  }

  function loadGuest() {
    state.rows = A.getGuestCart().map(viewOf);
    state.amount = 0;
    return Promise.resolve();
  }

  function reload() {
    var p = isServer() ? loadServer() : loadGuest();
    return p.then(render).catch(function () {
      state.rows = [];
      render();
    });
  }

  /* ---------- 渲染 ---------- */
  function rowHtml(item) {
    var href = item.goodsId ? 'detail.html?id=' + item.goodsId : 'javascript:;';
    var minusDis = item.quantity <= 1 ? ' disabled' : '';
    var plusDis = item.stock > 0 && item.quantity >= item.stock ? ' disabled' : '';
    var oos = item.stock === 0 ? '<span class="oos-tag">缺货</span>' : '';
    return '<tr class="cart-row" data-key="' + esc(item.key) + '">'
      + '<td class="col-check"><label class="checkbox">'
      + '<input type="checkbox" class="row-checkbox" data-key="' + esc(item.key) + '"' + (item.selected ? ' checked' : '') + '>'
      + '<span class="checkbox-box"></span></label></td>'
      + '<td class="col-product">'
      + '<img class="cart-thumb" src="' + esc(item.image) + '" alt="' + esc(item.name) + '"'
      + ' onerror="if(window.ShopUtil)ShopUtil.fallback(this)">'
      + '<div class="cart-info"><a class="cart-name" href="' + href + '">' + esc(item.name) + '</a>'
      + (item.specText ? '<div class="cart-spec">' + esc(item.specText) + '</div>' : '')
      + oos + '</div></td>'
      + '<td class="col-price">¥' + S.money(item.price) + '</td>'
      + '<td class="col-quantity"><div class="quantity-picker">'
      + '<span class="qty-btn qty-minus' + minusDis + '">-</span>'
      + '<input type="text" class="qty-input" value="' + esc(item.quantity) + '" readonly>'
      + '<span class="qty-btn qty-plus' + plusDis + '">+</span></div></td>'
      + '<td class="col-subtotal price">¥' + S.money(item.price * item.quantity) + '</td>'
      + '<td class="col-action"><span class="delete-btn" title="删除">×</span></td></tr>';
  }

  function updateFooter() {
    var sel = selectedRows();
    var count = sel.reduce(function (s, r) { return s + r.quantity; }, 0);
    var amount = sel.reduce(function (s, r) { return s + r.price * r.quantity; }, 0);
    var all = state.rows.length > 0 && state.rows.every(function (r) { return r.selected; });
    Array.prototype.forEach.call(document.querySelectorAll('.selected-count'), function (el) {
      el.textContent = String(count);
    });
    Array.prototype.forEach.call(document.querySelectorAll('.cart-total-num'), function (el) {
      el.textContent = S.money(amount);
    });
    Array.prototype.forEach.call(document.querySelectorAll('.select-all-checkbox'), function (el) {
      el.checked = all;
    });
  }

  function renderTip() {
    var tip = document.getElementById('cartTip');
    if (!tip) return;
    if (isServer() || !state.rows.length) {
      tip.style.display = 'none';
      return;
    }
    tip.style.display = '';
    tip.innerHTML = '当前为游客购物车（仅保存在本机），'
      + '<a href="login.html?redirect=' + encodeURIComponent('cart.html') + '">登录</a>后自动合并到账户。';
  }

  function render() {
    var empty = document.getElementById('cartEmpty');
    var main = document.getElementById('cartMain');
    if (!state.rows.length) {
      if (empty) empty.style.display = 'block';
      if (main) main.style.display = 'none';
      updateFooter();
      renderTip();
      if (document.getElementById('cartBody')) document.getElementById('cartBody').innerHTML = '';
      return;
    }
    if (empty) empty.style.display = 'none';
    if (main) main.style.display = '';
    document.getElementById('cartBody').innerHTML = state.rows.map(rowHtml).join('');
    updateFooter();
    renderTip();
  }

  function renderLoading() {
    var empty = document.getElementById('cartEmpty');
    var main = document.getElementById('cartMain');
    if (empty) empty.style.display = 'none';
    if (main) main.style.display = '';
    document.getElementById('cartBody').innerHTML =
      '<tr><td colspan="6" style="text-align:center;padding:30px;color:var(--text-secondary)">加载中…</td></tr>';
  }

  /* ---------- 操作 ---------- */
  function saveGuest() {
    A.setGuestCart(state.rows.map(function (r) {
      return {
        goodsId: r.goodsId, skuId: r.skuId, name: r.name, specText: r.specText,
        price: r.price, image: r.image, quantity: r.quantity, selected: r.selected ? 1 : 0
      };
    }));
  }

  function rollback(err) {
    U.toast((err && err.message) || '操作失败，已刷新为最新数据', 'error');
    return reload();
  }

  function setSelected(item, value) {
    item.selected = value;
    render();
    if (isServer()) {
      Api.updateCartSelected([item.id], value).catch(rollback);
    } else {
      saveGuest();
    }
  }

  function toggleAll(value) {
    state.rows.forEach(function (r) { r.selected = value; });
    render();
    if (isServer()) {
      Api.updateCartSelected([], value).catch(rollback);
    } else {
      saveGuest();
    }
  }

  function changeQuantity(item, delta) {
    var next = item.quantity + delta;
    if (next < 1) return;
    if (item.stock > 0 && next > item.stock) {
      U.toast('库存仅剩 ' + item.stock + ' 件', 'warn');
      return;
    }
    item.quantity = next;
    render();
    if (isServer()) {
      Api.updateCartQuantity(item.id, next).then(function () {
        A.refreshCartBadge();
      }).catch(rollback);
    } else {
      saveGuest();
    }
  }

  function removeRow(item) {
    if (!window.confirm('确定要删除该商品吗？')) return;
    state.rows = state.rows.filter(function (r) { return r.key !== item.key; });
    render();
    if (isServer()) {
      Api.deleteCartItem(item.id).then(function () {
        A.refreshCartBadge();
      }).catch(rollback);
    } else {
      saveGuest();
    }
  }

  function goCheckout() {
    if (!selectedRows().length) {
      U.toast('请先选择要结算的商品', 'warn');
      return;
    }
    if (!A.isLogin()) {
      window.location.href = 'login.html?redirect=' + encodeURIComponent('cart.html');
      return;
    }
    window.location.href = 'checkout.html';
  }

  /* ---------- 事件（document 级委托，重渲染不失效） ---------- */
  function bindEvents() {
    document.addEventListener('change', function (e) {
      var t = e.target;
      if (t.classList.contains('select-all-checkbox')) {
        toggleAll(t.checked);
        return;
      }
      if (t.classList.contains('row-checkbox')) {
        var item = rowOf(t.getAttribute('data-key'));
        if (item) setSelected(item, t.checked);
      }
    });

    document.addEventListener('click', function (e) {
      var btn = e.target.closest('.checkout-btn');
      if (btn) {
        goCheckout();
        return;
      }
      var del = e.target.closest('.delete-btn');
      if (del) {
        var row = rowIndex(del);
        if (row) removeRow(row);
        return;
      }
      var qtyBtn = e.target.closest('.qty-btn');
      if (qtyBtn && !qtyBtn.classList.contains('disabled')) {
        var item = rowIndex(qtyBtn);
        if (item) changeQuantity(item, qtyBtn.classList.contains('qty-minus') ? -1 : 1);
      }
    });
  }

  bindEvents();
  renderLoading();
  reload();
})(window, document);
