/* ============================================
   加入购物车成功页脚本（specs/商城前台V1.2.spec.md §8.4）
   - 读 ?goodsId=&skuId=&quantity=&from= 渲染刚加购商品快照（服务端真值）
   - 继续购物 → from 来源；去购物车结算 → cart.html
   - 猜你喜欢 → GET /goods?is_recommend=1
   依赖：ui.js / api.js / auth.js
   ============================================ */
(function (window, document) {
  'use strict';

  var S = window.ShopUtil;
  var Api = window.ShopApi;

  var goodsId = Number(S.getParam('goodsId')) || 0;
  var skuId = Number(S.getParam('skuId')) || 0;
  var quantity = Number(S.getParam('quantity')) || 1;
  var info = document.getElementById('jsInfo');
  var cont = document.getElementById('jsContinue');

  function esc(t) { return S.esc(t); }

  function safeFrom(raw) {
    var s = String(raw || '');
    return /^[\w\-./?=&%]+\.html([?#].*)?$/.test(s) ? s : 'index.html';
  }

  function mainImage(goods) {
    var imgs = (goods.images || []).filter(function (im) { return im && im.url; });
    return imgs.length ? imgs[0].url : '';
  }

  function renderSnapshot(goods, sku) {
    var price = sku ? Number(sku.price) : Number(goods.price || 0);
    var image = (sku && sku.image) ? sku.image : mainImage(goods);
    var spec = sku ? (sku.specText || '') : '';
    info.innerHTML =
      '<img src="' + esc(image) + '" alt="' + esc(goods.name) + '"'
      + ' onerror="if(window.ShopUtil)ShopUtil.fallback(this)">'
      + '<div class="info-text">'
      + '<h3><a href="detail.html?id=' + goods.id + '">' + esc(goods.name) + '</a></h3>'
      + (spec ? '<div class="spec">规格：' + esc(spec) + '</div>' : '')
      + '<div class="spec">数量：' + quantity + '</div>'
      + '<div class="price">¥' + S.money(price) + '</div>'
      + '</div>';
  }

  function renderError(text) {
    info.innerHTML = '<div class="info-text"><h3>' + esc(text) + '</h3>'
      + '<div class="spec">请返回商品详情重新加入购物车。</div></div>';
  }

  function recommendCard(g) {
    return '<a class="product-card" href="detail.html?id=' + g.id + '">'
      + '<div class="product-image">' + S.img(g.image, g.name) + '</div>'
      + '<div class="product-name">' + esc(g.name) + '</div>'
      + '<div class="product-price price">' + S.money(Number(g.price)) + '<span class="yuan">元起</span></div></a>';
  }

  function loadRecommend() {
    var wrap = document.getElementById('jsGuess');
    if (!wrap) return;
    Api.goods({ is_recommend: 1, page_size: 5 }).then(function (res) {
      var list = (res || {}).list || [];
      if (!list.length) return;
      wrap.innerHTML = list.map(recommendCard).join('');
    }).catch(function () {});
  }

  if (cont) {
    cont.setAttribute('href', safeFrom(S.getParam('from')));
  }

  if (!goodsId) {
    renderError('缺少商品参数');
    loadRecommend();
    return;
  }

  Api.goodsDetail(goodsId).then(function (goods) {
    var sku = (goods.skus || []).filter(function (s) { return String(s.id) === String(skuId); })[0] || null;
    renderSnapshot(goods, sku);
  }).catch(function () {
    renderError('商品不存在或已下架');
  });

  loadRecommend();
})(window, document);
