/* ============================================
   收货地址表单脚本（specs/商城前台V1.2.spec.md §8.8 / §8.9）
   新增（address-add.html）与编辑（address-edit.html）共用
   省市区三级级联取 GET /regions?parentCode=；文本（name）落库、code 仅前端级联用
   返回目标由 ?from= 决定（仅放行站内 .html），缺省 address.html
   依赖：ui.js / api.js / auth.js
   ============================================ */
(function (window, document) {
  'use strict';

  var S = window.ShopUtil;
  var U = window.ShopUI;
  var Api = window.ShopApi;

  var PAGE = window.location.pathname.split('/').pop() || '';
  var IS_EDIT = PAGE === 'address-edit.html';

  var q = new URLSearchParams(window.location.search);
  var ADDR_ID = Number(q.get('id')) || 0;
  var FROM = q.get('from') || 'address.html';

  function $(id) { return document.getElementById(id); }
  function esc(t) { return S.esc(t); }

  /* 只放行站内 .html 相对路径。
     原先的写法 /\/.html($|\?)/ 是"包含匹配"且不锚定开头，javascript:alert(1).html 可以同时
     绕过该正则与下面的协议判断：伪协议注入 → 点取消即执行脚本。改为全串锚定 + 字符白名单。*/
  function safeFrom() {
    var f = String(FROM || '');
    return /^[\w\-./?=&%]+\.html([?#].*)?$/.test(f) ? f : 'address.html';
  }

  function goBack() {
    window.location.href = safeFrom();
  }

  /* ---------- 省市区级联 ---------- */
  function fill(sel, list, placeholder, selectedName) {
    var html = '<option value="">' + esc(placeholder) + '</option>';
    html += (list || []).map(function (r) {
      return '<option value="' + esc(r.name) + '" data-code="' + esc(r.code) + '"'
        + (selectedName && r.name === selectedName ? ' selected' : '') + '>' + esc(r.name) + '</option>';
    }).join('');
    sel.innerHTML = html;
    if (selectedName) {
      for (var i = 0; i < sel.options.length; i++) {
        if (sel.options[i].value === selectedName) { sel.selectedIndex = i; break; }
      }
    }
  }

  function codeOf(sel) {
    var opt = sel.options[sel.selectedIndex];
    return opt ? (opt.getAttribute('data-code') || '') : '';
  }

  function loadChildren(parentCode, targetSel, placeholder, selectedName) {
    return Api.regions(parentCode).then(function (data) {
      fill(targetSel, data && data.list, placeholder, selectedName);
    }).catch(function () {
      fill(targetSel, [], placeholder, selectedName);
    });
  }

  function clearChildren() {
    fill($('jsCity'), [], '请选择城市');
    fill($('jsDistrict'), [], '请选择区县');
  }

  function bindRegionEvents() {
    $('jsProvince').addEventListener('change', function () {
      var code = codeOf(this);
      clearChildren();
      if (code) loadChildren(code, $('jsCity'), '请选择城市');
    });
    $('jsCity').addEventListener('change', function () {
      var code = codeOf(this);
      fill($('jsDistrict'), [], '请选择区县');
      if (code) loadChildren(code, $('jsDistrict'), '请选择区县');
    });
  }

  /* ---------- 数据装载 ---------- */
  function loadForm(addr) {
    if (!addr) return;
    $('jsReceiver').value = addr.receiverName || '';
    $('jsPhone').value = addr.receiverPhone || '';
    $('jsDetail').value = addr.detail || '';
    $('jsDefault').checked = !!addr.isDefault;
    return Api.regions('').then(function (data) {
      fill($('jsProvince'), data && data.list, '请选择省份', addr.province);
      var provCode = codeOf($('jsProvince'));
      if (!provCode) return;
      return loadChildren(provCode, $('jsCity'), '请选择城市', addr.city).then(function () {
        var cityCode = codeOf($('jsCity'));
        if (!cityCode) return;
        return loadChildren(cityCode, $('jsDistrict'), '请选择区县', addr.district);
      });
    });
  }

  /* ---------- 校验与提交 ---------- */
  function validate() {
    var body = {
      receiverName: $('jsReceiver').value.trim(),
      receiverPhone: $('jsPhone').value.trim(),
      province: $('jsProvince').value,
      city: $('jsCity').value,
      district: $('jsDistrict').value,
      detail: $('jsDetail').value.trim(),
      isDefault: $('jsDefault').checked ? 1 : 0
    };
    if (body.receiverName.length < 2) return { msg: '请填写收货人姓名（至少 2 个字）' };
    if (!/^1\d{10}$/.test(body.receiverPhone)) return { msg: '请填写正确的 11 位手机号' };
    if (!body.province || !body.city || !body.district) return { msg: '请选择完整的省 / 市 / 区' };
    if (body.detail.length < 5) return { msg: '详细地址太短，请填写街道门牌等信息' };
    return { body: body };
  }

  function submit() {
    var v = validate();
    if (v.msg) {
      $('jsMsg').textContent = v.msg;
      U.toast(v.msg, 'warn');
      return;
    }
    $('jsMsg').textContent = '';
    U.busy($('jsSave'), function () {
      var req = IS_EDIT ? Api.updateAddress(ADDR_ID, v.body) : Api.createAddress(v.body);
      return req.then(function () {
        U.toast(IS_EDIT ? '地址已更新' : '地址已保存', 'success');
        window.setTimeout(goBack, 500);
      });
    });
  }

  function bindActions() {
    $('jsSave').addEventListener('click', submit);
    $('jsCancel').addEventListener('click', goBack);
  }

  /* ---------- 初始化 ---------- */
  bindActions();
  bindRegionEvents();

  if (IS_EDIT) {
    if (!ADDR_ID) {
      U.toast('缺少地址参数', 'error');
      window.setTimeout(goBack, 600);
      return;
    }
    Api.addresses().then(function (data) {
      var list = (data && data.list) || [];
      var hit = null;
      for (var i = 0; i < list.length; i++) {
        if (list[i].id === ADDR_ID) { hit = list[i]; break; }
      }
      if (!hit) {
        U.toast('地址不存在', 'error');
        window.setTimeout(goBack, 600);
        return;
      }
      loadForm(hit);
    }).catch(function () {});
  } else {
    loadChildren('', $('jsProvince'), '请选择省份');
  }
})(window, document);
