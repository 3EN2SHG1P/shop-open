/* ============================================
   模拟扫码收银 wechat-pay.html（specs/商城前台V1.2.spec.md §8.11）
   - 进页订单仍待付款（payment 不预置成功）
   - 进入即轮询 GET /pay/{orderNo}/status（2s/次，最长 60s）
   - 用户点「我已完成支付」→ POST /pay/{orderNo} 置成功 → 跳 orders.html?tab=paid
   - 轮询/回调已支付同样跳 orders；倒计时超时或 3006 → 跳 orders 提示超时重下
   - 「返回重选」回 payment
   依赖：ui.js / api.js / auth.js
   ============================================ */
(function (window, document) {
  'use strict';

  var U = window.ShopUI;
  var Api = window.ShopApi;
  var S = window.ShopUtil;

  var TIMEOUT_MINUTES = 14;
  var POLL_INTERVAL = 2000;
  var POLL_MAX = 60000;

  var orderNo = S.getParam('orderNo');
  var detail = null;
  var deadline = 0;
  var pollTimer = null;
  var expireTimer = null;
  var pollStart = 0;
  var finished = false;

  function $(id) { return document.getElementById(id); }

  function goOrders(msg, tab) {
    finished = true;
    stopTimers();
    if (msg) U.toast(msg, tab === 'paid' ? 'success' : 'warn');
    window.location.href = 'orders.html' + (tab ? '?tab=' + tab : '');
  }

  function stopTimers() {
    if (pollTimer) { window.clearInterval(pollTimer); pollTimer = null; }
    if (expireTimer) { window.clearInterval(expireTimer); expireTimer = null; }
  }

  function fmtRemain(ms) {
    if (ms <= 0) return '0小时 0分';
    var total = Math.floor(ms / 1000);
    var h = Math.floor(total / 3600);
    var m = Math.floor((total % 3600) / 60);
    return h + '小时 ' + m + '分';
  }

  function tickCountdown() {
    var left = deadline - Date.now();
    var el = $('jsCountdown');
    if (el) el.textContent = fmtRemain(left);
    if (left <= 0) goOrders('订单已超时，请重新下单');
  }

  function onPaid() {
    goOrders('支付成功', 'paid');
  }

  function startPolling() {
    pollStart = Date.now();
    pollTimer = window.setInterval(function () {
      if (finished) return;
      if (Date.now() - pollStart >= POLL_MAX) { stopTimers(); return; }
      Api.payStatus(orderNo).then(function (st) {
        if (finished) return;
        if (Number(st.payStatus) === 1) onPaid();
      }).catch(function () {});
    }, POLL_INTERVAL);
  }

  function render() {
    if (!detail) return;
    if ($('jsOrderNo')) $('jsOrderNo').textContent = detail.orderNo || '';
    var amt = S.money(detail.payAmount);
    if ($('jsPayAmount')) $('jsPayAmount').textContent = amt;
    if ($('jsModalAmount')) $('jsModalAmount').textContent = amt;

    if (Number(detail.orderStatus) !== 1) {
      // 订单已非待付款（可能已在他处支付/取消）→ 回订单列表
      goOrders(Number(detail.orderStatus) === 5 ? '订单已取消' : '订单状态已变更');
      return;
    }
    var created = S.parseTime(detail.createdAt);
    deadline = (created ? created.getTime() : Date.now()) + TIMEOUT_MINUTES * 60 * 1000;
    tickCountdown();
    expireTimer = window.setInterval(tickCountdown, 1000);
    startPolling();
  }

  function bindEvents() {
    document.addEventListener('click', function (e) {
      if (e.target.closest('#jsBackBtn') || e.target.closest('#jsBackBtn2')) {
        stopTimers();
        finished = true;
        window.location.href = 'payment.html?orderNo=' + encodeURIComponent(orderNo);
        return;
      }
      if (e.target.closest('#jsPaySuccessBtn')) {
        var btn = $('jsPaySuccessBtn');
        U.busy(btn, function () {
          return Api.payOrder(orderNo, detail ? detail.payType : 1).then(function () {
            onPaid();
          }).catch(function (err) {
            var code = err && err.code;
            if (code === 3006) { goOrders('订单已超时，请重新下单'); return; }
            U.toast((err && err.message) || '支付失败', 'error');
            throw err;
          });
        });
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
