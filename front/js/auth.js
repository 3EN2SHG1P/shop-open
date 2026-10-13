/* ============================================
   商城前台 · 登录态 / 游客购物车 / 顶栏渲染
   （specs/商城前台V1.2.spec.md §7 路由守卫、§8.13 登录、§9 公共层）

   存储键：
     shop_token / shop_member  会员登录态
     shop_cart_guest           游客购物车（登录时合并到服务端 member_cart）
   ============================================ */
(function (window, document) {
  'use strict';

  var TOKEN_KEY = 'shop_token';
  var MEMBER_KEY = 'shop_member';
  var GUEST_KEY = 'shop_cart_guest';

  var PAGE = (window.location.pathname.split('/').pop() || 'index.html');

  function toast(msg, type) {
    if (window.ShopUI && window.ShopUI.toast) window.ShopUI.toast(msg, type);
  }

  /* ---------- 登录态 ---------- */
  function getToken() {
    return window.localStorage.getItem(TOKEN_KEY) || '';
  }

  function getMember() {
    try {
      return JSON.parse(window.localStorage.getItem(MEMBER_KEY) || 'null');
    } catch (e) {
      return null;
    }
  }

  function isLogin() {
    return !!getToken();
  }

  function setSession(token, member) {
    window.localStorage.setItem(TOKEN_KEY, token);
    if (member) window.localStorage.setItem(MEMBER_KEY, JSON.stringify(member));
  }

  function clear() {
    window.localStorage.removeItem(TOKEN_KEY);
    window.localStorage.removeItem(MEMBER_KEY);
  }

  function logout() {
    if (window.ShopApi) {
      window.ShopApi.logout().catch(function () {});
    }
    clear();
    window.location.href = 'index.html';
  }

  /* ---------- 游客购物车 ---------- */
  function getGuestCart() {
    try {
      var list = JSON.parse(window.localStorage.getItem(GUEST_KEY) || '[]');
      return Array.isArray(list) ? list : [];
    } catch (e) {
      return [];
    }
  }

  function setGuestCart(items) {
    window.localStorage.setItem(GUEST_KEY, JSON.stringify(items || []));
    updateCartBadge();
  }

  function clearGuestCart() {
    window.localStorage.removeItem(GUEST_KEY);
    updateCartBadge();
  }

  function guestCartCount() {
    return getGuestCart().reduce(function (sum, item) {
      return sum + (Number(item.quantity) || 0);
    }, 0);
  }

  /** 登录后合并游客车：本地非空 → POST /cart/merge → 清空本地；失败不阻塞 */
  function mergeGuestCart() {
    var items = getGuestCart();
    if (!items.length) return Promise.resolve(0);
    var payload = items.map(function (i) {
      return {
        goodsId: Number(i.goodsId || i.id) || 0,
        skuId: Number(i.skuId || i.versionId || i.id) || 0,
        quantity: Number(i.quantity) || 1,
        selected: i.selected === false ? 0 : 1
      };
    });
    return window.ShopApi.mergeCart(payload).then(function () {
      clearGuestCart();
      return items.length;
    }).catch(function (err) {
      toast((err && err.message) || '购物车合并失败', 'error');
      return 0;
    });
  }

  /* ---------- 顶栏角标 ---------- */
  function updateCartBadge(count) {
    var nodes = document.querySelectorAll('.cart-count');
    if (!nodes.length) return;
    var value = count;
    if (typeof value !== 'number') {
      value = isLogin() ? Number(window.localStorage.getItem('shop_cart_count') || 0) : guestCartCount();
    }
    Array.prototype.forEach.call(nodes, function (el) {
      el.textContent = String(value);
    });
  }

  function refreshCartBadge() {
    if (!isLogin()) {
      updateCartBadge(guestCartCount());
      return Promise.resolve();
    }
    return window.ShopApi.cart().then(function (data) {
      var count = Number((data && data.totalCount) || 0);
      window.localStorage.setItem('shop_cart_count', String(count));
      updateCartBadge(count);
    }).catch(function () {
      updateCartBadge(guestCartCount());
    });
  }

  /* ---------- 顶栏登录态 ---------- */
  function redirectQuery() {
    return '?redirect=' + encodeURIComponent(PAGE + window.location.search);
  }

  function ensureSlot(bar) {
    var slot = bar.querySelector('.shop-auth-slot');
    if (slot) return slot;
    slot = document.createElement('span');
    slot.className = 'shop-auth-slot';
    var loginA = bar.querySelector('a[href="login.html"]');
    var regA = bar.querySelector('a[href="register.html"]');
    if (regA && regA.parentNode === bar) regA.parentNode.removeChild(regA);
    if (loginA && loginA.parentNode === bar) {
      bar.insertBefore(slot, loginA);
      loginA.parentNode.removeChild(loginA);
    } else {
      bar.insertBefore(slot, bar.firstChild);
    }
    return slot;
  }

  function renderHeaderAuth() {
    var bars = document.querySelectorAll('.top-bar-right');
    if (!bars.length) return;
    Array.prototype.forEach.call(bars, function (bar) {
      var slot = ensureSlot(bar);
      if (isLogin()) {
        var m = getMember() || {};
        var name = m.nickname || m.phone || '我的账户';
        var eName = window.ShopUtil ? window.ShopUtil.esc(name) : name;
        slot.innerHTML =
          '<a href="orders.html" class="shop-user-link" title="' + eName + '">' + eName + '</a>' +
          '<a href="javascript:;" class="shop-logout-link">退出</a>';
        var out = slot.querySelector('.shop-logout-link');
        if (out) {
          out.addEventListener('click', function (e) {
            e.preventDefault();
            logout();
          });
        }
      } else {
        slot.innerHTML =
          '<a href="login.html' + redirectQuery() + '">登录</a>' +
          '<a href="register.html' + redirectQuery() + '">注册</a>';
      }
    });
  }

  /* ---------- 路由守卫（spec §7） ---------- */
  var NEED_LOGIN = ['checkout.html', 'address.html', 'address-add.html', 'address-edit.html',
    'payment.html', 'wechat-pay.html', 'orders.html', 'after-sale.html', 'coupons.html', 'points.html'];

  function guard() {
    if (isLogin() && (PAGE === 'login.html' || PAGE === 'register.html')) {
      window.location.replace('index.html');
      return true;
    }
    if (!isLogin() && NEED_LOGIN.indexOf(PAGE) >= 0) {
      window.location.replace('login.html' + redirectQuery());
      return true;
    }
    return false;
  }

  /** 登录后回跳：读 ?redirect=，缺省 index.html。
      只放行站内 .html 相对路径——直接把 origin 可控的参数丢给 location.href 会同时造成
      开放重定向钓鱼与 javascript: 伪协议脚本执行（如 ?redirect=javascript:alert(1)）。*/
  function gotoAfterLogin() {
    var params = new URLSearchParams(window.location.search);
    var target = String(params.get('redirect') || 'index.html');
    if (target.charAt(0) === '/') target = target.slice(1);
    if (!/^[\w\-./?=&%]+\.html([?#].*)?$/.test(target)) target = 'index.html';
    window.location.href = target;
  }

  /* ---------- 初始化 ---------- */
  function init() {
    if (guard()) return;
    renderHeaderAuth();
    updateCartBadge();
    refreshCartBadge();
  }

  window.ShopAuth = {
    TOKEN_KEY: TOKEN_KEY,
    MEMBER_KEY: MEMBER_KEY,
    GUEST_KEY: GUEST_KEY,
    getToken: getToken,
    getMember: getMember,
    isLogin: isLogin,
    setSession: setSession,
    clear: clear,
    logout: logout,
    getGuestCart: getGuestCart,
    setGuestCart: setGuestCart,
    clearGuestCart: clearGuestCart,
    guestCartCount: guestCartCount,
    mergeGuestCart: mergeGuestCart,
    updateCartBadge: updateCartBadge,
    refreshCartBadge: refreshCartBadge,
    renderHeaderAuth: renderHeaderAuth,
    guard: guard,
    gotoAfterLogin: gotoAfterLogin,
    redirectQuery: redirectQuery
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})(window, document);
