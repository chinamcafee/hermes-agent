"""PII and secret detection for memory review items."""

from __future__ import annotations

from dataclasses import dataclass, replace
import re
from typing import Any, Protocol


@dataclass(frozen=True)
class SafetyDetection:
    sensitivity: str
    findings: tuple[str, ...] = ()
    reject: bool = False


class SafetyClassifier(Protocol):
    def classify(self, text: str) -> SafetyDetection: ...


class RegexSafetyClassifier:
    EMAIL_RE = re.compile(r"\b[^@\s]+@[^@\s]+\.[^@\s]+\b")
    SECRET_RE = re.compile(r"\b(?:OPENAI_API_KEY|API_KEY|TOKEN|SECRET)\s*=\s*\S+|\bsk-[A-Za-z0-9_-]{8,}")

    def classify(self, text: str) -> SafetyDetection:
        findings: list[str] = []
        if self.SECRET_RE.search(text):
            findings.append("secret_token")
            return SafetyDetection(
                sensitivity="secret",
                findings=tuple(findings),
                reject=True,
            )
        if self.EMAIL_RE.search(text):
            findings.append("email_address")
            return SafetyDetection(sensitivity="pii", findings=tuple(findings))
        return SafetyDetection(sensitivity="normal")


class MemoryPiiSecretDetector:
    def __init__(
        self,
        *,
        review_repository: Any,
        memory_service: Any,
        classifier: SafetyClassifier | None = None,
    ) -> None:
        self.review_repository = review_repository
        self.memory_service = memory_service
        self.classifier = classifier or RegexSafetyClassifier()

    def process_pending(self, *, limit: int = 100) -> dict[str, int]:
        items = [
            item
            for item in self.review_repository.review_items.values()
            if item.status == "pending"
        ][:limit]
        summary = {
            "selected": len(items),
            "pii": 0,
            "secrets": 0,
            "rejected": 0,
            "unchanged": 0,
        }
        for item in items:
            memory = self.memory_service.items.get(item.memory_id)
            if memory is None:
                summary["unchanged"] += 1
                continue
            detection = self.classifier.classify(memory["content"])
            if detection.sensitivity == "normal" and not detection.findings:
                summary["unchanged"] += 1
                continue
            if detection.sensitivity == "secret" or detection.reject:
                self._mark_secret(item, memory, detection)
                summary["secrets"] += 1
                summary["rejected"] += 1
                continue
            self._mark_pii(item, memory, detection)
            summary["pii"] += 1
        return summary

    def _mark_pii(
        self,
        item: Any,
        memory: dict[str, Any],
        detection: SafetyDetection,
    ) -> None:
        self.memory_service.update_memory(
            memory["id"],
            {"sensitivity": detection.sensitivity},
        )
        self.review_repository.review_items[item.id] = replace(
            item,
            review_kind="pii",
            reason="pii_detected",
            candidate_payload={
                **item.candidate_payload,
                "safety_findings": list(detection.findings),
                "safety_sensitivity": detection.sensitivity,
            },
        )

    def _mark_secret(
        self,
        item: Any,
        memory: dict[str, Any],
        detection: SafetyDetection,
    ) -> None:
        self.memory_service.update_memory(
            memory["id"],
            {
                "sensitivity": "secret",
                "status": "rejected",
            },
        )
        self.review_repository.review_items[item.id] = replace(
            item,
            status="rejected",
            review_kind="pii",
            reason="secret_detected",
            candidate_payload={
                **item.candidate_payload,
                "safety_findings": list(detection.findings),
                "safety_sensitivity": "secret",
            },
        )
