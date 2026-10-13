"""业务时区模块（core/timezone）回归测试。

背景：Windows / 精简 Python 环境无 tzdata 包时，`ZoneInfo("Asia/Shanghai")` 抛
ZoneInfoNotFoundError（KeyError 子类，非 ImportError），曾导致模块导入失败、
全量测试 47 errors。本用例固化「可导入 + 东八区语义」两件事，防止回归。
"""

from datetime import timedelta

from core.timezone import TZ_NAME, TZ_OFFSET, now, to_naive


def test_timezone_module_importable():
    assert TZ_NAME == "Asia/Shanghai"
    assert TZ_OFFSET == "+08:00"


def test_now_is_aware_cst():
    t = now()
    assert t.tzinfo is not None, "now() 必须是 aware 时间"
    assert t.utcoffset() == timedelta(hours=8), f"业务时区应为 +08:00，实际 {t.utcoffset()}"


def test_to_naive_keeps_literal():
    t = now()
    n = to_naive(t)
    assert n.tzinfo is None
    assert n.replace(microsecond=0) == t.replace(tzinfo=None, microsecond=0)


def test_to_naive_passthrough():
    assert to_naive(None) is None

    from datetime import datetime

    naive = datetime(2026, 9, 5, 11, 0, 0)
    assert to_naive(naive) is naive


def test_now_literal_is_utc_plus_8h():
    """落库字面量必须是 UTC+8：比 UTC 字面量快 8 小时（aware 相减会折回同一时刻，故比较 naive 字面量）。"""
    from datetime import datetime, timezone

    utc_naive = datetime.now(timezone.utc).replace(tzinfo=None)
    diff = (to_naive(now()) - utc_naive).total_seconds()
    assert abs(diff - 8 * 3600) < 60, f"now() 字面量与 UTC 差值异常: {diff}s"
