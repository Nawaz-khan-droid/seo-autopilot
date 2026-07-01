"""Issue dataclass — output canónico de toda regla."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

Severity = Literal["critical", "warning", "info"]


@dataclass(frozen=True, slots=True)
class Issue:
    rule_id: str
    severity: Severity
    category: str
    message: str
    url_id: int | None = None
    evidence: dict[str, Any] = field(default_factory=dict)
    detected_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc),
    )

    @property
    def issue_id(self) -> int:
        payload = json.dumps(
            {
                "rule": self.rule_id,
                "url": self.url_id,
                "evidence": self.evidence,
            },
            sort_keys=True,
            default=str,
        )
        digest = hashlib.blake2b(payload.encode(), digest_size=8).digest()
        return int.from_bytes(digest, "big", signed=False)

    def to_row(self) -> dict[str, Any]:
        d = asdict(self)
        d["issue_id"] = self.issue_id
        d["evidence"] = json.dumps(self.evidence, default=str)
        return d
