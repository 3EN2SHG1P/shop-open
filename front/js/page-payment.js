/* ============================================
   收银台 payment.html（specs/商城前台V1.2.spec.md §8.10）
   - ?orderNo= 查订单展示应付/订单号
   - 支付方式二选（后端 payType 枚举：1=扫码支付、2=快捷支付，均为演示模拟，不接真实网关）
   - 倒计时按订单创建时间 + 超时分钟数（与后端 3006 兜底口径一致）
   - 本页不直接调 pay：立即支付 → 跳 wechat-pay.html?orderNo=（支付动作收敛在收银台页）
   依赖：ui.js / api.js / auth.js
   ============================================ */
(function (window, document) {
  'use strict';

  var U = window.ShopUI;
  var Api = window.ShopApi;
  var S = window.ShopUtil;

  var TIMEOUT_MINUTES = 14; // 与 backend config.order_pay_timeout_minutes 一致

  var orderNo = S.getParam('orderNo');
  var detail = null;
  var deadline = 0;
  var timer = null;

  function $(id) { return document.getElementById(id); }

  function goOrders(msg, tab) {
    if (msg) U.toast(msg, 'warn');
    window.location.href = 'orders.html' + (tab ? '?tab=' + tab : '');
  }

  function fmtRemain(ms) {
    if (ms <= 0) return '0小时 0分';
    var total = Math.floor(ms / 1000);
    var h = Math.floor(total / 3600);
    var m = Math.floor((total % 3600) / 60);
    return h + '小时 ' + m + '分';
  }

  function tick() {
    var left = deadline - Date.now();
    var el = $('jsCountdown');
    if (el) el.textContent = fmtRemain(left);
    if (left <= 0) {
      stopTimer();
      goOrders('订单已超时，请重新下单');
    }
  }

  function stopTimer() {
    if (timer) { window.clearInterval(timer); timer = null; }
  }

  function render() {
    if (!detail) return;
    if ($('jsOrderNo')) $('jsOrderNo').textContent = detail.orderNo || '';
    if ($('jsPayAmount')) $('jsPayAmount').textContent = S.money(detail.payAmount);

    if (Number(detail.orderStatus) !== 1) {
      // 订单已非待付款（已支付/已取消等）→ 回到订单列表
      var tip = Number(detail.orderStatus) === 5 ? '订单已取消' : '订单状态已变更';
      goOrders(tip);
      return;
    }

    var created = S.parseTime(detail.createdAt);
    deadline = (created ? created.getTime() : Date.now()) + TIMEOUT_MINUTES * 60 * 1000;
    tick();
    stopTimer();
    timer = window.setInterval(tick, 1000);
  }

  function bindEvents() {
    document.addEventListener('click', function (e) {
      var pm = e.target.closest('.pay-method');
      if (pm) {
        Array.prototype.forEach.call(document.querySelectorAll('.pay-method'), function (m) {
          m.classList.remove('active');
        });
        pm.classList.add('active');
        return;
      }
      if (e.target.closest('#jsPayBtn')) {
        // 真实网关接入点：此处改为「生成支付单 + 跳转真实收银台」；演示环境仅跳模拟扫码页
        if (!detail || Number(detail.orderStatus) !== 1) { goOrders('订单状态已变更'); return; }
        stopTimer();
        window.location.href = 'wechat-pay.html?orderNo=' + encodeURIComponent(orderNo);
      }
    });
  }

  function init() {
    if (!orderNo) { goOrders('缺少订单号'); return; }
    bindEvents();
    Api.orderDetail(orderNo).then(function (data) {
      detail = data;
      render();
    }).catch(function (err) {
      var code = err && err.code;
      if (code === 3006) { goOrders('订单已超时，请重新下单'); return; }
      U.toast((err && err.message) || '订单加载失败', 'error');
    });
  }

  init();
})(window, document);
