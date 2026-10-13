class BizError(Exception):
    def __init__(self, code: int, message: str, http_status: int = 200):
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


def biz(code: int, message: str, http_status: int = 200):
    raise BizError(code, message, http_status)


def bad_request(message: str = "参数错误"):
    biz(2001, message, 422)


def not_found(message: str = "资源不存在"):
    biz(2001, message, 404)


def duplicate(message: str = "数据重复"):
    biz(3004, message)


def referenced(message: str = "存在关联数据，不可删除"):
    biz(3003, message)


def state_error(message: str = "当前状态不允许此操作"):
    biz(3002, message)


def stock_not_enough(message: str = "库存不足"):
    biz(3001, message)


def not_stackable(message: str = "该商品不参与叠加优惠"):
    biz(3005, message)


def order_timeout(message: str = "订单已超时，请重新下单"):
    biz(3006, message)


def coupon_unavailable(message: str = "优惠券不可用"):
    biz(3007, message)


def buy_limit(message: str = "超出该商品限购数量"):
    biz(3008, message)


def no_permission(message: str = "无接口权限"):
    biz(4001, message, 403)


def no_data_permission(message: str = "无数据权限"):
    biz(4002, message, 403)


def auth_failed(message: str = "登录状态无效或已过期"):
    biz(1001, message, 401)


def not_logged_in(message: str = "未登录"):
    biz(1002, message, 401)


def account_locked(message: str = "登录失败次数超限，账号已锁定，请稍后再试"):
    biz(1003, message, 423)


def server_error(message: str = "服务器内部错误"):
    biz(5000, message, 500)
