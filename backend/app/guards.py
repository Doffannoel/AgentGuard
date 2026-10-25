import json
import re
from typing import Any

from .db import canonical

PATTERNS = [
    ("SECRET_EXPOSURE", "BEARER_TOKEN", re.compile(r"(?i)bearer\s+[a-z0-9._~+/=-]+")),
    (
        "SECRET_EXPOSURE",
        "API_KEY",
        re.compile(r"(?:ag_(?:live|test)_[A-Za-z0-9_-]+|sk-[A-Za-z0-9_-]{8,}|AKIA[A-Z0-9]{16})"),
    ),
    ("PII_DETECTED", "EMAIL", re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")),
    ("PII_DETECTED", "PHONE", re.compile(r"(?<!\w)\+\d[\d ()-]{7,}\d")),
]
SECRET_FIELDS = re.compile(r"(?i)^(password|secret|api[_-]?key|access[_-]?token|authorization)$")
SUSPICIOUS = re.compile(
    r"(?i)ignore (?:all |the )?(?:previous|prior) instructions|system prompt|bypass (?:security|policy)|jailbreak"
)


def inspect(value: Any) -> tuple[Any, list[dict]]:
    findings = []

    def finding(kind, subtype, action="REDACTED"):
        item = {
            "type": kind,
            "subtype": subtype,
            "detected": subtype,
            "severity": "high" if kind == "SECRET_EXPOSURE" else "medium",
            "action": action,
        }
        if item not in findings:
            findings.append(item)

    def redact(item):
        if isinstance(item, dict):
            result = {}
            for key, val in item.items():
                if SECRET_FIELDS.fullmatch(key):
                    finding("SECRET_EXPOSURE", "CREDENTIAL_FIELD")
                    result[key] = "[REDACTED]"
                else:
                    result[key] = redact(val)
            return result
        if isinstance(item, list):
            return [redact(val) for val in item]
        if not isinstance(item, str):
            return item
        if item.lstrip().startswith(("{", "[")):
            try:
                parsed = json.loads(item)
            except (ValueError, RecursionError):
                pass
            else:
                return json.dumps(redact(parsed), ensure_ascii=False)
        if SUSPICIOUS.search(item):
            finding("SUSPICIOUS_INSTRUCTION", "INSTRUCTION_OVERRIDE", "FLAGGED")
        for kind, subtype, pattern in PATTERNS:
            if pattern.search(item):
                finding(kind, subtype)
                item = pattern.sub(f"[REDACTED_{subtype}]", item)
        return item

    # ponytail: deterministic patterns miss obfuscated PII; add detectors against measured replay gaps.
    return redact(value), findings


def token_ceiling(value) -> int:
    # UTF-8 byte count is a conservative reservation for byte-level provider tokenizers.
    return len(canonical(value).encode()) + 64
