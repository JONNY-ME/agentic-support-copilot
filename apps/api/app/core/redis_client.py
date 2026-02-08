from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

import redis as redis_lib

@lru_cache(maxsize=1)
def get_redis() -> Optional[redis_lib.Redis]:
    url = os.getenv("REDIS_URL", "")
    if not url:
        return None
    try:
        r = redis_lib.from_url(url, decode_responses=True)
        r.ping()
        return r
    except Exception:
        return None
