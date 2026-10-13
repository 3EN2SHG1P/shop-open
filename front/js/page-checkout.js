/* ============================================
   结算确认页脚本（specs/商城前台V1.2.spec.md §8.6）
   服务端算钱：一切金额取 POST /orders/preview 返回
     - cart 模式：服务端取已勾选购物车行
     - buy  模式：?buy=1&goodsId=&skuId=&quantity= 直购单（详情页「立即购买」）
   地址/优惠券/积分任一变化 → 重新 preview 换取新 previewToken 后再提交
   依赖：ui.js / api.js / auth.js
   ============================================ */
(function (window, document) {
  'use strict';

  var S = window.ShopUtil;
  var U = window.ShopUI;
  var A = window.ShopAuth;
  var Api = window.ShopApi;

  var POINTS_RATIO = 100;
  var ADDR_KEY = 'shop_checkout_address';

  var state = {
    mode: 'cart',
    buyItem: null,
    addressId: 0,
    addresses: [],
    preview: null,
    couponId: null,
    pointsOn: false,
    payType: 1
  };

  function esc(t) { return S.esc(t); }
  function $(id) { return document.getElementById(id); }
  function node(sel) { return document.querySelector(sel); }
  function params() { return new URLSearchParams(window.location.search); }
  function money(n) { return S.money(Number(n) || 0); }
  function ratioAmount(points) { return Math.floor((Number(points) || 0) / POINTS_RATIO * 100) / 100; }

  /* ---------- 入口参数 ---------- */
  function initMode() {
    var q = params();
    if (q.get('buy') === '1' && q.get('goodsId') && q.get('skuId')) {
      state.mode = 'buy';
      state.buyItem = {
        goodsId: Number(q.get('goodsId')),
        skuId: Number(q.get('skuId')),
        quantity: Math.max(1, Number(q.get('quantity')) || 1)
      };
    }
    var stored = Number(window.sessionStorage.getItem(ADDR_KEY) || 0);
    if (stored > 0) {
      state.addressId = stored;
      window.sessionStorage.removeItem(ADDR_KEY);
    }
  }

  function previewBody() {
    var body = {
      type: state.mode,
      addressId: state.addressId || null,
      couponId: state.couponId || null,
      pointsUsed: state.pointsOn ? (Number(pointsOf(state.preview)) || 0) : 0
    };
    if (state.mode === 'buy') {
      body.items = [state.buyItem];
    }
    return body;
  }

  function pointsOf(preview) {
    return preview ? Number(preview.memberPoints) || 0 : 0;
  }

  /* ---------- 地址区 ---------- */
  function currentAddress() {
    for (var i = 0; i < state.addresses.length; i++) {
      if (state.addresses[i].id === state.addressId) return state.addresses[i];
    }
    return null;
  }

  function loadAddresses() {
    return Api.addresses().then(function (data) {
      state.addresses = (data && data.list) || [];
      if (!state.addressId) {
        var def = null;
        for (var i = 0; i < state.addresses.length; i++) {
          if (state.addresses[i].isDefault) { def = state.addresses[i]; break; }
        }
        state.addressId = def ? def.id : (state.addresses[0] ? state.addresses[0].id : 0);
      } else {
        var exists = state.addresses.some(function (a) { return a.id === state.addressId; });
        if (!exists) state.addressId = state.addresses[0] ? state.addresses[0].id : 0;
      }
    }).catch(function () {
      state.addresses = [];
    });
  }

  function addressText(a) {
    return [a.province, a.city, a.district, a.detail].filter(Boolean).join(' ');
  }

  function renderAddress() {
    var box = $('jsAddress');
    if (!box) return;
    var addr = currentAddress();
    if (!addr) {
      box.innerHTML = '<div class="address-empty">'
        + '<div class="empty-icon">📍</div>'
        + '<div class="empty-text">您还没有添加收货地址，请先添加</div>'
        + '<a class="add-address-btn" href="address-add.html?from=checkout.html">+ 添加收货地址</a></div>';
      return;
    }
    var cnt = state.addresses.length;
    box.innerHTML = '<div class="address-card active">'
      + '<div class="addr-top"><span class="addr-name">' + esc(addr.receiverName) + '</span>'
      + '<span class="addr-phone">' + esc(addr.receiverPhone) + '</span>'
      + (addr.isDefault ? '<span class="addr-default">默认</span>' : '') + '</div>'
      + '<div class="addr-detail">' + esc(addressText(addr)) + '</div>'
      + '<div class="addr-actions">'
      + '<a href="address-edit.html?id=' + addr.id + '&from=checkout.html">修改</a>'
      + (cnt > 1 ? '<a href="address.html?select=1">更换地址</a>' : '')
      + '</div></div>';
  }

  /* ---------- 商品清单 ---------- */
  function renderItems() {
    var box = $('jsItems');
    if (!box || !state.preview) return;
    box.innerHTML = state.preview.items.map(function (it) {
      return '<div class="checkout-item">'
        + '<img src="' + esc(it.image || '') + '" alt="' + esc(it.goodsName) + '"'
        + ' onerror="if(window.ShopUtil)ShopUtil.fallback(this)">'
        + '<div class="item-info"><div class="item-name">' + esc(it.goodsName) + '</div>'
        + (it.specText ? '<div class="item-spec">' + esc(it.specText) + '</div>' : '')
        + (it.seckill ? '<div class="item-spec seckill-tag">秒杀</div>' : '')
        + '</div>'
        + '<div class="item-price">¥' + money(it.price) + '</div>'
        + '<div class="item-qty">x' + it.quantity + '</div>'
        + '<div class="item-subtotal">¥' + money(it.subtotal) + '</div></div>';
    }).join('');
  }

  /* ---------- 优惠券 ---------- */
  function couponLabel(c) {
    var rule = c.type === 2
      ? ((Number(c.rate) || 1) * 10).toFixed(1).replace(/\.0$/, '') + ' 折'
      : '¥' + money(c.amount);
    return c.name + '（满' + money(c.minAmount) + '减' + rule + '，可抵 ¥' + money(c.discount) + '）';
  }

  function renderCoupon() {
    var sel = $('jsCoupon');
    var info = $('jsCouponInfo');
    if (!sel || !state.preview) return;
    var list = state.preview.availableCoupons || [];
    var usable = list.filter(function (c) { return c.usable; });
    var html = '<option value="">不使用优惠券</option>';
    html += usable.map(function (c) {
      return '<option value="' + c.id + '"' + (Number(state.couponId) === c.id ? ' selected' : '') + '>'
        + esc(couponLabel(c)) + '</option>';
    }).join('');
    html += list.filter(function (c) { return !c.usable; }).map(function (c) {
      return '<option value="" disabled>' + esc(c.name + '（当前订单不可用）') + '</option>';
    }).join('');
    sel.innerHTML = html;
    sel.value = usable.some(function (c) { return Number(state.couponId) === c.id; }) ? String(state.couponId) : '';
    if (info) {
      var unavailable = list.length === 0 ? '暂无可用优惠券' : (usable.length ? '可用 ' + usable.length + ' 张' : '无可用的优惠券');
      info.textContent = unavailable;
    }
  }

  /* ---------- 积分 ---------- */
  function renderPoints() {
    var box = $('jsPoints');
    var cb = $('jsPointsUse');
    if (!box || !state.preview) return;
    var pts = pointsOf(state.preview);
    if (!pts) {
      box.style.display = 'none';
      return;
    }
    box.style.display = '';
    if (cb) cb.checked = state.pointsOn;
    var amount = Math.min(ratioAmount(pts), Number(state.preview.payAmount) || 0);
    var text = $('jsPointsText');
    if (text) {
      text.innerHTML = '可用积分 <strong>' + pts + '</strong>，可抵扣 ¥' + money(amount)
        + '（' + POINTS_RATIO + ' 积分抵 ¥1）';
    }
  }

  /* ---------- 金额 ---------- */
  function renderAmount() {
    var p = state.preview;
    if (!p) return;
    var count = p.items.reduce(function (s, it) { return s + Number(it.quantity || 0); }, 0);
    setText('jsCount', String(count));
    setText('jsTotal', '¥' + money(p.totalAmount));
    setText('jsFreight', '¥' + money(p.freightAmount));
    setText('jsCouponAmount', '¥' + money(p.couponAmount));
    setText('jsPointsAmount', '¥' + money(p.pointsAmount));
    setText('jsPay', money(p.payAmount));
    var rowCoupon = $('jsRowCoupon');
    var rowPoints = $('jsRowPoints');
    if (rowCoupon) rowCoupon.style.display = Number(p.couponAmount) > 0 ? '' : 'none';
    if (rowPoints) rowPoints.style.display = Number(p.pointsAmount) > 0 ? '' : 'none';
  }

  function setText(id, text) {
    var el = $(id);
    if (el) el.textContent = text;
  }

  /* ---------- 加载 ---------- */
  function render() {
    renderAddress();
    renderItems();
    renderCoupon();
    renderPoints();
    renderAmount();
    var btn = $('jsSubmit');
    if (btn) btn.disabled = !state.preview || !state.addressId;
  }

  function renderLoading() {
    if ($('jsAddress')) $('jsAddress').innerHTML = '<div class="loading-hint">加载中…</div>';
    if ($('jsItems')) $('jsItems').innerHTML = '<div class="loading-hint">加载中…</div>';
  }

  function backToCart(msg) {
    U.toast(msg || '没有待结算的商品', 'warn');
    window.setTimeout(function () {
      window.location.href = state.mode === 'buy' ? 'index.html' : 'cart.html';
    }, 600);
  }

  function doPreview() {
    return Api.previewOrder(previewBody()).then(function (data) {
      state.preview = data;
      if (data && data.addressId) state.addressId = Number(data.addressId) || state.addressId;
      if (state.couponId && Number((data.couponAmount) || 0) <= 0) state.couponId = null;
      render();
    });
  }

  function reloadAll() {
    renderLoading();
    return loadAddresses().then(function () {
      return doPreview();
    }).catch(function (err) {
      var code = err && err.code;
      if (code === 3001 || code === 3002 || code === 2001) backToCart((err && err.message) || '结算商品已失效');
      else U.toast((err && err.message) || '结算信息加载失败', 'error');
    });
  }

  /* ---------- 事件 ---------- */
  function bindEvents() {
    document.addEventListener('click', function (e) {
      var pm = e.target.closest('.payment-method');
      if (pm) {
        Array.prototype.forEach.call(document.querySelectorAll('.payment-method'), function (m) {
          m.classList.remove('active');
        });
        pm.classList.add('active');
        state.payType = Number(pm.getAttribute('data-pay')) || 1;
        return;
      }
      if (e.target.closest('.submit-order-btn')) submit();
    });

    document.addEventListener('change', function (e) {
      if (e.target.id === 'jsCoupon') {
        state.couponId = e.target.value ? Number(e.target.value) : null;
        doPreview().catch(function () {});
        return;
      }
      if (e.target.id === 'jsPointsUse') {
        state.pointsOn = e.target.checked;
        doPreview().catch(function () {});
      }
    });

    window.addEventListener('pageshow', function (e) {
      if (!e.persisted) return;
      var stored = Number(window.sessionStorage.getItem(ADDR_KEY) || 0);
      if (stored > 0) {
        state.addressId = stored;
        window.sessionStorage.removeItem(ADDR_KEY);
        doPreview().catch(function () {});
      }
    });
  }

  /* ---------- 提交 ---------- */
  function submit() {
    if (!state.addressId) { U.toast('请先选择收货地址', 'warn'); return; }
    if (!state.preview || !state.preview.previewToken) { U.toast('结算信息已失效，正在刷新…', 'warn'); reloadAll(); return; }
    var btn = $('jsSubmit');
    var remark = $('jsRemark') ? $('jsRemark').value.trim() : '';
    U.busy(btn, function () {
      return Api.createOrder({
        previewToken: state.preview.previewToken,
        addressId: Number(state.addressId),
        payType: state.payType,
        couponId: state.couponId || null,
        pointsUsed: state.pointsOn ? (Number(pointsOf(state.preview)) || 0) : 0,
        buyerMessage: remark
      }).then(function (data) {
        window.sessionStorage.removeItem(ADDR_KEY);
        A.refreshCartBadge();
        window.location.href = 'payment.html?orderNo=' + encodeURIComponent(data.orderNo);
      }).catch(function (err) {
        var code = err && err.code;
        if (code === 3006 || code === 3002) {
          U.toast('订单金额已更新，请确认后重新提交', 'warn');
          reloadAll();
          return;
        }
        if (code === 3007) {
          state.couponId = null;
          reloadAll();
          return;
        }
        if (code === 3001 || code === 3008) reloadAll();
      });
    });
  }

  bindEvents();
  initMode();
  renderLoading();
  reloadAll();
})(window, document);
