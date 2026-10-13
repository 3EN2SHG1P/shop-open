"""金额精度统一工具。

背景（已取证）：
- MySQL 侧金额列均为 DECIMAL(10,2)，比率列 DECIMAL(5,2)（见 backend/seed/schema.py）
- aiomysql 的 DictCursor 会把 DECIMAL 映射为 decimal.Decimal（见 core/database.py）

因此**存储层恒为精确**，误差窗口只存在于 Python 侧的算术过程中。
约定：**任何金额在离开算术运算前必须量化到分**。

出口统一用 f2() 输出 float，保持 HTTP 响应契约不变，前端无需改动。
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

CENT = Decimal("0.01")
ZERO = Decimal("0.00")
DEFAULT_RATIO = 100


def d(v) -> Decimal:
    """任意来源（Decimal / float / int / str / None）→ Decimal。

    float 走 str() 中转，避免 12.34 被展开成 12.339999999999999857...
    """
    if v is None or v == "":
        return ZERO
    if isinstance(v, Decimal):
        return v
    if isinstance(v, float):
        return Decimal(str(v))
    return Decimal(v)


def q2(v) -> Decimal:
    """量化到分，ROUND_HALF_UP（财务口径）。

    不用内置 round()：它是 banker's rounding，round(0.125, 2) == 0.12，
    而财务口径应为 0.13。
    """
    try:
        return d(v).quantize(CENT, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        return ZERO


def f2(v) -> float:
    """出口序列化：量化后转 float。用于替代各 service 里的 _money()。"""
    return float(q2(v))


def add_money(*vs) -> Decimal:
    """多金额求和后量化（避免累加误差）。"""
    return q2(sum((d(v) for v in vs), ZERO))


def sub_money(a, b) -> Decimal:
    return q2(d(a) - d(b))


def mul_money(amount, factor) -> Decimal:
    return q2(d(amount) * d(factor))


def min_money(*vs) -> Decimal:
    return q2(min(d(v) for v in vs))


def cmp_money(a, b) -> int:
    """先量化再比较，杜绝 0.1 + 0.2 != 0.3 类问题。"""
    x, y = q2(a), q2(b)
    return (x > y) - (x < y)


def gt(a, b) -> bool:
    return cmp_money(a, b) > 0


def lt(a, b) -> bool:
    return cmp_money(a, b) < 0


def gte(a, b) -> bool:
    return cmp_money(a, b) >= 0


def lte(a, b) -> bool:
    return cmp_money(a, b) <= 0


def points_to_money(points, ratio: int = DEFAULT_RATIO) -> Decimal:
    """积分 → 金额。"""
    return q2(Decimal(int(points or 0)) / Decimal(ratio))


def money_to_points(amount, ratio: int = DEFAULT_RATIO) -> int:
    """金额 → 积分（反向）。用 Decimal 量化，不受 float 乘法抖动影响。"""
    return int((q2(amount) * ratio).to_integral_value(rounding=ROUND_HALF_UP))
