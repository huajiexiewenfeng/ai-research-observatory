from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime

from .domain import EvidenceTier, SourceMethod


@dataclass(frozen=True)
class Evidence:
    schema_version: int
    evidence_id: str
    target_id: str
    source_id: str
    source_method: SourceMethod
    evidence_tier: EvidenceTier
    title: str
    url: str
    content: str
    published_at: datetime
    collected_at: datetime
    content_hash: str
    run_id: str

    @classmethod
    def create(
        cls, *, target_id: str, source_id: str, source_method: SourceMethod,
        evidence_tier: EvidenceTier, title: str, url: str, content: str,
        published_at: datetime, collected_at: datetime, run_id: str,
    ) -> "Evidence":
        normalized = " ".join(content.split())
        content_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        identity = json.dumps(
            [target_id, source_id, url, published_at.isoformat(), content_hash],
            ensure_ascii=False,
            separators=(",", ":"),
        )
        evidence_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()
        return cls(
            1, evidence_id, target_id, source_id, source_method, evidence_tier,
            title.strip(), url, normalized, published_at, collected_at, content_hash, run_id,
        )

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["source_method"] = self.source_method.value
        payload["evidence_tier"] = self.evidence_tier.value
        payload["published_at"] = self.published_at.isoformat()
        payload["collected_at"] = self.collected_at.isoformat()
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> "Evidence":
        return cls(**{
            **payload,
            "source_method": SourceMethod(payload["source_method"]),
            "evidence_tier": EvidenceTier(payload["evidence_tier"]),
            "published_at": datetime.fromisoformat(payload["published_at"]),
            "collected_at": datetime.fromisoformat(payload["collected_at"]),
        })
