from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

CONFIDENCE_VERIFIED = "verified"
CONFIDENCE_OBSERVED = "observed"
CONFIDENCE_ESTIMATED = "estimated"
CONFIDENCE_RECOMMENDED = "recommended"
CONFIDENCE_NO_DATA = "no_data"

SOURCE_GSC_API = "gsc_api"
SOURCE_GA4_API = "ga4_api"
SOURCE_PAGESPEED_API = "pagespeed_api"
SOURCE_SERP_SNAPSHOT = "serp_snapshot"
SOURCE_SERP_HISTORY = "serp_history"
SOURCE_SITE_AUDIT = "site_audit"
SOURCE_WEBSITE_INSIGHTS = "website_insights"
SOURCE_MANUAL = "manual"
SOURCE_RECOMMENDED = "recommended"
SOURCE_MISSING = "missing"


@dataclass
class Evidence:
    value: Any = None
    source: str = SOURCE_MISSING
    timestamp: str = ""
    confidence: str = CONFIDENCE_NO_DATA
    proof_url: str | None = None

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat(timespec="seconds")

    @property
    def is_verified(self) -> bool:
        return self.confidence == CONFIDENCE_VERIFIED

    @property
    def is_available(self) -> bool:
        return self.confidence != CONFIDENCE_NO_DATA and self.value is not None

    @property
    def display_value(self) -> str:
        if self.is_available:
            return str(self.value)
        return "\u2014"

    @property
    def confidence_label(self) -> str:
        labels = {
            CONFIDENCE_VERIFIED: "Verified",
            CONFIDENCE_OBSERVED: "Observed",
            CONFIDENCE_ESTIMATED: "Estimated",
            CONFIDENCE_RECOMMENDED: "Recommended",
            CONFIDENCE_NO_DATA: "No Data",
        }
        return labels.get(self.confidence, "Unknown")

    @classmethod
    def missing(cls) -> Evidence:
        return cls(value=None, source=SOURCE_MISSING, confidence=CONFIDENCE_NO_DATA)

    @classmethod
    def verified(cls, value: Any, source: str, proof_url: str | None = None) -> Evidence:
        return cls(value=value, source=source, confidence=CONFIDENCE_VERIFIED, proof_url=proof_url)

    @classmethod
    def observed(cls, value: Any, source: str) -> Evidence:
        return cls(value=value, source=source, confidence=CONFIDENCE_OBSERVED)

    @classmethod
    def estimated(cls, value: Any, source: str = SOURCE_RECOMMENDED) -> Evidence:
        return cls(value=value, source=source, confidence=CONFIDENCE_ESTIMATED)

    @classmethod
    def recommended(cls, value: Any) -> Evidence:
        return cls(value=value, source=SOURCE_RECOMMENDED, confidence=CONFIDENCE_RECOMMENDED)
