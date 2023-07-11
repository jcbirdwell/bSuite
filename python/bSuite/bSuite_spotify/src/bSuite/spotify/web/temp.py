from datetime import datetime


def tz_ts(ms=False):
    """TZ posix (s) timestamp as int"""
    ts_float = datetime.now().timestamp()
    return int(ts_float * 1000 if ms else ts_float)


def utc_ts(ms=False):
    """UTC posix (s) timestamp as int"""
    ts_float = datetime.utcnow().timestamp()
    return int(ts_float * 1000 if ms else ts_float)
