/* ============================================
   商城后台管理系统 - 公共 JS
   ============================================ */

(function () {
  'use strict';

  let COMMON_SRC = '';
  try {
    COMMON_SRC = document.currentScript && document.currentScript.src ? document.currentScript.src : '';
  } catch (e) { }

  const SESSION_KEY = 'mall_admin_session';
  const API_BASE = '/api/v1';
  let memorySession = null;

  function getSession() {
    try {
      const raw = localStorage.getItem(SESSION_KEY);
      if (raw) {
        return JSON.parse(raw) || null;
      }
    } catch (e) { }
    return memorySession;
  }

  function setSession(user) {
    memorySession = user;
    try {
      localStorage.setItem(SESSION_KEY, JSON.stringify(user));
    } catch (e) { }
  }

  function clearSession() {
    memorySession = null;
    try {
      localStorage.removeItem(SESSION_KEY);
    } catch (e) { }
  }

  function escHtml(s) {
    return String(s === null || s === undefined ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function fmtTime(v) {
    if (v === null || v === undefined || v === '') return '-';
    const s = String(v).trim();
    // ISO 字符串（浏览器 Date 解析：带 tz 的 +08:00/Z 按基准；naive 按本机时区）
    if (s.indexOf('T') !== -1) {
      const d = new Date(s);
      if (!isNaN(d.getTime())) return _fmtYmdHms(d);
    }
    // naive 字符串：业务统一为东八区（CST +08:00）落库，按此基准解析后转本机时区显示
    const m = s.match(/^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2}):(\d{2})/);
    if (m) {
      const d = new Date(m[1] + '-' + m[2] + '-' + m[3] + 'T' + m[4] + ':' + m[5] + ':' + m[6] + '+08:00');
      if (!isNaN(d.getTime())) return _fmtYmdHms(d);
    }
    return s.slice(0, 19);
  }
  function _fmtYmdHms(d) {
    const p = function (n) { return n < 10 ? '0' + n : '' + n; };
    return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate())
      + ' ' + p(d.getHours()) + ':' + p(d.getMinutes()) + ':' + p(d.getSeconds());
  }

  function qs(params) {
    if (!params) return '';
    const parts = [];
    for (const k in params) {
      const v = params[k];
      if (v === undefined || v === null || v === '') continue;
      parts.push(encodeURIComponent(k) + '=' + encodeURIComponent(v));
    }
    return parts.length ? '?' + parts.join('&') : '';
  }

  function menuPrefix() {
    const segs = function (p) { return p.split('/').filter(Boolean); };
    if (COMMON_SRC) {
      const m = COMMON_SRC.match(/^[a-z][a-z0-9+.-]*:\/\/[^/]*(\/.*)$/i);
      const comSegs = m ? segs(m[1]) : [];
      comSegs.pop();
      comSegs.pop();
      const docSegs = segs(location.pathname);
      docSegs.pop();
      let extra = Math.max(0, docSegs.length - comSegs.length);
      let prefix = '';
      while (extra--) prefix += '../';
      return prefix;
    }
    return location.pathname.indexOf('/pages/') !== -1 ? '../../' : '';
  }

  /* 菜单根（绝对路径，以 / 开头、/ 结尾）。menuData 的 href 均相对该根；用绝对路径可避免 SPA 切页后相对链接随 URL 深度漂移 */
  function menuRoot() {
    if (COMMON_SRC) {
      const m = COMMON_SRC.match(/^[a-z][a-z0-9+.-]*:\/\/[^/]*(\/.*)$/i);
      if (m) {
        const s = m[1].split('/').filter(Boolean);
        s.pop();
        s.pop();
        return '/' + s.join('/') + '/';
      }
    }
    return '/';
  }

  function token() {
    const s = getSession();
    return s && s.token ? s.token : '';
  }

  function permissions() {
    const s = getSession();
    return s && Array.isArray(s.permissions) ? s.permissions : null;
  }

  function can(code) {
    const perms = permissions();
    if (!perms) return false;
    return perms.indexOf(code) !== -1;
  }

  function showToast(message, type) {
    type = type || 'info';
    const conf = {
      success: { icon: '✓', bg: 'linear-gradient(135deg, #73D13D, #52C41A)' },
      error: { icon: '✕', bg: 'linear-gradient(135deg, #FF7875, #FF4D4F)' },
      warning: { icon: '!', bg: 'linear-gradient(135deg, #FFC53D, #FAAD14)' },
      info: { icon: 'i', bg: 'linear-gradient(135deg, var(--primary-light), var(--primary))' }
    };
    const c = conf[type] || conf.info;
    const idx = document.querySelectorAll('.admin-toast').length;
    const toast = document.createElement('div');
    toast.className = 'admin-toast';
    // 顶栏下方右侧弹出，避免与顶栏账户信息重叠
    toast.style.top = (76 + idx * 68) + 'px';
    toast.innerHTML = '<span class="toast-icon" style="background:' + c.bg + '">' + c.icon + '</span><span class="toast-msg">' + escHtml(message) + '</span>';
    document.body.appendChild(toast);
    setTimeout(() => {
      toast.classList.add('hide');
      setTimeout(() => { if (toast.parentNode) toast.remove(); }, 320);
    }, 2800);
  }

  async function request(method, url, data, opts) {
    opts = opts || {};
    const headers = {};
    if (data !== undefined) headers['Content-Type'] = 'application/json';
    const t = token();
    if (t) headers['Authorization'] = 'Bearer ' + t;
    const ctrl = (typeof AbortController !== 'undefined') ? new AbortController() : null;
    const timeoutMs = opts.timeout || 15000;
    let timer = null;
    if (ctrl) timer = setTimeout(function () { ctrl.abort(); }, timeoutMs);
    let resp;
    try {
      resp = await fetch(url, {
        method: method,
        headers: headers,
        body: data !== undefined ? JSON.stringify(data) : undefined,
        signal: ctrl ? ctrl.signal : undefined
      });
    } catch (e) {
      showToast(e && e.name === 'AbortError' ? '请求超时，请重试' : '网络异常，请确认后端服务已启动', 'error');
      throw e;
    } finally {
      if (ctrl && timer) clearTimeout(timer);
    }
    let json = null;
    try { json = await resp.json(); } catch (e) { json = null; }
    const msg = (json && json.message) || ('请求失败(' + resp.status + ')');
    const authExpired = resp.status === 401 || (json && (json.code === 1001 || json.code === 1002));
    if (authExpired) {
      if (opts.redirect401 !== false) {
        clearSession();
        showToast('登录状态已失效，请重新登录', 'warning');
        setTimeout(() => { window.location.replace(menuRoot() + 'login.html'); }, 500);
      } else {
        showToast(msg, 'error');
      }
      const err = new Error(msg);
      err.code = (json && json.code) || 0;
      throw err;
    }
    if (!json || json.code !== 0) {
      const err = new Error(msg);
      err.code = json ? json.code : 0;
      if (!opts.silent) showToast(msg, 'error');
      throw err;
    }
    return json.data;
  }

  async function download(url, filename) {
    const headers = {};
    const t = token();
    if (t) headers['Authorization'] = 'Bearer ' + t;
    const resp = await fetch(url, { headers: headers });
    if (!resp.ok) {
      let msg = '下载失败(' + resp.status + ')';
      try {
        const j = await resp.json();
        if (j && j.message) msg = j.message;
      } catch (e) { }
      showToast(msg, 'error');
      return;
    }
    const blob = await resp.blob();
    const a = document.createElement('a');
    const objUrl = URL.createObjectURL(blob);
    a.href = objUrl;
    a.download = filename || 'download';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(objUrl), 1000);
  }

  /* ========== 列表行缓存 ==========
     不少页面曾用 AdminUI.get(url, {page:1, page_size:100}) 拿回一百条再 filter 找 id 来回填编辑表单。
     记录一旦超过 100 条，目标行压根不在结果里，「编辑」点了毫无反应且没有任何提示。
     这里统一解决：所有列表请求返回时按 url 缓存行，findRow 优先从已渲染过的数据里取；
     只有确实没见过时才退化成一次小分页查询（保持旧的 100 条兜底能力）。*/
  const _rowCache = {};
  const _ROW_CACHE_MAX = 1000;

  function _cacheRows(url, list) {
    if (!Array.isArray(list) || !list.length) return;
    let m = _rowCache[url];
    if (!m) { m = _rowCache[url] = new Map(); }
    list.forEach(function (r) {
      if (r && r.id !== undefined && r.id !== null) m.set(Number(r.id), r);
    });
    if (m.size > _ROW_CACHE_MAX) {
      // 只保留最近写入的一批，避免长时间操作后缓存无界增长
      const keep = Array.from(m.entries()).slice(-_ROW_CACHE_MAX);
      m.clear();
      keep.forEach(function (e) { m.set(e[0], e[1]); });
    }
  }

  function getApi(url, params, opts) {
    return request('GET', url + qs(params), undefined, opts).then(function (data) {
      if (data && Array.isArray(data.list)) _cacheRows(url, data.list);
      return data;
    });
  }

  async function findRowApi(url, id) {
    const hit = _rowCache[url] && _rowCache[url].get(Number(id));
    if (hit) return hit;
    const data = await getApi(url, { page: 1, page_size: 100 });
    return ((data && data.list) || []).filter(function (x) { return Number(x.id) === Number(id); })[0];
  }

  function postApi(url, body, opts) { return request('POST', url, body, opts); }
  function putApi(url, body, opts) { return request('PUT', url, body, opts); }
  function delApi(url, params, opts) { return request('DELETE', url + qs(params), undefined, opts); }

  function flattenTree(nodes, depth) {
    depth = depth || 0;
    const out = [];
    (nodes || []).forEach(n => {
      out.push(Object.assign({ depth: depth }, n));
      if (n.children && n.children.length) {
        out.push.apply(out, flattenTree(n.children, depth + 1));
      }
    });
    return out;
  }

  function debounce(fn, wait) {
    let t;
    return function () {
      const ctx = this, args = arguments;
      clearTimeout(t);
      t = setTimeout(function () { fn.apply(ctx, args); }, wait);
    };
  }

  /* ========== 侧边栏菜单数据 ========== */
  const menuData = [
    {
      group: '主导航',
      items: [
        { icon: '📊', text: '仪表盘', href: 'dashboard.html', key: 'dashboard' }
      ]
    },
    {
      group: '商品管理',
      items: [
        {
          icon: '📦', text: '商品管理', key: 'goods',
          children: [
            { text: '商品列表', href: 'pages/goods/goods-list.html', key: 'goods-list' },
            { text: '商品分类', href: 'pages/goods/goods-category.html', key: 'goods-category' },
            { text: '品牌管理', href: 'pages/goods/goods-brand.html', key: 'goods-brand' },
            { text: '规格属性', href: 'pages/goods/goods-spec-attr.html', key: 'goods-spec-attr' },
            { text: '评论管理', href: 'pages/goods/goods-comment.html', key: 'goods-comment' }
          ]
        }
      ]
    },
    {
      group: '订单管理',
      items: [
        {
          icon: '📋', text: '订单管理', key: 'order',
          children: [
            { text: '订单列表', href: 'pages/order/order-list.html', key: 'order-list' },
            { text: '售后管理', href: 'pages/order/after-sale.html', key: 'after-sale' },
            { text: '物流公司', href: 'pages/order/logistics.html', key: 'logistics' }
          ]
        }
      ]
    },
    {
      group: '用户管理',
      items: [
        {
          icon: '👥', text: '用户管理', key: 'member',
          children: [
            { text: '会员列表', href: 'pages/member/member-list.html', key: 'member-list' },
            { text: '会员等级', href: 'pages/member/member-level.html', key: 'member-level' },
            { text: '积分管理', href: 'pages/member/points.html', key: 'points' }
          ]
        }
      ]
    },
    {
      group: '营销中心',
      items: [
        {
          icon: '🎯', text: '营销管理', key: 'marketing',
          children: [
            { text: '优惠券', href: 'pages/marketing/coupon.html', key: 'coupon' },
            { text: '秒杀活动', href: 'pages/marketing/seckill.html', key: 'seckill' },
            { text: '满减满折', href: 'pages/marketing/full-discount.html', key: 'full-discount' },
            { text: '拼团活动', href: 'pages/marketing/group-buy.html', key: 'group-buy' },
            { text: '分销管理', href: 'pages/marketing/distributor.html', key: 'distributor' }
          ]
        }
      ]
    },
    {
      group: '内容管理',
      items: [
        {
          icon: '📝', text: '内容管理', key: 'content',
          children: [
            { text: '文章管理', href: 'pages/content/article.html', key: 'article' },
            { text: '广告管理', href: 'pages/content/ad.html', key: 'ad' },
            { text: '公告通知', href: 'pages/content/notice.html', key: 'notice' }
          ]
        }
      ]
    },
    {
      group: '系统',
      items: [
        { icon: '⚙️', text: '系统设置', href: 'pages/settings/settings.html', key: 'settings' },
        {
          icon: '🔐', text: '权限管理', key: 'permission',
          children: [
            { text: '管理员', href: 'pages/permission/admin.html', key: 'admin' },
            { text: '角色管理', href: 'pages/permission/role.html', key: 'role' },
            { text: '权限资源', href: 'pages/permission/resource.html', key: 'resource' },
            { text: '部门管理', href: 'pages/permission/dept.html', key: 'dept' },
            { text: '登录日志', href: 'pages/permission/login-log.html', key: 'login-log' }
          ]
        },
        { icon: '📜', text: '操作日志', href: 'pages/logs/operation-log.html', key: 'logs' }
      ]
    }
  ];

  const MENU_PERM = {
    dashboard: 'dashboard:',
    goods: 'goods:', 'goods-list': 'goods:', 'goods-category': 'goods:', 'goods-brand': 'goods:', 'goods-spec-attr': 'goods:', 'goods-comment': 'goods:',
    order: 'order:', 'order-list': 'order:', 'after-sale': 'order:', logistics: 'order:',
    member: 'member:', 'member-list': 'member:', 'member-level': 'member:', points: 'member:',
    marketing: 'marketing:', coupon: 'marketing:', seckill: 'marketing:', 'full-discount': 'marketing:', 'group-buy': 'marketing:', distributor: 'marketing:',
    content: 'content:', article: 'content:', ad: 'content:', notice: 'content:',
    settings: 'settings:',
    permission: 'permission:', admin: 'permission:', role: 'permission:', resource: 'permission:', dept: 'permission:', 'login-log': 'permission:',
    logs: 'logs:'
  };

  function menuVisible(item) {
    const pre = MENU_PERM[item.key];
    if (!pre) {
      // 未配置权限前缀的菜单一律隐藏：宁可不显示，也不能让它绕过权限对所有管理员可见。
      // 新增菜单时请在 MENU_PERM 补一行（与后端 seed/base.py 的 PERM_TREE 保持同码）。
      console.warn('[menu] 菜单缺少权限前缀配置，已隐藏：' + item.key);
      return false;
    }
    const perms = permissions();
    if (!perms) return false;
    return perms.some(c => c.indexOf(pre) === 0);
  }

  function filterMenuItems(items) {
    const out = [];
    items.forEach(item => {
      if (item.children) {
        const kids = filterMenuItems(item.children);
        if (kids.length) out.push(Object.assign({}, item, { children: kids }));
      } else if (menuVisible(item)) {
        out.push(item);
      }
    });
    return out;
  }

  /* 菜单项排序：带子的项放前面，同类型内保持原顺序 */
  function sortMenuItems(items) {
    const withChildren = items.filter(item => item.children && item.children.length);
    const withoutChildren = items.filter(item => !item.children || !item.children.length);
    return withChildren.concat(withoutChildren);
  }

  /* ========== 侧边栏状态记忆（跨页面保持展开组与滚动位置） ========== */
  const SIDEBAR_STATE_KEY = 'mall_admin_sidebar_state';
  function readSidebarState() {
    try { return JSON.parse(sessionStorage.getItem(SIDEBAR_STATE_KEY)) || {}; }
    catch (e) { return {}; }
  }
  function writeSidebarState(patch) {
    const s = readSidebarState();
    for (const k in patch) s[k] = patch[k];
    try { sessionStorage.setItem(SIDEBAR_STATE_KEY, JSON.stringify(s)); } catch (e) { }
  }

  /* ========== 折叠态悬浮子菜单 ========== */
  const COLLAPSE_KEY = 'mall_admin_sidebar_collapsed';
  let collapsedPop = null;
  let popTimer = null;

  function hideCollapsedPop(immediate) {
    if (popTimer) { clearTimeout(popTimer); popTimer = null; }
    if (!collapsedPop) return;
    if (immediate) { collapsedPop.classList.remove('show'); return; }
    popTimer = setTimeout(function () { if (collapsedPop) collapsedPop.classList.remove('show'); }, 200);
  }

  function showCollapsedPop(trigger) {
    if (!document.body.classList.contains('sidebar-collapsed')) return;
    if (popTimer) { clearTimeout(popTimer); popTimer = null; }
    const key = trigger.getAttribute('data-toggle');
    const submenu = document.getElementById('submenu-' + key);
    if (!submenu || !submenu.querySelector('a.menu-item')) { hideCollapsedPop(true); return; }
    if (!collapsedPop) {
      collapsedPop = document.createElement('div');
      collapsedPop.className = 'collapsed-pop';
      document.body.appendChild(collapsedPop);
      collapsedPop.addEventListener('mouseenter', function () {
        if (popTimer) { clearTimeout(popTimer); popTimer = null; }
      });
      collapsedPop.addEventListener('mouseleave', function () {
        hideCollapsedPop();
      });
    }
    const titleEl = trigger.querySelector('.menu-text');
    const popTitle = titleEl ? escHtml(titleEl.textContent).trim() : '';
    const titleBlock = popTitle ? '<div class="collapsed-pop-title">' + popTitle + '</div>' : '';
    collapsedPop.innerHTML = titleBlock + submenu.innerHTML;
    const r = trigger.getBoundingClientRect();
    const w = collapsedPop.offsetWidth;
    const h = collapsedPop.offsetHeight;
    let top = r.top;
    if (top + h > window.innerHeight - 12) top = Math.max(12, window.innerHeight - h - 12);
    let left = r.right + 6;
    if (left + w > window.innerWidth - 12) left = r.left - w - 6;
    collapsedPop.style.top = top + 'px';
    collapsedPop.style.left = left + 'px';
    collapsedPop.classList.add('show');
  }

  /* ========== 渲染侧边栏 ========== */
  function renderSidebar(activeKey) {
    const sidebar = document.getElementById('sidebar');
    if (!sidebar) return;
    if (document.body && document.body.getAttribute('data-spa-nav') === '1') return;

    const prefix = menuRoot();
    const filtered = menuData
      .map(group => Object.assign({}, group, { items: sortMenuItems(filterMenuItems(group.items)) }))
      .filter(g => g.items.length);
    const saved = readSidebarState();
    const savedExpanded = (saved.expanded && saved.expanded.length) ? saved.expanded : [];

    let html = `
      <div class="sidebar-logo">
        <div class="logo-icon"><img src="${prefix}images/logo.png" alt="随心商城"></div>
        <span class="logo-text">随心商城管理后台</span>
      </div>
      <div class="sidebar-menu">
    `;

    filtered.forEach(group => {
      if (!group.items.length) return;
      html += `<div class="menu-group">`;
      html += `<div class="menu-group-title">${group.group}</div>`;

      group.items.forEach(item => {
        if (item.children) {
          const isActiveGroup = item.children.some(c => c.key === activeKey);
          const shouldOpen = isActiveGroup || savedExpanded.indexOf(item.key) !== -1;
          html += `
            <div class="menu-item ${shouldOpen ? 'expanded' : ''}" data-toggle="${item.key}" title="${item.text}">
              <span class="menu-icon">${item.icon}</span>
              <span class="menu-text">${item.text}</span>
              <span class="menu-arrow">▶</span>
            </div>
            <div class="submenu ${shouldOpen ? 'open' : ''}" id="submenu-${item.key}">
          `;
          item.children.forEach(child => {
            html += `
              <a href="${prefix}${child.href}" class="menu-item ${child.key === activeKey ? 'active' : ''}" title="${child.text}">
                <span class="menu-text">${child.text}</span>
              </a>
            `;
          });
          html += `</div>`;
        } else {
          html += `
            <a href="${prefix}${item.href}" class="menu-item ${item.key === activeKey ? 'active' : ''}" title="${item.text}">
              <span class="menu-icon">${item.icon}</span>
              <span class="menu-text">${item.text}</span>
            </a>
          `;
        }
      });

      html += `</div>`;
    });

    if (!filtered.length) {
      html += '<div class="menu-empty"><div class="menu-empty-icon">🔒</div>暂无菜单权限<br><span>请联系管理员分配角色权限</span></div>';
    }
    html += `</div>`;
    sidebar.innerHTML = html;

    const menuEl = sidebar.querySelector('.sidebar-menu');
    if (menuEl) {
      menuEl.addEventListener('scroll', function () {
        writeSidebarState({ scrollTop: menuEl.scrollTop });
      });

      const persist = function () {
        const keys = [];
        sidebar.querySelectorAll('.menu-item.expanded[data-toggle]').forEach(function (el) {
          keys.push(el.getAttribute('data-toggle'));
        });
        writeSidebarState({ expanded: keys, scrollTop: menuEl.scrollTop });
      };

      sidebar.querySelectorAll('[data-toggle]').forEach(el => {
        el.addEventListener('click', function () {
          const key = this.getAttribute('data-toggle');
          const submenu = document.getElementById('submenu-' + key);
          if (document.body.classList.contains('sidebar-collapsed')) {
            if (collapsedPop && collapsedPop.classList.contains('show') && collapsedPop.getAttribute('data-key') === key) {
              hideCollapsedPop(true);
            } else {
              showCollapsedPop(this);
              if (collapsedPop) collapsedPop.setAttribute('data-key', key);
            }
            return;
          }
          const beforeScroll = menuEl.scrollTop;
          this.classList.toggle('expanded');
          submenu.classList.toggle('open');
          menuEl.scrollTop = beforeScroll;
          requestAnimationFrame(function () { menuEl.scrollTop = beforeScroll; });
          setTimeout(function () { menuEl.scrollTop = beforeScroll; }, 280);
          persist();
        });
        el.addEventListener('mouseenter', function () {
          if (document.body.classList.contains('sidebar-collapsed')) showCollapsedPop(this);
        });
        el.addEventListener('mouseleave', function () {
          if (document.body.classList.contains('sidebar-collapsed')) hideCollapsedPop();
        });
      });

      // 点击菜单跳页前记录滚动位置
      sidebar.querySelectorAll('a.menu-item').forEach(function (a) {
        a.addEventListener('click', function () {
          writeSidebarState({ scrollTop: menuEl.scrollTop });
        });
      });

      // 页面刷新/跳转后恢复滚动位置（同步恢复避免闪烁回顶）
      if (typeof saved.scrollTop === 'number') {
        menuEl.scrollTop = saved.scrollTop;
        requestAnimationFrame(function () { menuEl.scrollTop = saved.scrollTop; });
      }
    }
  }

  /* ========== 渲染顶部栏 ========== */
  function renderHeader(breadcrumb) {
    const header = document.getElementById('header');
    if (!header) return;
    if (document.body && document.body.getAttribute('data-spa-nav') === '1') return;

    const prefix = menuPrefix();
    const session = getSession();
    if (!session || !session.token) {
      window.location.replace(menuRoot() + 'login.html');
      return;
    }

    const realName = session.realName || session.username || '管理员';
    const roles = (session.roles && session.roles.length) ? session.roles : [];
    const roleText = roles.map(r => r.roleName || r.role_name || '').filter(Boolean).join(' / ');
    const accountText = roleText || session.roleLabel || (session.username || '');

    const bcHtml = breadcrumb.map((item, i) => {
      if (i === breadcrumb.length - 1) {
        return `<span class="breadcrumb-current">${escHtml(item)}</span>`;
      }
      return `<span>${escHtml(item)}</span><span class="breadcrumb-sep">/</span>`;
    }).join('');

    header.innerHTML = `
      <div class="header-left">
        <button class="header-toggle" id="sidebarToggle" title="折叠菜单">☰</button>
        <div class="breadcrumb">${bcHtml}</div>
      </div>
      <div class="header-right">
        <div class="header-user" id="headerUser">
          <div class="user-avatar">${escHtml(realName.charAt(0))}</div>
          <div class="user-info">
            <span class="user-name">${escHtml(realName)}</span>
            <span class="user-role">${escHtml(accountText)}</span>
          </div>
          <span class="user-caret">▾</span>
          <div class="user-dropdown">
            <div class="user-dropdown-info">
              <span class="user-dropdown-name">${escHtml(realName)}</span>
              <span class="user-dropdown-account">账号：${escHtml(session.username || '')}</span>
            </div>
            <div class="user-dropdown-menu">
              <a class="user-dropdown-item danger" href="javascript:void(0)" id="logoutBtn">退出登录</a>
            </div>
          </div>
        </div>
      </div>
    `;

    document.getElementById('sidebarToggle').addEventListener('click', function () {
      const collapsed = document.body.classList.toggle('sidebar-collapsed');
      hideCollapsedPop(true);
      try { localStorage.setItem(COLLAPSE_KEY, collapsed ? '1' : ''); } catch (e) { }
    });

    const userBox = header.querySelector('.header-user');
    userBox.addEventListener('click', function (e) {
      e.stopPropagation();
      this.classList.toggle('open');
    });

    header.querySelector('#logoutBtn').addEventListener('click', async function (e) {
      e.preventDefault();
      e.stopPropagation();
      if (!window.confirm('确定要退出当前账号吗？')) return;
      const s = getSession();
      try {
        if (s && s.token) request('POST', API_BASE + '/auth/logout', undefined, { silent: true, redirect401: false });
      } catch (err) { }
      clearSession();
      showToast('已退出登录', 'success');
      window.location.replace(menuRoot() + 'login.html');
    });
  }

  /* ========== 页面初始化与路由守卫 ========== */
  function showNoPerm() {
    const main = document.querySelector('main.content');
    if (!main) return;
    main.innerHTML = `
      <div style="padding:120px 20px;text-align:center;">
        <div style="font-size:48px;margin-bottom:16px;">🔒</div>
        <div style="font-size:18px;font-weight:600;color:#1e293b;">无访问权限</div>
        <div style="margin-top:8px;color:#64748b;font-size:14px;">当前账号没有访问该页面的权限，请联系管理员分配权限</div>
      </div>
    `;
  }

  async function initPage(opts) {
    opts = opts || {};
    const prefix = menuPrefix();
    const session = getSession();
    if (!session || !session.token) {
      window.location.replace(menuRoot() + 'login.html');
      return false;
    }
    try {
      const me = await request('GET', API_BASE + '/auth/me');
      const updated = Object.assign({}, session, {
        username: me.username || session.username,
        realName: me.realName || me.username || session.realName || '',
        roles: me.roles || [],
        permissions: me.permissions || [],
        dataScope: me.dataScope,
        deptId: me.deptId
      });
      setSession(updated);
    } catch (e) {
      return false;
    }
    renderSidebar(opts.key);
    renderHeader(opts.breadcrumb || []);
    const need = opts.need || [];
    if (need.length && !need.some(code => can(code))) {
      showNoPerm();
      return false;
    }
    return true;
  }

  /* ========== 模态框 ========== */
  let modalOpenCount = 0;

  function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) return;
    modal.classList.add('show');
    modalOpenCount++;
    if (modalOpenCount === 1) document.body.classList.add('modal-open');
  }

  function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) return;
    modal.classList.remove('show');
    modalOpenCount = Math.max(0, modalOpenCount - 1);
    if (modalOpenCount === 0) document.body.classList.remove('modal-open');
  }

  document.addEventListener('click', function (e) {
    const closeBtn = e.target.closest('[data-close-modal], .modal-close');
    if (closeBtn) {
      const dataId = closeBtn.getAttribute('data-close-modal');
      if (dataId) { closeModal(dataId); return; }
      const overlay = closeBtn.closest('.modal-overlay');
      if (overlay && overlay.id) { closeModal(overlay.id); return; }
    }
    const drawerClose = e.target.closest('[data-close-drawer]');
    if (drawerClose) {
      const drawerId = drawerClose.getAttribute('data-close-drawer');
      if (drawerId) closeDrawer(drawerId);
      return;
    }
    if (e.target.classList.contains('modal-overlay')) {
      closeModal(e.target.id);
      return;
    }
    if (e.target.classList.contains('drawer-overlay')) {
      const id = e.target.id;
      if (id && id.indexOf('-overlay') !== -1) closeDrawer(id.slice(0, -'-overlay'.length));
    }
  });

  document.addEventListener('mousedown', function (e) {
    if (document.body.classList.contains('sidebar-collapsed')) {
      const inside = (collapsedPop && collapsedPop.contains(e.target)) ||
        (e.target.closest && e.target.closest('.sidebar'));
      if (!inside) hideCollapsedPop(true);
    }
  });

  /* ========== 抽屉 ========== */
  function openDrawer(drawerId) {
    const overlay = document.getElementById(drawerId + '-overlay');
    const drawer = document.getElementById(drawerId);
    if (overlay) overlay.classList.add('show');
    if (drawer) {
      drawer.classList.add('show');
      document.body.classList.add('drawer-open');
    }
  }

  function closeDrawer(drawerId) {
    const overlay = document.getElementById(drawerId + '-overlay');
    const drawer = document.getElementById(drawerId);
    if (overlay) overlay.classList.remove('show');
    if (drawer) drawer.classList.remove('show');
    if (!document.querySelector('.drawer.show')) {
      document.body.classList.remove('drawer-open');
    }
  }

  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    const drawer = document.querySelector('.drawer.show');
    if (drawer && drawer.id) { closeDrawer(drawer.id); return; }
    const modal = document.querySelector('.modal-overlay.show');
    if (modal && modal.id) closeModal(modal.id);
  });

  /* ========== 标签页切换 ========== */
  function initTabs(container) {
    const root = container || document;
    root.querySelectorAll('.tabs').forEach(tabs => {
      tabs.querySelectorAll('.tab-item').forEach(tab => {
        tab.addEventListener('click', function () {
          const target = this.getAttribute('data-tab');
          const parent = this.closest('.tabs-container') || this.parentElement.parentElement;
          tabs.querySelectorAll('.tab-item').forEach(t => t.classList.remove('active'));
          this.classList.add('active');
          if (parent) {
            parent.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            const targetContent = parent.querySelector('#' + target);
            if (targetContent) targetContent.classList.add('active');
          }
        });
      });
    });
  }

  /* ========== 全选复选框 ========== */
  function initCheckAll(table) {
    const root = table || document;
    root.querySelectorAll('.check-all').forEach(checkbox => {
      checkbox.addEventListener('change', function () {
        const tbody = this.closest('table').querySelector('tbody');
        if (tbody) {
          tbody.querySelectorAll('.row-check').forEach(cb => {
            cb.checked = this.checked;
          });
        }
        updateBatchBar(this.closest('.card') || document);
      });
    });
  }

  /* ========== 更新批量操作栏计数 ========== */
  function updateBatchBar(container) {
    const bar = container.querySelector('.batch-bar');
    if (!bar) return;
    const checked = container.querySelectorAll('.row-check:checked').length;
    const countEl = bar.querySelector('.batch-count');
    if (countEl) countEl.textContent = checked;
    bar.style.display = checked > 0 ? 'flex' : 'none';
  }

  /* ========== 树形结构展开/收起 ========== */
  function initTree(container) {
    const root = container || document;
    root.querySelectorAll('.tree-toggle').forEach(toggle => {
      toggle.addEventListener('click', function (e) {
        e.stopPropagation();
        const node = this.closest('.tree-node');
        const children = node.querySelector('.tree-children');
        if (children) {
          this.classList.toggle('expanded');
          children.classList.toggle('open');
        }
      });
    });
  }

  /* ========== 折叠树下拉选择器（通用组件） ==========
     root：容器元素（替代原生 select）
     opts：{
       data: 分类树顶层数组 [{id,name,children:[]}],
       value: 当前选中 id（空串=未选/全部）,
       showAll: true 时面板顶部显示「全部分类」行（默认 true）,
       allLabel: '全部分类',
       placeholder: showAll=false 时的占位提示,
       size: 'sm' 用于筛选栏小尺寸（高34）,
       onChange(value): 选中回调
     }
     返回实例：{ getValue, setValue, setData, open, close } */
  const catSelects = [];
  let catHandlersReady = false;
  function ensureCatHandlers() {
    if (catHandlersReady) return;
    catHandlersReady = true;
    document.addEventListener('mousedown', function (e) {
      const inside = catSelects.some(function (c) { return c.root.contains(e.target); });
      if (!inside) catSelects.forEach(function (c) { c.close(); });
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') catSelects.forEach(function (c) { c.close(); });
    });
    window.addEventListener('resize', function () { catSelects.forEach(function (c) { c.close(); }); });
    document.addEventListener('scroll', function () { catSelects.forEach(function (c) { c.close(); }); }, true);
  }

  function createCatTreeSelect(root, opts) {
    opts = opts || {};
    const showAll = opts.showAll !== false;
    const allLabel = opts.allLabel || '全部分类';
    const placeholder = opts.placeholder || '请选择分类';
    let data = opts.data || [];
    let value = (opts.value !== undefined && opts.value !== null) ? String(opts.value) : '';
    const onChange = typeof opts.onChange === 'function' ? opts.onChange : null;
    const instance = {};
    let indexMap = {};

    root.classList.add('cat-select');
    if (opts.size === 'sm') root.classList.add('cat-select-sm');
    root.innerHTML = '<button type="button" class="cat-trigger" title="选择分类"><span class="cat-value"></span><span class="cat-caret">▾</span></button>';
    const trigger = root.querySelector('.cat-trigger');
    const valueEl = root.querySelector('.cat-value');
    const panel = document.createElement('div');
    panel.className = 'cat-panel';
    root.appendChild(panel);

    function buildIndex() {
      indexMap = {};
      (function walk(nodes, path, ids) {
        (nodes || []).forEach(function (n) {
          const p = path.concat([n]);
          const i = ids.concat([String(n.id)]);
          if (!(String(n.id) in indexMap)) indexMap[String(n.id)] = { node: n, path: p, ids: i };
          walk(n.children || [], p, i);
        });
      })(data, [], []);
    }
    buildIndex();

    function renderBranch(n) {
      const kids = n.children && n.children.length;
      return '<div class="cat-branch">' +
        '<div class="cat-row' + (kids ? '' : ' leaf') + '" data-id="' + escHtml(String(n.id)) + '" data-leaf="' + (kids ? '0' : '1') + '" title="' + escHtml(n.name) + '">' +
        '<span class="cat-arrow">' + (kids ? '▶' : '') + '</span>' +
        '<span class="cat-text">' + escHtml(n.name) + '</span>' +
        '<span class="cat-check">✓</span></div>' +
        (kids ? '<div class="cat-children">' + (n.children || []).map(renderBranch).join('') + '</div>' : '') +
        '</div>';
    }

    function renderAll() {
      let html = '';
      if (showAll) {
        html += '<div class="cat-row all' + (value === '' ? ' selected' : '') + '" data-id="" data-leaf="1" title="' + escHtml(allLabel) + '">' +
          '<span class="cat-arrow"></span><span class="cat-text">' + escHtml(allLabel) + '</span><span class="cat-check">✓</span></div>' +
          '<div class="cat-divider"></div>';
      }
      if (!data.length) {
        html += '<div class="cat-empty">暂无分类数据</div>';
      } else {
        html += data.map(renderBranch).join('');
      }
      panel.innerHTML = html;
    }

    function syncText() {
      if (value === '') {
        valueEl.textContent = showAll ? allLabel : placeholder;
        valueEl.className = 'cat-value' + (showAll ? '' : ' placeholder');
      } else {
        const hit = indexMap[value];
        valueEl.textContent = hit ? hit.path.map(function (x) { return x.name; }).join(' / ') : ('分类#' + value);
        valueEl.className = 'cat-value';
      }
      valueEl.title = valueEl.textContent;
    }

    function markSelected() {
      Array.prototype.forEach.call(panel.querySelectorAll('.cat-row'), function (row) {
        row.classList.toggle('selected', row.getAttribute('data-id') === value);
      });
    }

    function positionPanel() {
      const r = trigger.getBoundingClientRect();
      const w = Math.min(Math.max(r.width, 220), window.innerWidth - 24);
      let left = r.left;
      if (left + w > window.innerWidth - 12) left = Math.max(12, window.innerWidth - 12 - w);
      panel.style.top = (r.bottom + 6) + 'px';
      panel.style.left = left + 'px';
      panel.style.width = w + 'px';
    }

    function openPath() {
      if (!value || !indexMap[value]) return;
      const ids = indexMap[value].ids;
      for (let i = 0; i < ids.length - 1; i++) {
        const row = panel.querySelector('.cat-row[data-id="' + ids[i] + '"]');
        if (row && row.getAttribute('data-leaf') === '0') {
          row.classList.add('open');
          const ch = row.parentNode ? row.parentNode.querySelector(':scope > .cat-children') : null;
          if (ch) ch.classList.add('open');
        }
      }
    }

    function open() {
      positionPanel();
      renderAll();
      markSelected();
      openPath();
      panel.classList.add('open');
      root.classList.add('open');
    }

    function close() {
      root.classList.remove('open');
      panel.classList.remove('open');
    }

    function selectValue(v) {
      value = (v === null || v === undefined) ? '' : String(v);
      syncText();
      markSelected();
      close();
      if (onChange) onChange(value);
    }

    trigger.addEventListener('click', function (e) {
      e.stopPropagation();
      if (root.classList.contains('open')) close();
      else {
        catSelects.forEach(function (c) { if (c !== instance) c.close(); });
        open();
      }
    });

    panel.addEventListener('click', function (e) {
      const row = e.target.closest ? e.target.closest('.cat-row') : null;
      if (!row) return;
      if (row.getAttribute('data-leaf') === '1') {
        selectValue(row.getAttribute('data-id') || '');
        return;
      }
      // 父分类：仅展开/收起其子节点
      const ch = row.parentNode ? row.parentNode.querySelector(':scope > .cat-children') : null;
      if (ch) {
        row.classList.toggle('open');
        ch.classList.toggle('open');
      }
    });

    instance.root = root;
    instance.getValue = function () { return value; };
    instance.setValue = function (v) {
      value = (v === null || v === undefined) ? '' : String(v);
      syncText();
      markSelected();
    };
    instance.setData = function (d) {
      data = d || [];
      buildIndex();
      renderAll();
      syncText();
      markSelected();
    };
    instance.open = open;
    instance.close = close;

    syncText();
    renderAll();
    catSelects.push(instance);
    ensureCatHandlers();
    return instance;
  }

  /* ========== 通用确认对话框 ========== */
  function confirmAction(message, callback) {
    if (window.confirm(message)) {
      if (callback) callback();
    }
  }

  /* ========== 实时筛选：筛选栏控件变化即自动触发搜索，无需再点搜索按钮 ========== */
  const liveTimers = {};
  const resetBtnRe = /^(重置|清空|还原|全部)$/;
  function triggerLiveSearch(bar) {
    if (!bar) return;
    const actions = bar.querySelector('.filter-actions');
    if (!actions) return;
    let hit = null;
    Array.prototype.forEach.call(actions.querySelectorAll('button'), function (b) {
      if (hit) return;
      const label = String(b.textContent || '').trim();
      if (resetBtnRe.test(label)) return;
      if (b.classList.contains('btn-primary') || /搜索|查询|🔍/.test(label)) hit = b;
    });
    if (hit) hit.click();
  }
  document.addEventListener('input', function (e) {
    const t = e.target;
    const bar = t && t.closest ? t.closest('.filter-bar') : null;
    if (!bar || !t.classList) return;
    if (t.tagName !== 'INPUT' && t.tagName !== 'TEXTAREA') return;
    const ty = (t.type || '').toLowerCase();
    if (ty === 'checkbox' || ty === 'radio' || ty === 'button' || ty === 'submit' || ty === 'reset') return;
    if (ty === 'text' || ty === 'search' || ty === 'number') {
      clearTimeout(liveTimers[t]);
      liveTimers[t] = setTimeout(function () { triggerLiveSearch(bar); }, 350);
    } else {
      triggerLiveSearch(bar);
    }
  }, true);
  document.addEventListener('change', function (e) {
    const t = e.target;
    const bar = t && t.closest ? t.closest('.filter-bar') : null;
    if (!bar || !t.classList) return;
    if (t.tagName === 'INPUT' && (t.type === 'text' || t.type === 'search' || t.type === 'number')) return;
    triggerLiveSearch(bar);
  }, true);

  const style = document.createElement('style');
  style.textContent = `
    /* ---------- Toast（右上角、顶栏下方、暖色系卡片） ---------- */
    @keyframes toastInRight {
      from { opacity: 0; transform: translateX(40px); }
      to { opacity: 1; transform: translateX(0); }
    }
    .admin-toast {
      position: fixed; right: 24px; z-index: 9999;
      display: flex; align-items: center; gap: 12px;
      min-width: 260px; max-width: 380px;
      padding: 14px 18px 14px 16px;
      background: #fff; border-radius: 14px;
      border: 1px solid #F3E7DC;
      box-shadow: 0 10px 32px rgba(120, 60, 0, 0.14);
      font-size: 14px; color: #333; font-weight: 500;
      animation: toastInRight 0.32s cubic-bezier(0.2, 0.9, 0.3, 1.15);
    }
    .admin-toast.hide { opacity: 0; transform: translateX(24px); transition: all 0.3s ease; }
    .admin-toast .toast-icon {
      width: 28px; height: 28px; border-radius: 50%;
      display: flex; align-items: center; justify-content: center;
      color: #fff; font-size: 14px; font-weight: 700; flex-shrink: 0;
      box-shadow: 0 3px 10px rgba(0, 0, 0, 0.15);
    }
    .admin-toast .toast-msg { flex: 1; line-height: 1.5; word-break: break-word; }

    /* ---------- 折叠树下拉选择器（通用） ---------- */
    .cat-select { position: relative; display: inline-block; vertical-align: top; text-align: left; }
    .cat-trigger {
      display: flex; align-items: center; justify-content: space-between; gap: 8px;
      width: 100%; height: 38px; padding: 0 12px;
      border: 1px solid var(--border-color); border-radius: var(--radius);
      background: #fff; font-size: 13px; color: var(--text-primary);
      cursor: pointer; transition: var(--transition); user-select: none;
    }
    .cat-trigger:hover { border-color: var(--primary); }
    .cat-select.open .cat-trigger { border-color: var(--primary); box-shadow: 0 0 0 3px rgba(255, 103, 0, 0.12); }
    .cat-select-sm .cat-trigger { height: 34px; font-size: 12px; }
    .cat-trigger .cat-value { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .cat-value.placeholder { color: var(--text-muted); }
    .cat-trigger .cat-caret { font-size: 10px; color: var(--text-muted); transition: transform 0.2s; flex-shrink: 0; }
    .cat-select.open .cat-caret { transform: rotate(180deg); }
    .cat-panel {
      position: fixed; z-index: 1200;
      background: #fff; border: 1px solid var(--border-color); border-radius: var(--radius-lg);
      box-shadow: 0 12px 40px rgba(0, 0, 0, 0.14);
      padding: 6px; max-height: 280px; overflow-y: auto; display: none;
    }
    .cat-panel.open { display: block; animation: catPanelIn 0.18s ease; }
    .cat-row {
      display: flex; align-items: center; gap: 6px; padding: 7px 10px;
      border-radius: var(--radius); cursor: pointer; transition: background 0.15s;
      font-size: 13px; color: var(--text-primary); white-space: nowrap;
    }
    .cat-row:hover { background: var(--primary-bg); }
    .cat-row.selected { background: var(--primary-bg); color: var(--primary); font-weight: 600; }
    .cat-arrow { width: 18px; height: 18px; flex-shrink: 0; display: inline-flex; align-items: center; justify-content: center; color: var(--text-muted); font-size: 9px; transition: transform 0.2s ease; border-radius: var(--radius); }
    .cat-row:hover > .cat-arrow { color: var(--primary); background: rgba(255,103,0,0.08); }
    .cat-row.open > .cat-arrow { transform: rotate(90deg); color: var(--primary); background: rgba(255,103,0,0.10); }
    .cat-row .cat-text { flex: 1; overflow: hidden; text-overflow: ellipsis; }
    .cat-row .cat-check { width: 16px; flex-shrink: 0; color: var(--primary); font-weight: 700; visibility: hidden; }
    .cat-row.selected .cat-check { visibility: visible; }
    .cat-children { display: none; padding-left: 20px; }
    .cat-children.open { display: block; }
    .cat-divider { height: 1px; background: var(--border-light); margin: 4px 0 6px; }
    .cat-empty { padding: 20px 10px; text-align: center; color: var(--text-muted); font-size: 13px; }
    @keyframes catPanelIn { from { opacity: 0; transform: translateY(-6px); } to { opacity: 1; transform: translateY(0); } }
  `;
  document.head.appendChild(style);

  /* ========== 分页初始化 ========== */
  function renderPagination(containerId, currentPage, totalPages, totalItems, pageSize) {
    const container = document.getElementById(containerId);
    if (!container) return;

    let pageBtns = '';
    const maxVisible = 5;
    let start = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    let end = Math.min(totalPages, start + maxVisible - 1);
    if (end - start + 1 < maxVisible) {
      start = Math.max(1, end - maxVisible + 1);
    }

    pageBtns += `<button class="page-btn" ${currentPage === 1 ? 'disabled' : ''} data-page="${currentPage - 1}">‹</button>`;

    if (start > 1) {
      pageBtns += `<button class="page-btn" data-page="1">1</button>`;
      if (start > 2) pageBtns += `<span style="padding:0 4px;color:#999999">...</span>`;
    }

    for (let i = start; i <= end; i++) {
      pageBtns += `<button class="page-btn ${i === currentPage ? 'active' : ''}" data-page="${i}">${i}</button>`;
    }

    if (end < totalPages) {
      if (end < totalPages - 1) pageBtns += `<span style="padding:0 4px;color:#999999">...</span>`;
      pageBtns += `<button class="page-btn" data-page="${totalPages}">${totalPages}</button>`;
    }

    pageBtns += `<button class="page-btn" ${currentPage === totalPages ? 'disabled' : ''} data-page="${currentPage + 1}">›</button>`;

    container.innerHTML = `
      <div class="pagination-info">共 ${totalItems} 条记录，第 ${currentPage}/${totalPages} 页</div>
      <div class="pagination-controls">
        ${pageBtns}
        <select class="page-size-select">
          <option value="10" ${pageSize === 10 ? 'selected' : ''}>10条/页</option>
          <option value="20" ${pageSize === 20 ? 'selected' : ''}>20条/页</option>
          <option value="50" ${pageSize === 50 ? 'selected' : ''}>50条/页</option>
        </select>
      </div>
    `;
  }

  function isImgSrc(v) {
    if (!v) return false;
    const s = String(v).trim();
    return /^https?:\/\//i.test(s) || s.indexOf('/uploads/') === 0;
  }

  function imgSrcHtml(v, alt) {
    if (!isImgSrc(v)) return '';
    return '<img src="' + escHtml(v) + '" alt="' + escHtml(alt || 'img') + '" loading="lazy">';
  }

  async function uploadFile(file, opts) {
    opts = opts || {};
    const fd = new FormData();
    fd.append('file', file);
    const headers = {};
    const t = token();
    if (t) headers['Authorization'] = 'Bearer ' + t;
    const ctrl = (typeof AbortController !== 'undefined') ? new AbortController() : null;
    let timer = null;
    if (ctrl) timer = setTimeout(function () { ctrl.abort(); }, 60000);
    let resp;
    try {
      resp = await fetch(API_BASE + '/upload', { method: 'POST', headers: headers, body: fd, signal: ctrl ? ctrl.signal : undefined });
    } catch (e) {
      showToast(e && e.name === 'AbortError' ? '上传超时，请重试' : '上传失败：网络异常', 'error');
      throw e;
    } finally {
      if (ctrl && timer) clearTimeout(timer);
    }
    let json = null;
    try { json = await resp.json(); } catch (e) { json = null; }
    const msg = (json && json.message) || ('上传失败(' + resp.status + ')');
    const authExpired = resp.status === 401 || (json && (json.code === 1001 || json.code === 1002));
    if (authExpired) {
      clearSession();
      showToast('登录状态已失效，请重新登录', 'warning');
      setTimeout(function () { window.location.replace(menuRoot() + 'login.html'); }, 500);
      const err = new Error(msg);
      err.code = (json && json.code) || 0;
      throw err;
    }
    if (!json || json.code !== 0) {
      const err = new Error(msg);
      err.code = json ? json.code : 0;
      if (!opts.silent) showToast(msg, 'error');
      throw err;
    }
    return json.data;
  }

  function enableImageUpload(cfg) {
    const input = cfg.input;
    if (!input) return null;
    let btn = cfg.btn || null;
    if (!btn) {
      btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'btn btn-sm btn-secondary upload-trigger';
      btn.textContent = cfg.hint || '上传';
      input.insertAdjacentElement('afterend', btn);
    }
    if (btn.dataset.uploadBound === '1') return btn;
    btn.dataset.uploadBound = '1';
    const pick = function () {
      let fileInput = btn._uploadFileInput || null;
      if (!fileInput || !fileInput.isConnected) {
        fileInput = document.createElement('input');
        fileInput.type = 'file';
        fileInput.accept = cfg.accept || 'image/*';
        fileInput.style.display = 'none';
        btn._uploadFileInput = fileInput;
        (btn.parentElement || document.body).appendChild(fileInput);
        fileInput.addEventListener('change', async function () {
          const f = fileInput.files && fileInput.files[0];
          fileInput.value = '';
          if (!f) return;
          if (f.type && f.type.indexOf('image/') !== 0) { showToast('仅支持图片文件', 'error'); return; }
          const max = (cfg.maxMB || 5) * 1024 * 1024;
          if (f.size > max) { showToast('图片大小不能超过 ' + (cfg.maxMB || 5) + 'MB', 'error'); return; }
          const oldText = btn.textContent;
          btn.disabled = true;
          btn.textContent = cfg.uploadingText || '上传中…';
          try {
            const d = await uploadFile(f);
            input.value = d.url;
            input.dispatchEvent(new Event('input'));
            if (cfg.onUpload) cfg.onUpload(d, input);
            if (!cfg.silent) showToast('上传成功', 'success');
          } catch (e) { /* toast 已提示 */ } finally {
            btn.disabled = false;
            btn.textContent = oldText;
          }
        });
      }
      fileInput.click();
    };
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      pick();
    });
    return btn;
  }

  window.AdminUI = {
    SESSION_KEY: SESSION_KEY,
    API_BASE: API_BASE,
    getSession: getSession,
    setSession: setSession,
    clearSession: clearSession,
    esc: escHtml,
    escHtml: escHtml,
    fmtTime: fmtTime,
    flattenTree: flattenTree,
    debounce: debounce,
    can: can,
    request: request,
    get: getApi,
    findRow: findRowApi,
    post: postApi,
    put: putApi,
    del: delApi,
    download: download,
    uploadFile: uploadFile,
    enableImageUpload: enableImageUpload,
    isImgSrc: isImgSrc,
    imgSrcHtml: imgSrcHtml,
    renderSidebar: renderSidebar,
    renderHeader: renderHeader,
    initPage: initPage,
    openModal: openModal,
    closeModal: closeModal,
    openDrawer: openDrawer,
    closeDrawer: closeDrawer,
    initTabs: initTabs,
    initCheckAll: initCheckAll,
    initTree: initTree,
    createCatTreeSelect: createCatTreeSelect,
    confirmAction: confirmAction,
    showToast: showToast,
    renderPagination: renderPagination,
    updateBatchBar: updateBatchBar,
    navigateTo: navigateTo
  };

  /* ========== SPA 化侧栏导航：点击子项只更新主区，侧栏/头部/浮层不重绘 ========== */
  function findActiveInfo(url) {
    try {
      const u = new URL(url, location.origin);
      const path = u.pathname;
      const prefix = menuRoot();
      for (const g of menuData) {
        for (const it of g.items) {
          if (it.children) {
            for (const c of it.children) {
              const full = prefix + c.href;
              if (full === path || path.indexOf(full) !== -1) return { key: c.key, group: it.key, groupText: g.group, itemText: c.text, href: new URL(full, location.origin).href };
            }
          } else if (it.href) {
            const full = prefix + it.href;
            if (full === path || path.indexOf(full) !== -1) return { key: it.key, group: it.key, groupText: g.group, itemText: it.text, href: new URL(full, location.origin).href };
          }
        }
      }
    } catch (e) { }
    return null;
  }

  function updateActiveByKey(key, href) {
    const target = href ? new URL(href, location.origin).href : null;
    const isActive = function (a) {
      if (a.getAttribute('data-key') === key) return true;
      if (target && a.href === target) return true;
      return false;
    };
    const sb = document.getElementById('sidebar');
    if (sb) sb.querySelectorAll('a.menu-item').forEach(a => a.classList.toggle('active', isActive(a)));
    if (collapsedPop) collapsedPop.querySelectorAll('a.menu-item').forEach(a => a.classList.toggle('active', isActive(a)));
  }

  function updateBreadcrumbByInfo(info) {
    const bc = document.querySelector('#header .breadcrumb');
    if (!bc) return;
    const arr = [info.groupText, info.itemText].filter(Boolean);
    bc.innerHTML = arr.map((t, i) => i === arr.length - 1
      ? '<span class="breadcrumb-current">' + escHtml(t) + '</span>'
      : '<span>' + escHtml(t) + '</span><span class="breadcrumb-sep">/</span>'
    ).join('');
  }

  function ensureStyleAvailable(href) {
    const head = document.head;
    return Array.from(head.querySelectorAll('link[rel="stylesheet"]')).some(l => l.href === href);
  }

  async function navigateTo(url, opts) {
    opts = opts || {};
    let absUrl;
    try {
      const u = new URL(url, location.origin);
      absUrl = u.pathname + u.search + u.hash;
    } catch (e) {
      absUrl = url;
    }
    let main, newMain;
    try {
      const resp = await fetch(absUrl, { headers: { 'X-Requested-With': 'spa' } });
      if (!resp.ok) { location.href = absUrl; return; }
      const text = await resp.text();
      const doc = new DOMParser().parseFromString(text, 'text/html');
      newMain = doc.querySelector('main.content');
      main = document.querySelector('main.content');
      if (!newMain || !main) { location.href = absUrl; return; }
      // 清掉上一次 SPA 切换注入的 page-specific 样式
      document.head.querySelectorAll('style[data-spa-page="1"]').forEach(s => s.remove());
      // 注入新页面 head 中的 stylesheet（去重）
      const base = new URL(absUrl, location.origin);
      doc.querySelectorAll('head link[rel="stylesheet"]').forEach(link => {
        const href = link.getAttribute('href');
        if (!href) return;
        const abs = new URL(href, base.href).href;
        if (ensureStyleAvailable(abs)) return;
        const nl = document.createElement('link');
        nl.rel = 'stylesheet';
        nl.href = abs;
        document.head.appendChild(nl);
      });
      // 注入新页面 head 中 page-specific <style>
      doc.querySelectorAll('head style').forEach(st => {
        const ns = document.createElement('style');
        ns.setAttribute('data-spa-page', '1');
        ns.textContent = st.textContent;
        document.head.appendChild(ns);
      });
      // 整体换壳：保留 #sidebar 与 #header（原生 DOM + 事件监听不重绘，展开/悬浮状态不消失），
      // body 其余内容（main + 页面级 modal 等页面专属部分）整体替换，避免只换 main 丢失页面挂件
      const b = document.body;
      const oldSide = b.querySelector('#sidebar');
      const oldHead = b.querySelector('#header');
      const oldMenuEl = oldSide ? oldSide.querySelector('.sidebar-menu') : null;
      const oldScrollTop = oldMenuEl ? oldMenuEl.scrollTop : 0;
      if (oldSide) oldSide.remove();
      if (oldHead) oldHead.remove();
      b.setAttribute('data-spa-nav', '1');
      b.innerHTML = doc.body.innerHTML;
      const holderSide = b.querySelector('#sidebar');
      const holderHead = b.querySelector('#header');
      if (oldSide && holderSide) holderSide.parentNode.replaceChild(oldSide, holderSide);
      if (oldHead && holderHead) holderHead.parentNode.replaceChild(oldHead, holderHead);
      const restoredMenuEl = oldSide ? oldSide.querySelector('.sidebar-menu') : null;
      if (restoredMenuEl) restoredMenuEl.scrollTop = oldScrollTop;
      main = b.querySelector('main.content');
      // 重新执行新页面脚本（跳过 common.js 引用，避免重复初始化）
      const allScripts = Array.from(doc.querySelectorAll('script'));
      allScripts.forEach(s => {
        const src = s.getAttribute('src');
        if (!src || /common\.js/.test(src)) return;
        const ns = document.createElement('script');
        Array.from(s.attributes).forEach(a => ns.setAttribute(a.name, a.value));
        ns.text = s.textContent;
        b.appendChild(ns);
      });
      // 页面内联脚本：合并后包进独立函数作用域执行。
      // 整页模式下各页顶层 const/let（如 API/F/PAGE）共享全局词法环境，SPA 重复注入会 SyntaxError，
      // 故 IIFE 隔离；顶层具名函数提升为 window 成员，保证内联 onclick（如 viewDetail(1)）仍可调用。
      const inlineScripts = allScripts.filter(s => !s.getAttribute('src'));
      if (inlineScripts.length) {
        let code = inlineScripts.map(s => s.textContent || '').join('\n;\n');
        const topFns = [];
        // 顶层普通 / async / 生成器函数声明
        code = code.replace(/^[ \t]*(?:async[ \t]+)?function[ \t]*(?:\*[ \t]*)?([A-Za-z_$][\w$]*)[ \t]*\(/gm, function (m, name) {
          topFns.push(name);
          return m;
        });
        // 顶层 const/let/var 直接赋函数或箭头函数（如 openX = () => {...}）
        code = code.replace(/^[ \t]*(?:const|let|var)[ \t]+([A-Za-z_$][\w$]*)[ \t]*=[ \t]*(?:async[ \t]*)?(?:function|\()/gm, function (m, name) {
          topFns.push(name);
          return m;
        });
        const exports = [];
        Array.from(new Set(topFns)).forEach(function (name) {
          exports.push('if (typeof ' + name + ' !== \'undefined\') { window.' + name + ' = ' + name + '; }');
        });
        const ns = document.createElement('script');
        ns.textContent = ';(function () {\n' + code + '\n' + (exports.length ? exports.join('\n') : '') + '\n})();';
        b.appendChild(ns);
      }
      const info = findActiveInfo(absUrl);
      if (info) { updateActiveByKey(info.key, info.href); updateBreadcrumbByInfo(info); }
      // 折叠态：保持浮层持续显示并按新 active 重画（换壳会销毁旧浮层，需重建）
      if (document.body.classList.contains('sidebar-collapsed') && collapsedPop && collapsedPop.classList.contains('show')) {
        const groupKey = info ? info.group : null;
        const trigger = groupKey ? document.querySelector('.sidebar [data-toggle="' + groupKey + '"]') : null;
        if (trigger) {
          if (!collapsedPop.isConnected) collapsedPop = null;
          showCollapsedPop(trigger);
        } else {
          hideCollapsedPop(true);
        }
      }
      document.title = doc.title || document.title;
    } catch (e) {
      location.href = absUrl;
      return;
    }
    if (!opts.fromPop) history.pushState({ spa: true }, '', absUrl);
  }

  function setupSidebarSpaNav() {
    const sb = document.getElementById('sidebar');
    if (sb) {
      sb.addEventListener('click', function (e) {
        const a = e.target.closest && e.target.closest('a.menu-item');
        if (!a) return;
        const href = a.getAttribute('href');
        if (!href || href.startsWith('javascript:') || href.startsWith('#') || a.target === '_blank') return;
        e.preventDefault();
        navigateTo(a.href);
      });
    }
    document.addEventListener('click', function (e) {
      const pop = e.target.closest && e.target.closest('.collapsed-pop a.menu-item');
      if (!pop) return;
      const href = pop.getAttribute('href');
      if (!href || href.startsWith('javascript:') || href.startsWith('#') || pop.target === '_blank') return;
      e.preventDefault();
      e.stopPropagation();
      navigateTo(pop.href);
    });
    window.addEventListener('popstate', function () {
      navigateTo(location.href, { fromPop: true });
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    try {
      if (localStorage.getItem(COLLAPSE_KEY) === '1') document.body.classList.add('sidebar-collapsed');
    } catch (e) { }
    setupSidebarSpaNav();
    initTabs();
    initCheckAll();
    initTree();

    document.addEventListener('click', function () {
      document.querySelectorAll('.header-user.open').forEach(el => el.classList.remove('open'));
    });
  });
})();
