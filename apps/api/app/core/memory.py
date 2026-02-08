from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

import redis as redis_lib

from app.core.redis_client import get_redis

class MemoryStore:
    def __init__(self, redis_client: Optional[redis_lib.Redis]) -> None:
        self.r = redis_client

    @classmethod
    def from_env(cls) -> "MemoryStore":
        return cls(get_redis())

    def append_turn(self, external_id: str, role: str, content: str, ts: datetime) -> None:
        if not self.r:
            return
        key = f"conv:{external_id}"
        payload = json.dumps({"role": role, "content": content, "ts": ts.isoformat()})
        self.r.rpush(key, payload)
        self.r.ltrim(key, -20, -1)

    def set_profile_field(self, external_id: str, field: str, value: str) -> None:
        if not self.r:
            return
        self.r.hset(f"profile:{external_id}", field, value)

    def get_profile_field(self, external_id: str, field: str) -> Optional[str]:
        if not self.r:
            return None
        return self.r.hget(f"profile:{external_id}", field)
