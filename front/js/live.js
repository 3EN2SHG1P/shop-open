/* ============================================
   商城前台 · 实时自动更新（specs/商城前台V1.2.spec.md §9.5）
   - 轮询后端 GET /api/v1/shop/live/version（默认 4s）
   - 返回 {assets:{css,html,js}, data}
   - 仅 css 指纹变化 → 无感热更样式表（不整页刷新）
   - html/js/data 指纹变化 → 自动整页刷新（页面可见且无输入/下拉聚焦时不打断）
   - 关闭：URL 加 ?live=0，或 localStorage 设 shop_live='off'
   - 间隔：localStorage shop_live_interval（毫秒，默认 4000）
   ============================================ */
(function (window) {
  'use strict';

  var DEFAULT_BASE = window.location.protocol + '//' + (window.location.hostname || '127.0.0.1') + ':8001';
  var LS_SIG = 'shop_live_sig';
  var LS_CSS = 'shop_live_css';
  var interval = parseInt(window.localStorage.getItem('shop_live_interval'), 10) || 4000;
  var params = new URLSearchParams(window.location.search);
  if (window.localStorage.getItem('shop_live') === 'off' || params.get('live') === '0') return;

  function baseUrl() {
    var raw = window.SHOP_API_BASE || window.localStorage.getItem('shop_api_base') || DEFAULT_BASE;
    return String(raw).replace(/\/+$/, '');
  }

  function canRefresh() {
    if (document.visibilityState !== 'visible') return false;
    var el = document.activeElement;
    if (!el) return true;
    var tag = el.tagName;
    return !(tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || el.isContentEditable);
  }

  function hotReloadCss() {
    var stamp = 'v=' + Date.now();
    var links = document.querySelectorAll('link[rel="stylesheet"]');
    for (var i = 0; i < links.length; i++) {
      var href = (links[i].getAttribute('href') || '').split('?')[0];
      if (!href || href.indexOf('.css') === -1) continue;
      links[i].setAttribute('href', href + '?' + stamp);
    }
  }

  function tick() {
    var url = baseUrl() + '/api/v1/shop/live/version';
    window.fetch(url, { method: 'GET', cache: 'no-store' })
      .then(function (resp) { return resp.json(); })
      .then(function (json) {
        if (!json || json.code !== 0 || !json.data) return;
        var assets = json.data.assets || {};
        var cssSig = assets.css || '';
        var restSig = [assets.html || '', assets.js || '', json.data.data || ''].join('|');
        var storedCss = window.localStorage.getItem(LS_CSS) || '';
        var storedSig = window.localStorage.getItem(LS_SIG) || '';

        // 结构/数据变化 → 整页自动刷新
        if (storedSig && restSig && restSig !== storedSig) {
          window.localStorage.setItem(LS_SIG, restSig);
          if (canRefresh()) window.location.reload();
          return;
        }
        // 仅样式变化 → 无感热更 css
        if (storedCss && cssSig && cssSig !== storedCss) {
          window.localStorage.setItem(LS_CSS, cssSig);
          hotReloadCss();
          return;
        }
        // 首次访问建立基线
        if (!storedSig) window.localStorage.setItem(LS_SIG, restSig);
        if (!storedCss) window.localStorage.setItem(LS_CSS, cssSig);
      })
      .catch(function () { /* 后端未就绪时静默 */ });
  }

  setTimeout(function () {
    tick();
    window.setInterval(tick, interval);
  }, 800);
})(window);
