from datetime import datetime, timezone
from typing import Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:8]}"


class Source(BaseModel):
    session_id: str
    turn: int


class Memory(BaseModel):
    id: str = Field(default_factory=lambda: _new_id("mem"))
    user_id: str
    type: Literal["semantic", "episodic", "procedural"] = "semantic"
    content: str
    entities: list[str] = Field(default_factory=list)
    source: Optional[Source] = None
    confidence: float = 1.0
    created_at: datetime = Field(default_factory=_now)
    valid_from: datetime = Field(default_factory=_now)
    valid_to: Optional[datetime] = None
    superseded_by: Optional[str] = None
    last_accessed: Optional[datetime] = None
    access_count: int = 0


class TraceEvent(BaseModel):
    ts: datetime = Field(default_factory=_now)
    op: Literal["extract", "add", "update", "search", "forget"]
    user_id: str
    input: str
    result: dict = Field(default_factory=dict)
    reason: str