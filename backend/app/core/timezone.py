"""业务统一时区：东八区（Asia/Shanghai）。

所有「业务时间」——落库的 datetime 字段、JSON 响应中的 created_at / last_login_time
等——统一使用 Asia/Shanghai 时区生成。数据库会话时区由 core.database 在 init_pool
中通过 `SET time_zone='+08:00'` 强制为东八区，与本模块保持一致。

老历史数据若原以 UTC 字面量落库（容器/MySQL 默认时区为 UTC 时期产生的记录），
前端 fmtTime 会按「naive 字符串 = 业务时区(CST)」解析后转本机时区显示，会与新记录
出现 8 小时差异；新数据从此刻起均为东八区，行为一致。
"""

from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo  # Python 3.9+

    _CST = ZoneInfo("Asia/Shanghai")
except Exception:  # noqa: BLE001 - 环境无 tzdata 时降级，见下注释
    # 部分环境（Windows / 精简 Python）未安装 tzdata 包，ZoneInfo(key) 会抛
    # ZoneInfoNotFoundError（KeyError 子类，非 ImportError，故此处必须宽捕获）。
    # 中国全境自 1991 年起无夏令时，固定 +08:00 与 Asia/Shanghai 全年等价。
    _CST = timezone(timedelta(hours=8))

TZ_NAME = "Asia/Shanghai"
TZ_OFFSET = "+08:00"


def now() -> datetime:
    """业务当前时间，aware(Asia/Shanghai)。"""
    return datetime.now(_CST)


def to_naive(dt: datetime | None) -> datetime | None:
    """aware -> naive（保持字面量不变），用于 MySQL DATETIME 字段写入。"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt
    return dt.replace(tzinfo=None)
