from __future__ import annotations

from dataclasses import dataclass, field

from .event import MarketEvent


@dataclass(frozen=True)
class Alert:
    event: MarketEvent
    score: int
    reasons: list[str] = field(default_factory=list)
    classification: str | None = None

    @property
    def should_send(self) -> bool:
        return self.score > 0
