"""Persian/RTL display helpers: digits, money, data sizes, Jalali dates."""
from __future__ import annotations

from datetime import datetime

import jdatetime

_EN_TO_FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def to_fa_digits(value: object) -> str:
    return str(value).translate(_EN_TO_FA)


def toman(amount: int, *, fa: bool = True) -> str:
    s = f"{amount:,}"
    s = to_fa_digits(s) if fa else s
    return f"{s} تومان"


def human_bytes(num: int, *, fa: bool = True) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(num)
    unit = units[0]
    for unit in units:
        if value < 1024 or unit == units[-1]:
            break
        value /= 1024
    out = f"{value:.2f}".rstrip("0").rstrip(".") + f" {unit}"
    return to_fa_digits(out) if fa else out


def gb(num_gb: int, *, fa: bool = True) -> str:
    out = f"{num_gb} گیگابایت"
    return to_fa_digits(out) if fa else out


def jalali(dt: datetime, *, with_time: bool = False, fa: bool = True) -> str:
    jd = jdatetime.datetime.fromgregorian(datetime=dt)
    fmt = "%Y/%m/%d %H:%M" if with_time else "%Y/%m/%d"
    out = jd.strftime(fmt)
    return to_fa_digits(out) if fa else out
