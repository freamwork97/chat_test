from __future__ import annotations

from datetime import datetime

import pytz

KST = pytz.timezone("Asia/Seoul")


def as_kst_naive(ts_str: str | None):
    """Convert an ISO timestamp string to naive Asia/Seoul datetime."""
    if ts_str:
        try:
            return (
                datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                .astimezone(KST)
                .replace(tzinfo=None)
            )
        except Exception:
            pass
    return datetime.now(KST).replace(tzinfo=None)


def kst_iso_now():
    return datetime.now(KST).isoformat()

