/* ============================================
   商品详情页脚本（specs/商城前台V1.2.spec.md §8.3）
   依赖 ui.js / api.js / auth.js / main.js
   规格联动 SKU：?id= 进入；全选规格才可加购/立即购买
   ============================================ */
(function (window, document) {
  'use strict';

  var S = window.ShopUtil;
  var U = window.ShopUI;
  var $ = function (id) { return document.getElementById(id); };
  var A = window.ShopAuth;

  var goodsId = parseInt(S.getParam('id'), 10) || 0;
  var goods = null;
  var specIds = [];
  var selected = {};
  var currentSku = null;
  var boundActions = false;
  var reviewPage = 0;
  var reviewLoaded = false;

  function esc(t) { return S.esc(t); }
  function vids(sku) {
    return (sku.specValueIds || []).map(function (x) { return String(x); });
  }
  function specNameOf(id) {
    var sp = (goods.specs || []).filter(function (s) { return String(s.id) === String(id); })[0];
    return sp ? sp.name : '';
  }
  function allChosen() {
    return specIds.every(function (id) { return selected[id] !== undefined && selected[id] !== ''; });
  }
  function chooseSku() {
    if (!allChosen()) return null;
    return goods.skus.find(function (sku) {
      var vs = vids(sku);
      return specIds.every(function (id) { return vs.indexOf(String(selected[id])) >= 0; });
    }) || null;
  }
  function defaultPrice() {
    var p = Infinity;
    (goods.skus || []).forEach(function (s) { p = Math.min(p, Number(s.price)); });
    return isFinite(p) && goods.skus.length ? p : Number(goods.price || 0);
  }

  /* ---------- 图片集 ---------- */
  function imagesOf() {
    return (goods.images || []).filter(function (im) { return im && im.url; });
  }
  function renderGallery() {
    var imgs = imagesOf();
    var mainSrc = imgs[0] ? imgs[0].url : '';
    var mainImg = '<img id="jsMainImg" alt="' + esc(goods.name) + '"'
      + (mainSrc ? ' src="' + esc(mainSrc) + '"' : '')
      + ' onerror="if(window.ShopUtil)ShopUtil.fallback(this)">';
    var thumbs = '<div class="thumb-list">';
    imgs.forEach(function (im, i) {
      thumbs += '<div class="thumb-item' + (i === 0 ? ' active' : '') + '" data-img="' + esc(im.url) + '">'
        + S.img(im.url, '') + '</div>';
    });
    thumbs += '</div>';
    $('jsGallery').innerHTML = '<div class="main-image">' + mainImg + '</div>' + thumbs;
  }

  /* ---------- 规格区 ---------- */
  function valueAvailable(specId, valueId) {
    var others = specIds.filter(function (id) { return String(id) !== String(specId); })
      .filter(function (id) { return selected[id] !== undefined && selected[id] !== ''; });
    return goods.skus.some(function (sku) {
      var vs = vids(sku);
      if (vs.indexOf(String(valueId)) < 0) return false;
      return others.every(function (id) { return vs.indexOf(String(selected[id])) >= 0; });
    });
  }

  function missingText() {
    var miss = specIds.filter(function (id) { return selected[id] === undefined || selected[id] === ''; })
      .map(specNameOf);
    return miss.length ? '请选择' + miss.join('、') : '';
  }

  function renderSpecs() {
    var wrap = $('jsSpecs');
    var html = '';
    goods.specs.forEach(function (sp) {
      var sid = String(sp.id);
      var chosen = selected[sid] !== undefined ? selected[sid] : '';
      var optHtml = '';
      (sp.values || []).forEach(function (v) {
        var active = String(v.id) === String(chosen);
        var dis = !active && !valueAvailable(sid, v.id);
        optHtml += '<span class="spec-option' + (active ? ' active' : '') + (dis ? ' disabled' : '') + '" data-sid="' + sid + '" data-vid="' + v.id + '">' + esc(v.value) + '</span>';
      });
      html += '<div class="spec-group"><div class="spec-label">' + esc(sp.name)
        + '<span class="selected-val">' + (chosen !== '' ? '' : '') + '</span></div>'
        + '<div class="spec-options">' + optHtml + '</div></div>';
    });
    wrap.innerHTML = html;
  }

  function updatePrice() {
    var cur = currentSku ? Number(currentSku.price) : defaultPrice();
    var oldRaw = Number(goods.marketPrice || 0);
    var old = oldRaw > cur ? oldRaw : (Number(goods.price || 0) > cur ? Number(goods.price) : 0);
    $('jsPrice').textContent = S.money(cur);
    if (old > 0) {
      $('jsOldPrice').textContent = '¥' + S.money(old);
      $('jsOldPrice').style.display = '';
    } else {
      $('jsOldPrice').style.display = 'none';
    }
    if (currentSku && currentSku.image) $('jsMainImg').src = currentSku.image;
    var tip = $('jsStockTip');
    if (!allChosen()) {
      tip.textContent = missingText() + '后加入购物车';
    } else if (!currentSku) {
      tip.textContent = '当前组合无货，请选择其他规格';
    } else if (currentSku.specText) {
      tip.textContent = '已选 ' + currentSku.specText + '，库存 ' + (currentSku.stock || 0) + ' 件';
    } else {
      tip.textContent = '库存 ' + (currentSku.stock || 0) + ' 件';
    }
    var can = !!currentSku && Number(currentSku.stock || 0) > 0;
    $('jsAddCart').disabled = !can;
    $('jsBuyNow').disabled = !can;
  }

  function sync() {
    currentSku = chooseSku();
    renderSpecs();
    updatePrice();
  }

  /* ---------- 商品主体 ---------- */
  function renderProduct() {
    var box = $('jsProductBox');
    box.innerHTML = '<div class="product-gallery" id="jsGallery"></div>'
      + '<div class="product-info">'
      + '<h1 class="product-title">' + esc(goods.name) + '</h1>'
      + '<p class="product-subtitle">' + esc(goods.subtitle || '') + '</p>'
      + '<div class="product-price-box"><div class="price-label">随心价</div>'
      + '<span class="current-price"><span class="yuan">¥</span><span id="jsPrice"></span></span>'
      + '<span class="original-price" id="jsOldPrice" style="display:none;"></span></div>'
      + '<div id="jsSpecs"></div>'
      + '<div class="quantity-row"><span class="qty-label">数量</span>'
      + '<div class="quantity-picker"><span class="qty-btn qty-minus disabled">-</span>'
      + '<input type="text" class="qty-input" value="1" readonly>'
      + '<span class="qty-btn qty-plus">+</span></div>'
      + '<span class="stock-tip" id="jsStockTip"></span></div>'
      + '<div class="action-buttons">'
      + '<button class="btn-add-cart" id="jsAddCart" disabled>加入购物车</button>'
      + '<button class="btn-buy-now" id="jsBuyNow" disabled>立即购买</button></div>'
      + '<div class="service-tags"><span>✓ 可提交售后申请</span><span>✓ 运费按模板计算</span>'
      + '<span>✓ 描述与实物一致</span></div>'
      + '<div style="font-size:12px;color:#999;margin-top:4px;">以上为演示站点示例说明，不代表真实商家承诺</div>'
      + '</div>';
    renderGallery();
    sync();
    bindActions();
  }

  /* ---------- Tab 区 ---------- */
  function renderTabs() {
    var count = Number(goods.commentCount || 0);
    $('jsTabBar').innerHTML =
      '<div class="detail-tab active" data-tab="intro">商品介绍</div>'
      + '<div class="detail-tab" data-tab="review">用户评价' + (count ? ' (' + count + ')' : '') + '</div>'
      + '<div class="detail-tab" data-tab="service">售后保障</div>';
    // detailHtml 由后台富文本编辑而来，插入前必须净化，防存储型 XSS
    $('tab-intro').innerHTML = '<h3>商品介绍</h3>'
      + (goods.detailHtml ? '<div class="intro-rich">' + S.sanitizeHtml(goods.detailHtml) + '</div>' : '<p>暂无详细介绍，敬请期待。</p>');
    $('tab-service').innerHTML = '<h3>售后保障</h3>'
      + '<p><strong>7天无理由退货：</strong>商品签收之日起 7 天内，在不影响二次销售的情况下可申请退货退款，请在「申请售后」中提交。</p>'
      + '<p><strong>售后处理：</strong>提交售后单后由客服在售后单内回复处理意见，进度可在「我的售后」查看。</p>'
      + '<p><strong>运费说明：</strong>运费按商品绑定的运费模板计算，满足模板包邮条件时免运费，结算页会实时展示运费金额。</p>'
      + '<p><strong>发货时效：</strong>正常情况下订单付款后 48 小时内发货，预售商品以商品详情页标注的发货时间为准。</p>'
      + '<p class="svc-note">以上为演示站点的示例服务说明，不代表任何真实商家承诺。</p>';
    $('tab-review').innerHTML = '<h3>用户评价</h3><p class="empty-hint">加载中…</p>';
    $('jsTabsWrap').style.display = '';
  }

  function showTab(name) {
    Array.prototype.forEach.call($('jsTabBar').children, function (t) {
      t.classList.toggle('active', t.dataset.tab === name);
    });
    ['intro', 'review', 'service'].forEach(function (n) {
      var el = $('tab-' + n);
      if (el) el.classList.toggle('active', n === name);
    });
    if (name === 'review' && !reviewLoaded) {
      reviewLoaded = true;
      reviewPage = 0;
      loadReviews();
    }
  }

  /* ---------- 评价 ---------- */
  function maskName(name) {
    var s = String(name || '匿名用户');
    if (s.length <= 1) return s;
    return s.charAt(0) + '***' + s.charAt(s.length - 1);
  }

  function starText(score) {
    var out = '';
    for (var i = 0; i < 5; i++) out += i < score ? '★' : '☆';
    return out;
  }

  function reviewHtml(item) {
    var imgs = '';
    var raw = String(item.images || '').trim();
    if (raw) {
      imgs = '<div class="review-imgs">' + raw.split(',').map(function (u) {
        return '<img src="' + esc(u.trim()) + '" alt="">';
      }).join('') + '</div>';
    }
    return '<div class="review-item">'
      + '<div class="review-user"><div class="review-avatar">' + esc(String(item.memberName || '匿').charAt(0)) + '</div>'
      + '<span class="review-name">' + esc(maskName(item.memberName)) + '</span>'
      + '<span class="review-stars">' + starText(Number(item.score || 5)) + '</span></div>'
      + '<p class="review-text">' + esc(item.content) + '</p>'
      + imgs
      + (item.reply ? '<div class="review-reply">商家回复：' + esc(item.reply) + '</div>' : '')
      + '<p class="review-date">' + esc(String(item.createdAt || '').slice(0, 10)) + '</p></div>';
  }

  function loadReviews() {
    ShopApi.goodsComments(goodsId, { page: reviewPage + 1, page_size: 5 }).then(function (res) {
      var d = res || {};
      var list = d.list || [];
      var total = Number(d.total || 0);
      reviewPage += 1;
      var rate = Number(goods && goods.goodRate ? goods.goodRate : 0);
      var box = $('tab-review');
      var body = '<h3>用户评价</h3>'
        + (rate > 0 ? '<div class="rate-summary"><span class="rate-num">' + rate + '%</span><span class="rate-text">好评率（共 ' + total + ' 条评价）</span></div>' : '');
      if (!total) {
        body += '<p class="empty-hint">暂无评价，快来抢沙发～</p>';
      } else {
        var first = reviewPage === 1;
        body += (first ? '' : '<div class="review-page">');
        body += list.map(reviewHtml).join('');
        if (reviewPage * 5 < total) {
          body += '<div class="review-more"><button id="jsReviewMore" type="button">加载更多</button></div>';
        }
        body += (first ? '' : '</div>');
      }
      box.innerHTML = body;
      var more = $('jsReviewMore');
      if (more) more.addEventListener('click', function () { loadReviews(); });
    }).catch(function () {
      $('tab-review').innerHTML = '<h3>用户评价</h3><p class="empty-hint">评价加载失败</p>';
    });
  }

  /* ---------- 加购 / 立即购买 ---------- */
  function currentQty() {
    var v = parseInt((document.querySelector('.qty-input') || {}).value, 10) || 1;
    var max = currentSku ? Number(currentSku.stock) : 1;
    return Math.max(1, Math.min(v, Math.max(max, 1)));
  }

  function addToCart() {
    if (!currentSku) { U.toast('请先选择完整规格', 'warn'); return; }
    if (Number(currentSku.stock || 0) <= 0) { U.toast('该规格暂时缺货', 'warn'); return; }
    var qty = currentQty();
    var jump = function () {
      window.location.href = 'add-to-cart.html?goodsId=' + goodsId + '&skuId=' + currentSku.id
        + '&quantity=' + qty + '&from=' + encodeURIComponent('detail.html?id=' + goodsId);
    };
    if (A.isLogin()) {
      ShopApi.addCart(goodsId, currentSku.id, qty).then(function () {
        A.refreshCartBadge();
        U.toast('已加入购物车', 'success');
        setTimeout(jump, 300);
      }).catch(function () {
        U.toast('加入购物车失败', 'error');
      });
    } else {
      var items = A.getGuestCart();
      var idx = -1;
      for (var i = 0; i < items.length; i++) {
        if (String(items[i].goodsId) === String(goodsId) && String(items[i].skuId) === String(currentSku.id)) idx = i;
      }
      var row = {
        goodsId: goodsId, skuId: currentSku.id, name: goods.name,
        specText: currentSku.specText || '',
        price: currentSku.price, image: currentSku.image || (imagesOf()[0] || {}).url || '',
        quantity: qty, selected: 1
      };
      if (idx >= 0) {
        items[idx].quantity = Math.min(items[idx].quantity + qty, Math.max(Number(currentSku.stock), 1));
      } else {
        items.push(row);
      }
      A.setGuestCart(items);
      U.toast('已加入购物车', 'success');
      setTimeout(jump, 300);
    }
  }

  function buyNow() {
    if (!currentSku) { U.toast('请先选择完整规格', 'warn'); return; }
    if (Number(currentSku.stock || 0) <= 0) { U.toast('该规格暂时缺货', 'warn'); return; }
    if (!A.isLogin()) {
      window.location.href = 'login.html?redirect=' + encodeURIComponent('detail.html?id=' + goodsId);
      return;
    }
    window.location.href = 'checkout.html?buy=1&goodsId=' + goodsId + '&skuId=' + currentSku.id + '&quantity=' + currentQty();
  }

  function bindActions() {
    if (boundActions) return;
    boundActions = true;
    $('jsSpecs').addEventListener('click', function (e) {
      var opt = e.target.closest('.spec-option');
      if (!opt || opt.classList.contains('disabled')) return;
      var sid = opt.dataset.sid;
      var vid = opt.dataset.vid;
      if (String(selected[sid] || '') === String(vid)) {
        delete selected[sid];
      } else {
        selected[sid] = String(vid);
      }
      sync();
    });
    $('jsGallery').addEventListener('click', function (e) {
      var t = e.target.closest('.thumb-item');
      if (!t) return;
      Array.prototype.forEach.call(document.querySelectorAll('.thumb-item'), function (x) { x.classList.remove('active'); });
      t.classList.add('active');
      $('jsMainImg').src = t.dataset.img;
    });
    $('jsAddCart').addEventListener('click', addToCart);
    $('jsBuyNow').addEventListener('click', buyNow);
    $('jsTabBar').addEventListener('click', function (e) {
      var t = e.target.closest('.detail-tab');
      if (t) showTab(t.dataset.tab);
    });
  }

  /* ---------- 猜你喜欢 ---------- */
  function recommendCard(g) {
    return '<a class="product-card" href="detail.html?id=' + g.id + '">'
      + '<div class="product-image">' + S.img(g.image, g.name) + '</div>'
      + '<div class="product-name">' + esc(g.name) + '</div>'
      + '<div class="product-price price">' + S.money(Number(g.price)) + '<span class="yuan">元起</span></div></a>';
  }
  function loadRecommend() {
    ShopApi.goods({ is_recommend: 1, page_size: 5 }).then(function (res) {
      var list = (res || {}).list || [];
      if (!list.length) return;
      $('jsRecommend').innerHTML = list.map(recommendCard).join('');
      $('jsRecommendWrap').style.display = '';
    }).catch(function () {});
  }

  /* ---------- 初始化 ---------- */
  function loadDetail() {
    if (!goodsId) {
      $('jsProductBox').innerHTML = '<div class="page-error">缺少商品参数（id）</div>';
      return;
    }
    ShopApi.goodsDetail(goodsId).then(function (res) {
      goods = res;
      specIds = (goods.specs || []).map(function (s) { return String(s.id); });
      $('jsCrumb').textContent = goods.name;
      document.title = goods.name + ' - 随心商城';
      renderProduct();
      renderTabs();
      showTab('intro');
      loadRecommend();
    }).catch(function () {
      $('jsProductBox').innerHTML = '<div class="page-error">商品不存在或已下架</div>';
    });
  }

  loadDetail();
})(window, document);
