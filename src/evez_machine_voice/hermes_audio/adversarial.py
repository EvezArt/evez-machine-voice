from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from .score_compiler import compile_performance


class Verdict:
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class AuditFinding:
    code: str
    verdict: str
    severity: str
    message: str


@dataclass(frozen=True)
class AdversarialReport:
    version: str
    audit_sha256: str
    verdict: str
    findings: tuple[AuditFinding, ...]
    invariants_checked: tuple[str, ...]


def _hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _finding(code: str, verdict: str, severity: str, message: str) -> AuditFinding:
    return AuditFinding(code, verdict, severity, message)


def audit_performance_pair(response_text: str, plan_payload: dict[str, Any]) -> list[AuditFinding]:
    findings: list[AuditFinding] = []

    replay = compile_performance(
        response_text,
        kind=plan_payload.get("performance_kind"),
        explicit_theme=plan_payload.get("theme"),
        bpm=plan_payload.get("bpm"),
        seed=plan_payload.get("seed"),
        key=plan_payload.get("key"),
        scale=plan_payload.get("scale"),
    )
    if replay.plan_sha256 == plan_payload.get("plan_sha256"):
        findings.append(_finding(
            "PLAN_REPLAY",
            Verdict.PASS,
            "critical",
            "Performance plan reproduces exactly from its declared inputs.",
        ))
    else:
        findings.append(_finding(
            "PLAN_REPLAY",
            Verdict.FAIL,
            "critical",
            "Declared performance plan does not reproduce from its declared inputs.",
        ))

    expected_source = hashlib.sha256(response_text.encode("utf-8")).hexdigest()
    if plan_payload.get("source_sha256") == expected_source:
        findings.append(_finding(
            "SOURCE_BINDING",
            Verdict.PASS,
            "critical",
            "Plan source hash binds to the supplied response text.",
        ))
    else:
        findings.append(_finding(
            "SOURCE_BINDING",
            Verdict.FAIL,
            "critical",
            "Plan source hash does not bind to the supplied response text.",
        ))

    for field in ("theme", "bpm", "key", "scale", "performance_kind"):
        if plan_payload.get(field) == getattr(replay, field):
            findings.append(_finding(
                f"PLAN_{field.upper()}",
                Verdict.PASS,
                "high",
                f"Declared {field} matches deterministic replay.",
            ))
        else:
            findings.append(_finding(
                f"PLAN_{field.upper()}",
                Verdict.FAIL,
                "high",
                f"Declared {field} differs from deterministic replay.",
            ))

    return findings


def audit_audio_artifact(artifact: dict[str, Any]) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    state = artifact.get("state")
    path_text = artifact.get("path")
    declared_sha = artifact.get("sha256")

    if state == "PRODUCED":
        if not path_text:
            findings.append(_finding("PRODUCED_PATH", Verdict.FAIL, "critical", "PRODUCED artifact has no path."))
            return findings
        path = Path(path_text)
        if not path.exists() or not path.is_file():
            findings.append(_finding("PRODUCED_EXISTS", Verdict.FAIL, "critical", "PRODUCED artifact path does not exist."))
            return findings
        actual = _file_sha256(path)
        if actual != declared_sha:
            findings.append(_finding(
                "OUTPUT_HASH",
                Verdict.FAIL,
                "critical",
                "PRODUCED artifact SHA-256 does not match the file.",
            ))
        else:
            findings.append(_finding(
                "OUTPUT_HASH",
                Verdict.PASS,
                "critical",
                "PRODUCED artifact SHA-256 matches the file.",
            ))

        manifest = artifact.get("manifest")
        if manifest and Path(str(manifest)).exists():
            findings.append(_finding("PROVENANCE_MANIFEST", Verdict.PASS, "high", "Provenance manifest exists."))
        else:
            findings.append(_finding("PROVENANCE_MANIFEST", Verdict.UNKNOWN, "high", "No readable provenance manifest was supplied."))

    elif state in {"PLANNED", "RENDERING"}:
        if path_text or declared_sha:
            findings.append(_finding(
                "STATE_ARTIFACT_MISMATCH",
                Verdict.FAIL,
                "critical",
                f"{state} artifact carries produced-file fields before production.",
            ))
        else:
            findings.append(_finding(
                "STATE_SEPARATION",
                Verdict.PASS,
                "critical",
                f"{state} correctly carries no produced waveform claim.",
            ))
    elif state == "FAILED":
        findings.append(_finding("FAILURE_DECLARED", Verdict.PASS, "high", "Renderer failure is explicitly represented."))
    else:
        findings.append(_finding("STATE_KNOWN", Verdict.UNKNOWN, "high", "Audio artifact state is unknown."))

    return findings


def audit_bundle(
    *,
    response_text: str,
    plan_payload: dict[str, Any] | None = None,
    audio_artifact: dict[str, Any] | None = None,
    session_verification: dict[str, Any] | None = None,
) -> AdversarialReport:
    findings: list[AuditFinding] = []

    if plan_payload is not None:
        findings.extend(audit_performance_pair(response_text, plan_payload))

    if audio_artifact is not None:
        findings.extend(audit_audio_artifact(audio_artifact))

    if session_verification is not None:
        if session_verification.get("ok") is True:
            findings.append(_finding(
                "SESSION_CHAIN",
                Verdict.PASS,
                "critical",
                "Session ledger verifies from genesis to head.",
            ))
        else:
            findings.append(_finding(
                "SESSION_CHAIN",
                Verdict.FAIL,
                "critical",
                "Session ledger verification failed.",
            ))

    critical_failures = [f for f in findings if f.verdict == Verdict.FAIL and f.severity == "critical"]
    if critical_failures:
        verdict = Verdict.FAIL
    elif any(f.verdict == Verdict.UNKNOWN for f in findings):
        verdict = Verdict.UNKNOWN
    else:
        verdict = Verdict.PASS

    canonical = {
        "version": "evez-hermes-adversarial-audit/v1",
        "verdict": verdict,
        "findings": [asdict(f) for f in findings],
        "invariants_checked": [
            "CLAIMED != MEASURED",
            "PLANNED != PRODUCED",
            "PRODUCED implies existing file",
            "PRODUCED hash == file hash",
            "SOURCE HASH binds control artifact to response",
            "PLAN replay is deterministic",
            "SESSION chain is append-only and verifiable",
        ],
    }

    return AdversarialReport(
        version="evez-hermes-adversarial-audit/v1",
        audit_sha256=_hash(canonical),
        verdict=verdict,
        findings=tuple(findings),
        invariants_checked=tuple(canonical["invariants_checked"]),
    )
