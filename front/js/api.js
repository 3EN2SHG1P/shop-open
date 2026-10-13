/* ============================================
   商城前台 · 公共请求层（specs/商城前台V1.2.spec.md §9）
   - fetch 封装：自动带会员 token、超时、统一 {code,message,data} 解包
   - 1001/1002 未登录/失效 → 跳 login.html 并带 redirect
   - 其余错误码 toast 提示后抛出，业务分支按 err.code 处理
   - 接口基址可配：window.SHOP_API_BASE > localStorage.shop_api_base > 默认 8001
   ============================================ */
(function (window) {
  'use strict';

  // 默认推导当前 host 的 8001 端口；可用 window.SHOP_API_BASE 或 localStorage.shop_api_base 覆盖
  var DEFAULT_BASE = window.location.protocol + '//' + (window.location.hostname || '127.0.0.1') + ':8001';

  function baseUrl() {
    var raw = window.SHOP_API_BASE || window.localStorage.getItem('shop_api_base') || DEFAULT_BASE;
    return String(raw).replace(/\/+$/, '');
  }

  function toast(msg) {
    if (window.ShopUI && typeof window.ShopUI.toast === 'function') {
      window.ShopUI.toast(msg);
    }
  }

  function redirectPath() {
    var path = window.location.pathname.split('/').pop() || 'index.html';
    return path + window.location.search;
  }

  function gotoLogin() {
    if (window.ShopAuth && typeof window.ShopAuth.clear === 'function') {
      window.ShopAuth.clear();
    } else {
      window.localStorage.removeItem('shop_token');
      window.localStorage.removeItem('shop_member');
    }
    var from = redirectPath();
    if (from.indexOf('login.html') === 0 || from.indexOf('register.html') === 0) {
      window.location.href = 'login.html';
    } else {
      window.location.href = 'login.html?redirect=' + encodeURIComponent(from);
    }
  }

  function request(path, opts) {
    opts = opts || {};
    var method = String(opts.method || 'GET').toUpperCase();
    var headers = { 'Content-Type': 'application/json' };
    var token = window.localStorage.getItem('shop_token');
    if (opts.auth !== false && token) {
      headers['Authorization'] = 'Bearer ' + token;
    }

    var timer = null;
    var init = { method: method, headers: headers };
    if (typeof AbortController !== 'undefined') {
      var ctrl = new AbortController();
      init.signal = ctrl.signal;
      timer = window.setTimeout(function () { ctrl.abort(); }, opts.timeout || 15000);
    }
    if (opts.body !== undefined && method !== 'GET') {
      init.body = JSON.stringify(opts.body);
    }

    function done(value) {
      if (timer) window.clearTimeout(timer);
      return value;
    }
    function fail(err) {
      if (timer) window.clearTimeout(timer);
      throw err;
    }

    return window.fetch(baseUrl() + path, init).then(function (res) {
      return res.json().catch(function () {
        throw new Error('服务返回异常（HTTP ' + res.status + '）');
      }).then(function (json) {
        var code = json.code;
        var message = json.message || '请求失败';
        if (code === 0) return json.data;
        if (code === 1001 || code === 1002) {
          // 已在登录页（如密码错误）不再跳转，避免死循环且让用户看到失败原因
          if (redirectPath().indexOf('login.html') === 0) {
            if (opts.silent !== true) toast(message);
          } else {
            gotoLogin();
          }
          var le = new Error(message);
          le.code = code;
          return Promise.reject(le);
        }
        var err = new Error(message);
        err.code = code;
        err.data = json.data;
        if (opts.silent !== true) toast(message);
        return Promise.reject(err);
      });
    }).catch(function (err) {
      if (err && err.code !== undefined) return fail(err);
      var message = '网络异常，请检查后端服务（' + baseUrl() + '）';
      if (err && err.name === 'AbortError') message = '请求超时，请重试';
      else if (err && err.message) message = err.message;
      var e = new Error(message);
      e.code = -1;
      if (opts.silent !== true) toast(message);
      return fail(e);
    }).then(done, fail);
  }

  function qs(params) {
    var parts = [];
    Object.keys(params || {}).forEach(function (k) {
      var v = params[k];
      if (v === undefined || v === null || v === '') return;
      parts.push(encodeURIComponent(k) + '=' + encodeURIComponent(v));
    });
    return parts.length ? '?' + parts.join('&') : '';
  }

  var ShopApi = {
    /* 认证 */
    sendCode: function (phone) {
      return request('/api/v1/shop/auth/send-code', { method: 'POST', body: { phone: phone, scene: 'register' } });
    },
    register: function (phone, code, password) {
      return request('/api/v1/shop/auth/register', { method: 'POST', body: { phone: phone, code: code, password: password } });
    },
    login: function (phone, password) {
      return request('/api/v1/shop/auth/login', { method: 'POST', body: { phone: phone, password: password } });
    },
    me: function () {
      return request('/api/v1/shop/auth/me');
    },
    logout: function () {
      return request('/api/v1/shop/auth/logout', { method: 'POST', silent: true });
    },

    /* 首页与内容 */
    home: function () {
      return request('/api/v1/shop/home');
    },
    notices: function () {
      return request('/api/v1/shop/notices');
    },
    ads: function (positionId) {
      return request('/api/v1/shop/ads' + (positionId ? qs({ positionId: positionId }) : ''));
    },
    categories: function () {
      return request('/api/v1/shop/categories');
    },
    brands: function () {
      return request('/api/v1/shop/brands');
    },
    specs: function () {
      return request('/api/v1/shop/specs');
    },

    /* 商品 */
    goods: function (params) {
      return request('/api/v1/shop/goods' + qs(params));
    },
    goodsDetail: function (id) {
      return request('/api/v1/shop/goods/' + id);
    },
    goodsComments: function (id, params) {
      return request('/api/v1/shop/goods/' + id + '/comments' + qs(params));
    },
    visit: function (id) {
      return request('/api/v1/shop/goods/' + id + '/visit', { method: 'POST' });
    },

    /* 购物车（入参 camelCase，见 spec §5.4） */
    cart: function () {
      return request('/api/v1/shop/cart', { silent: true });
    },
    addCart: function (goodsId, skuId, quantity) {
      return request('/api/v1/shop/cart', {
        method: 'POST',
        body: { goodsId: Number(goodsId), skuId: Number(skuId), quantity: Number(quantity) || 1 }
      });
    },
    updateCartQuantity: function (cartId, quantity) {
      return request('/api/v1/shop/cart/' + cartId, {
        method: 'PUT', body: { quantity: Number(quantity) }, silent: true
      });
    },
    updateCartSelected: function (ids, selected) {
      return request('/api/v1/shop/cart/selected', {
        method: 'PUT', body: { ids: ids || [], selected: selected !== false }, silent: true
      });
    },
    deleteCartItem: function (cartId) {
      return request('/api/v1/shop/cart/' + cartId, { method: 'DELETE', silent: true });
    },
    clearCart: function () {
      return request('/api/v1/shop/cart', { method: 'DELETE', silent: true });
    },
    mergeCart: function (items) {
      return request('/api/v1/shop/cart/merge', { method: 'POST', body: { items: items }, silent: true });
    },

    /* 收货地址（spec §5.5） */
    addresses: function () {
      return request('/api/v1/shop/addresses', { silent: true });
    },
    createAddress: function (body) {
      return request('/api/v1/shop/addresses', { method: 'POST', body: body });
    },
    updateAddress: function (id, body) {
      return request('/api/v1/shop/addresses/' + id, { method: 'PUT', body: body });
    },
    setDefaultAddress: function (id) {
      return request('/api/v1/shop/addresses/' + id + '/default', { method: 'PUT' });
    },
    deleteAddress: function (id) {
      return request('/api/v1/shop/addresses/' + id, { method: 'DELETE' });
    },
    regions: function (parentCode) {
      // 注意：后端 query 参数为 snake_case，此处必须用 parent_code
      return request('/api/v1/shop/regions' + qs({ parent_code: parentCode || '' }));
    },

    /* 结算与下单（spec §5.6） */
    previewOrder: function (body) {
      return request('/api/v1/shop/orders/preview', { method: 'POST', body: body, silent: true });
    },
    createOrder: function (body) {
      return request('/api/v1/shop/orders', { method: 'POST', body: body });
    },

    /* 订单列表与详情（spec §5.7） */
    orders: function (params) {
      return request('/api/v1/shop/orders' + qs(params));
    },
    orderDetail: function (orderNo) {
      return request('/api/v1/shop/orders/' + encodeURIComponent(orderNo));
    },
    cancelOrder: function (orderNo) {
      return request('/api/v1/shop/orders/' + encodeURIComponent(orderNo) + '/cancel', { method: 'POST' });
    },
    confirmReceipt: function (orderNo) {
      return request('/api/v1/shop/orders/' + encodeURIComponent(orderNo) + '/confirm-receipt', { method: 'POST' });
    },
    buyAgain: function (orderNo) {
      return request('/api/v1/shop/orders/' + encodeURIComponent(orderNo) + '/again', { method: 'POST' });
    },
    logistics: function (orderNo) {
      return request('/api/v1/shop/orders/' + encodeURIComponent(orderNo) + '/logistics');
    },

    /* 支付（模拟网关，spec §5.8） */
    payOrder: function (orderNo, payType) {
      // 不传 payType 时由后端按订单自身 payType 处理，避免"支付方式不一致"误拦
      return request('/api/v1/shop/pay/' + encodeURIComponent(orderNo), {
        method: 'POST', body: payType ? { payType: Number(payType) } : {}
      });
    },
    payStatus: function (orderNo) {
      return request('/api/v1/shop/pay/' + encodeURIComponent(orderNo) + '/status');
    },

    /* 会员积分（spec §5.10，orders 快捷条摘要） */
    points: function () {
      return request('/api/v1/shop/points');
    },

    /* 会员评价（spec §5.3 / §10 规则 10，仅已完成(4)订单本人可评、同订单同商品不重复） */
    addComment: function (goodsId, score, content) {
      return request('/api/v1/shop/goods/' + encodeURIComponent(goodsId) + '/comments', {
        method: 'POST', body: { score: Number(score), content: String(content) }
      });
    },

    /* 售后（spec §5.9 / §8.15，需登录） */
    afterSales: {
      list: function (params) { return request('/api/v1/shop/after-sales' + qs(params)); },
      detail: function (id) { return request('/api/v1/shop/after-sales/' + encodeURIComponent(id)); },
      apply: function (body) {
        return request('/api/v1/shop/after-sales', { method: 'POST', body: body });
      },
      logistics: function (id, company, no) {
        return request('/api/v1/shop/after-sales/' + encodeURIComponent(id) + '/logistics', {
          method: 'POST', body: { returnLogisticsCompany: String(company), returnLogisticsNo: String(no) }
        });
      },
      cancel: function (id) {
        return request('/api/v1/shop/after-sales/' + encodeURIComponent(id) + '/cancel', { method: 'POST' });
      }
    },

    /* 优惠券（spec §5.10 / §8.16，需登录） */
    coupons: {
      mine: function (params) { return request('/api/v1/shop/coupons' + qs(params)); },
      available: function () { return request('/api/v1/shop/coupons/available'); },
      receive: function (id) {
        return request('/api/v1/shop/coupons/' + encodeURIComponent(id) + '/receive', { method: 'POST' });
      }
    },

    /* 积分（spec §5.10 / §8.17，需登录） */
    points: function () {
      return request('/api/v1/shop/points');
    },
    pointsLogs: function (params) {
      return request('/api/v1/shop/points/logs' + qs(params));
    }
  };

  window.ShopRequest = request;
  window.ShopApi = ShopApi;
  window.SHOP_API_BASE_DEFAULT = DEFAULT_BASE;
})(window);
