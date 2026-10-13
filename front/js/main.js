/* ============================================
   随心商城 - 公共交互脚本
   ============================================ */

(function() {
  'use strict';

  /* ---------- 购物车数据管理（localStorage） ---------- */
  const Cart = {
    KEY: 'shop_cart_guest',

    getItems() {
      try {
        return JSON.parse(localStorage.getItem(this.KEY)) || [];
      } catch (e) {
        return [];
      }
    },

    saveItems(items) {
      localStorage.setItem(this.KEY, JSON.stringify(items));
      this.updateCartCount();
    },

    addItem(product) {
      const items = this.getItems();
      const existing = items.find(item => item.id === product.id && item.version === product.version && item.color === product.color);
      if (existing) {
        existing.quantity += product.quantity || 1;
      } else {
        items.push({
          id: product.id,
          name: product.name,
          price: product.price,
          image: product.image,
          version: product.version || '',
          color: product.color || '',
          quantity: product.quantity || 1,
          selected: true
        });
      }
      this.saveItems(items);
    },

    removeItem(id, version, color) {
      let items = this.getItems();
      items = items.filter(item => !(item.id === id && item.version === version && item.color === color));
      this.saveItems(items);
    },

    updateQuantity(id, version, color, quantity) {
      const items = this.getItems();
      const item = items.find(i => i.id === id && i.version === version && i.color === color);
      if (item) {
        item.quantity = Math.max(1, quantity);
        this.saveItems(items);
      }
    },

    toggleSelect(id, version, color) {
      const items = this.getItems();
      const item = items.find(i => i.id === id && i.version === version && i.color === color);
      if (item) {
        item.selected = !item.selected;
        this.saveItems(items);
      }
    },

    toggleSelectAll(selected) {
      const items = this.getItems();
      items.forEach(item => item.selected = selected);
      this.saveItems(items);
    },

    getSelectedItems() {
      return this.getItems().filter(item => item.selected);
    },

    getTotalCount() {
      return this.getItems().reduce((sum, item) => sum + item.quantity, 0);
    },

    getSelectedTotal() {
      return this.getSelectedItems().reduce((sum, item) => sum + item.price * item.quantity, 0);
    },

    getSelectedCount() {
      return this.getSelectedItems().reduce((sum, item) => sum + item.quantity, 0);
    },

    clear() {
      this.saveItems([]);
    },

    updateCartCount() {
      const count = this.getTotalCount();
      document.querySelectorAll('.cart-count').forEach(el => {
        el.textContent = count;
      });
    }
  };

  // 暴露到全局
  window.ShopCart = Cart;

  /* ---------- Banner轮播 ---------- */
  function initBanner() {
    const banners = document.querySelectorAll('.banner');
    banners.forEach(banner => {
      if (banner.dataset.bound === '1') return;
      const slides = banner.querySelectorAll('.banner-slide');
      const dots = banner.querySelectorAll('.banner-dots .dot');
      const prevBtn = banner.querySelector('.banner-arrow.prev');
      const nextBtn = banner.querySelector('.banner-arrow.next');
      if (slides.length === 0) return;
      // S1：数据未就绪时的 loading 占位不绑定（page-home.js 渲染真实轮播后自行 init）
      if (slides.length === 1 && slides[0].classList.contains('js-banner-loading')) return;
      banner.dataset.bound = '1';

      let current = 0;
      let timer = null;

      function show(index) {
        slides.forEach((s, i) => s.classList.toggle('active', i === index));
        dots.forEach((d, i) => d.classList.toggle('active', i === index));
        current = index;
      }

      function next() {
        show((current + 1) % slides.length);
      }

      function prev() {
        show((current - 1 + slides.length) % slides.length);
      }

      function startAuto() {
        stopAuto();
        timer = setInterval(next, 5000);
      }

      function stopAuto() {
        if (timer) clearInterval(timer);
      }

      dots.forEach((dot, i) => {
        dot.addEventListener('click', () => { show(i); startAuto(); });
      });

      if (nextBtn) nextBtn.addEventListener('click', () => { next(); startAuto(); });
      if (prevBtn) prevBtn.addEventListener('click', () => { prev(); startAuto(); });

      banner.addEventListener('mouseenter', stopAuto);
      banner.addEventListener('mouseleave', startAuto);

      startAuto();
    });
  }

  window.ShopBanner = { init: initBanner };

  /* ---------- 分类菜单弹出（仅点击展开，hover 不展开；） ----------
     点击父分类=展开/再点收起/点其他父项切换；点击面板内叶子走默认跳转；
     点击菜单外任意处收起。任一时刻仅一个分类项 active（面板由 CSS 控制显隐）。 */
  window.ShopCategory = { init: initCategoryMenu };
  function initCategoryMenu() {
    document.querySelectorAll('.category-menu').forEach(menu => {
      if (menu.dataset.catBound) return;
      menu.dataset.catBound = '1';

      let current = null;

      function setActive(item) {
        if (current === item) return;
        current = item;
        menu.querySelectorAll('.menu-item').forEach(m => m.classList.remove('active'));
        if (item) {
          const sub = item.querySelector(':scope > .category-submenu');
          if (sub) item.classList.add('active');
        }
      }

      // 点击父分类项=展开（不跳转），再点同一项=收起，点其他父项=切换
      menu.addEventListener('click', (e) => {
        const item = e.target.closest ? e.target.closest('.menu-item') : null;
        if (!item || !menu.contains(item)) return;
        if (e.target.closest('.category-submenu')) return;
        if (item.classList.contains('has-children')) {
          e.preventDefault();
          setActive(current === item ? null : item);
        }
      });

      // 点击菜单（含面板）以外任意处收起
      document.addEventListener('click', (e) => {
        if (!menu.contains(e.target)) setActive(null);
      });
    });
  }

  /* ---------- 数量加减器 ---------- */
  function initQuantityPicker() {
    document.addEventListener('click', function(e) {
      const btn = e.target.closest('.qty-btn');
      if (!btn || btn.classList.contains('disabled')) return;

      const picker = btn.closest('.quantity-picker');
      const input = picker.querySelector('.qty-input');
      let val = parseInt(input.value) || 1;

      if (btn.classList.contains('qty-minus')) {
        val = Math.max(1, val - 1);
      } else if (btn.classList.contains('qty-plus')) {
        val += 1;
      }

      input.value = val;
      updateMinusBtn(picker);

      // 触发自定义事件
      picker.dispatchEvent(new CustomEvent('quantity-change', { detail: { quantity: val } }));
    });
  }

  function updateMinusBtn(picker) {
    const input = picker.querySelector('.qty-input');
    const minusBtn = picker.querySelector('.qty-minus');
    if (parseInt(input.value) <= 1) {
      minusBtn.classList.add('disabled');
    } else {
      minusBtn.classList.remove('disabled');
    }
  }

  /* ---------- 模态弹窗 ---------- */
  const Modal = {
    open(id) {
      const modal = document.getElementById(id);
      const overlay = document.querySelector('.modal-overlay');
      if (modal) modal.classList.add('active');
      if (overlay) overlay.classList.add('active');
      document.body.style.overflow = 'hidden';
    },

    close(id) {
      const modal = document.getElementById(id);
      const overlay = document.querySelector('.modal-overlay');
      if (modal) modal.classList.remove('active');
      if (overlay) overlay.classList.remove('active');
      document.body.style.overflow = '';
    },

    closeAll() {
      document.querySelectorAll('.modal.active').forEach(m => m.classList.remove('active'));
      document.querySelectorAll('.modal-overlay.active').forEach(o => o.classList.remove('active'));
      document.body.style.overflow = '';
    }
  };

  window.ShopModal = Modal;

  // 弹窗关闭按钮
  function initModals() {
    document.addEventListener('click', function(e) {
      // 关闭按钮
      if (e.target.closest('.modal-close')) {
        Modal.closeAll();
        return;
      }
      // 点击遮罩关闭
      if (e.target.classList.contains('modal-overlay')) {
        Modal.closeAll();
      }
    });

    // ESC关闭
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape') Modal.closeAll();
    });
  }

  /* ---------- Tab切换 ---------- */
  function initTabs() {
    document.addEventListener('click', function(e) {
      const tab = e.target.closest('.tab');
      if (!tab) return;

      const tabGroup = tab.parentElement;
      tabGroup.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');

      // 触发自定义事件
      tabGroup.dispatchEvent(new CustomEvent('tab-change', { detail: { tab: tab.textContent.trim() } }));
    });
  }

  /* ---------- 搜索框 ---------- */
  function initSearch() {
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Enter' && e.target.classList.contains('search-input')) {
        const keyword = e.target.value.trim();
        if (keyword) {
          window.location.href = 'search.html?keyword=' + encodeURIComponent(keyword);
        }
      }
    });

    document.addEventListener('click', function(e) {
      if (e.target.closest('.search-btn')) {
        const box = e.target.closest('.search-box');
        const input = box.querySelector('.search-input');
        const keyword = input.value.trim();
        if (keyword) {
          window.location.href = 'search.html?keyword=' + encodeURIComponent(keyword);
        }
      }
    });
  }

  /* ---------- 登录/注册表单验证 ---------- */
  function initAuthForms() {
    // 协议复选框控制按钮状态
    document.addEventListener('change', function(e) {
      if (e.target.id === 'agree-checkbox') {
        const btn = document.querySelector('.auth-submit');
        if (btn) {
          if (e.target.checked) {
            btn.classList.remove('disabled');
            btn.disabled = false;
          } else {
            btn.classList.add('disabled');
            btn.disabled = true;
          }
        }
      }
    });

    // 密码显示/隐藏
    document.addEventListener('click', function(e) {
      const toggle = e.target.closest('.password-toggle');
      if (!toggle) return;
      const input = toggle.parentElement.querySelector('input');
      if (input.type === 'password') {
        input.type = 'text';
        toggle.textContent = '🙈';
      } else {
        input.type = 'password';
        toggle.textContent = '👁';
      }
    });

    // 注：验证码倒计时已移交 register.html 内联逻辑（真实调用 /auth/send-code），此处不再绑定
  }

  /* ---------- 商品详情页规格选择 ---------- */
  function initProductDetail() {
    const versionOptions = document.querySelectorAll('.version-option');
    const colorOptions = document.querySelectorAll('.color-option');

    function updateSelected() {
      const version = document.querySelector('.version-option.active');
      const color = document.querySelector('.color-option.active');
      const summary = document.querySelector('.selected-summary');
      const totalEl = document.querySelector('.total-price');
      const addBtn = document.querySelector('.add-to-cart-btn');

      if (version && color && summary) {
        const versionText = version.textContent.trim();
        const colorText = color.textContent.trim();
        const price = parseFloat(version.dataset.price) || 0;
        summary.textContent = versionText.split(' ')[0] + ' ' + colorText;
        if (totalEl) totalEl.textContent = price.toFixed(0);
      }

      if (addBtn) {
        if (version && color) {
          addBtn.classList.remove('disabled');
          addBtn.disabled = false;
        } else {
          addBtn.classList.add('disabled');
          addBtn.disabled = true;
        }
      }
    }

    versionOptions.forEach(opt => {
      opt.addEventListener('click', () => {
        versionOptions.forEach(o => o.classList.remove('active'));
        opt.classList.add('active');
        updateSelected();
      });
    });

    colorOptions.forEach(opt => {
      opt.addEventListener('click', () => {
        colorOptions.forEach(o => o.classList.remove('active'));
        opt.classList.add('active');
        updateSelected();
      });
    });

    // 加入购物车
    document.addEventListener('click', function(e) {
      const btn = e.target.closest('.add-to-cart-btn');
      if (!btn || btn.classList.contains('disabled')) return;

      const version = document.querySelector('.version-option.active');
      const color = document.querySelector('.color-option.active');
      const nameEl = document.querySelector('.product-title');
      const priceEl = document.querySelector('.total-price');
      const imgEl = document.querySelector('.main-image img');

      if (version && color) {
        Cart.addItem({
          id: 'product_' + Date.now(),
          name: nameEl ? nameEl.textContent.trim() : '商品',
          price: parseFloat(priceEl?.textContent) || 0,
          image: imgEl?.src || '',
          version: version.textContent.trim().split(' ')[0],
          color: color.textContent.trim(),
          quantity: 1
        });
        window.location.href = 'add-to-cart.html';
      }
    });
  }

  /* ---------- 购物车页面逻辑 ---------- */
  function initCartPage() {
    const cartTable = document.querySelector('.cart-table');
    if (!cartTable) return;

    function render() {
      const items = Cart.getItems();
      const tbody = cartTable.querySelector('tbody');
      const emptyEl = document.querySelector('.cart-empty');

      if (items.length === 0) {
        if (emptyEl) emptyEl.style.display = 'block';
        cartTable.style.display = 'none';
        return;
      }

      if (emptyEl) emptyEl.style.display = 'none';
      cartTable.style.display = '';

      // 购物车数据会经接口回流（会员服务端车合并），所有插值必须转义
      const esc = (v) => String(v == null ? '' : v).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
      tbody.innerHTML = items.map(item => `
        <tr class="cart-row" data-id="${esc(item.id)}" data-version="${esc(item.version)}" data-color="${esc(item.color)}">
          <td class="col-check">
            <label class="checkbox">
              <input type="checkbox" ${item.selected ? 'checked' : ''} class="row-checkbox">
              <span class="checkbox-box"></span>
            </label>
          </td>
          <td class="col-product">
            <img src="${esc(item.image)}" alt="${esc(item.name)}" class="cart-thumb">
            <span class="cart-name">${esc(item.name)} ${esc(item.version)} ${esc(item.color)}</span>
          </td>
          <td class="col-price">${item.price.toFixed(0)}元</td>
          <td class="col-quantity">
            <div class="quantity-picker">
              <span class="qty-btn qty-minus ${item.quantity <= 1 ? 'disabled' : ''}">-</span>
              <input type="text" class="qty-input" value="${esc(item.quantity)}" readonly>
              <span class="qty-btn qty-plus">+</span>
            </div>
          </td>
          <td class="col-subtotal price">${(item.price * item.quantity).toFixed(0)}元</td>
          <td class="col-action"><span class="delete-btn" title="删除">×</span></td>
        </tr>
      `).join('');

      updateTotals();
    }

    function updateTotals() {
      const items = Cart.getItems();
      const allSelected = items.length > 0 && items.every(i => i.selected);
      const selectAll = document.querySelector('.select-all-checkbox');
      if (selectAll) selectAll.checked = allSelected;

      const selectedCount = Cart.getSelectedCount();
      const selectedTotal = Cart.getSelectedTotal();

      document.querySelectorAll('.selected-count').forEach(el => el.textContent = selectedCount);
      document.querySelectorAll('.cart-total').forEach(el => el.textContent = selectedTotal.toFixed(0));
    }

    // 全选
    document.addEventListener('change', function(e) {
      if (e.target.classList.contains('select-all-checkbox')) {
        Cart.toggleSelectAll(e.target.checked);
        render();
      }
      if (e.target.classList.contains('row-checkbox')) {
        const row = e.target.closest('.cart-row');
        Cart.toggleSelect(row.dataset.id, row.dataset.version, row.dataset.color);
        updateTotals();
      }
    });

    // 数量变化
    document.addEventListener('quantity-change', function(e) {
      const picker = e.target.closest('.quantity-picker');
      if (!picker) return;
      const row = picker.closest('.cart-row');
      if (!row) return;
      Cart.updateQuantity(row.dataset.id, row.dataset.version, row.dataset.color, e.detail.quantity);
      const items = Cart.getItems();
      const item = items.find(i => i.id === row.dataset.id && i.version === row.dataset.version && i.color === row.dataset.color);
      if (item) {
        row.querySelector('.col-subtotal').textContent = (item.price * item.quantity).toFixed(0) + '元';
      }
      updateTotals();
    });

    // 删除
    document.addEventListener('click', function(e) {
      if (e.target.classList.contains('delete-btn')) {
        if (!confirm('确定要删除该商品吗？')) return;
        const row = e.target.closest('.cart-row');
        Cart.removeItem(row.dataset.id, row.dataset.version, row.dataset.color);
        render();
      }
    });

    // 去结算
    document.addEventListener('click', function(e) {
      if (e.target.closest('.checkout-btn')) {
        if (Cart.getSelectedCount() === 0) {
          alert('请先选择商品');
          return;
        }
        window.location.href = 'checkout.html';
      }
    });

    render();
  }

  /* ---------- 支付倒计时 ---------- */
  function initPaymentCountdown() {
    const countdownEl = document.querySelector('.payment-countdown');
    if (!countdownEl) return;

    let totalSeconds = 14 * 60; // 14分钟

    function update() {
      const hours = Math.floor(totalSeconds / 3600);
      const minutes = Math.floor((totalSeconds % 3600) / 60);
      countdownEl.textContent = hours + '小时 ' + minutes + '分';
      if (totalSeconds <= 60) {
        countdownEl.style.color = '#E53935';
      }
      if (totalSeconds <= 0) {
        clearInterval(timer);
        alert('订单已超时取消');
        window.location.href = 'orders.html';
      }
      totalSeconds--;
    }

    update();
    const timer = setInterval(update, 1000);
  }

  /* ---------- 顶部主导航接真实分类（2026-10-05 改"产品线口径"）
     1) 每个导航项固定映射到它所属的一级分类（根）——点进去看该产品线全部商品，
        不允许再出现同层级导航落到叶子/二级造成的"点笔记本=只给笔记本电脑"的偏差；
     2) 列表页当前分类所在产品线对应的导航项自动高亮（产品线入口口径）。 */
  const NAV_ALIAS = {
    '手机': '手机', '智能手机': '手机', '电视': '电视',
    '笔记本': '笔记本', '平板': '平板', '家电': '家用电器', '路由器': '路由器'
  };

  function flattenCategories(nodes, out) {
    (nodes || []).forEach(function (n) { out.push(n); flattenCategories(n.children, out); });
    return out;
  }

  function indexCategories(flat) {
    var map = {};
    flat.forEach(function (c) { map[String(c.id)] = c; });
    return map;
  }

  // 逐级上溯到一级分类（parentId 为 0 或父节点缺失即停）
  function rootOf(map, id) {
    var cur = map[String(id)];
    var guard = 0;
    while (cur && cur.parentId && map[String(cur.parentId)] && guard++ < 12) {
      cur = map[String(cur.parentId)];
    }
    return cur || null;
  }

  // URL 上记录的“点了哪个导航项”（同一产品线多入口时用它在刷新/回退后还原高亮）
  function navParam() {
    var m = (window.location.search || '').match(/[?&]nav=([^&]*)/);
    return m ? decodeURIComponent((m[1] || '').replace(/\+/g, ' ')) : '';
  }

  function currentRootId(map) {
    var m = (window.location.search || '').match(/categoryId=(\d+)/);
    if (!m) return null;
    var root = rootOf(map, m[1]);
    return root ? String(root.id) : null;
  }

  function initMainNav() {
    var nav = document.querySelector('.main-nav');
    if (!nav || !window.ShopApi || !ShopApi.categories) return;
    ShopApi.categories().then(function (res) {
      var flat = flattenCategories((res || {}).list || res || [], []);
      if (!flat.length) return;
      var linked = {};
      nav.querySelectorAll('a').forEach(function (a) {
        var key = NAV_ALIAS[(a.textContent || '').trim()];
        if (!key) return;
        var hit = flat.find(function (c) { return c.name === key; })
          || flat.find(function (c) { return (c.name || '').indexOf(key) >= 0; });
        if (!hit) return;
        var root = rootOf(indexCategories(flat), hit.id);
        if (!root) return;
        var label = (a.textContent || '').trim();
        a.setAttribute('href', 'search.html?categoryId=' + root.id + '&nav=' + encodeURIComponent(label));
        a.dataset.catId = String(root.id);
        // 同一产品线存在多个入口（手机 / 智能手机）时保留首个，避免后者覆盖导致高亮串位
        if (!linked[String(root.id)]) linked[String(root.id)] = a;
      });
      // 高亮：优先还原“点过的那一项”，否则回落该产品线的首个入口
      var wanted = navParam();
      var target = null;
      if (wanted) {
        nav.querySelectorAll('a').forEach(function (a) {
          if (!target && (a.textContent || '').trim() === wanted) target = a;
        });
      }
      if (!target) {
        var rid = currentRootId(indexCategories(flat));
        if (rid && linked[rid]) target = linked[rid];
      }
      if (target) target.classList.add('active');
    }).catch(function () {});
  }

  /* ---------- 页面初始化 ---------- */
  document.addEventListener('DOMContentLoaded', function() {
    Cart.updateCartCount();
    initMainNav();
    initBanner();
    initCategoryMenu();
    initQuantityPicker();
    initModals();
    initTabs();
    initSearch();
    initAuthForms();
    initProductDetail();
    initCartPage();
    initPaymentCountdown();

    // 初始化所有数量加减器的减号按钮状态
    document.querySelectorAll('.quantity-picker').forEach(updateMinusBtn);
  });
})();
