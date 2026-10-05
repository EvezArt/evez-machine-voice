# Hermes Adversarial Truth Gate

The Adversarial Truth Gate exists for one reason:

Make the system fail before a false artifact becomes a fact.

It treats every output as an adversarial claim against reality.

## Core attacks

### Replay attack

The declared response, theme, BPM, key, scale, performance kind, and seed are used to recompile the performance plan.

If the resulting SHA-256 differs from the declared plan hash, the plan fails.

### Source-binding attack

The response text is hashed independently.

If the plan source hash does not equal the response hash, the plan fails.

### Waveform-existence attack

A PRODUCED audio artifact must point to an actual file.

A nonexistent path is a critical failure.

### Waveform-integrity attack

A PRODUCED artifact must carry the SHA-256 of the actual file.

Any mismatch is a critical failure.

### State-separation attack

PLANNED and RENDERING artifacts are forbidden from carrying a produced waveform claim.

### Provenance attack

A produced audio artifact should carry a readable provenance manifest. Missing provenance is reported as UNKNOWN rather than silently converted into PASS.

### Session-chain attack

The session ledger must verify every parent link and every record hash.

Tampering, deletion, reordering, or alteration becomes visible.

## Verdicts

PASS means the checked invariants survived.

FAIL means a critical invariant was violated.

UNKNOWN means the system cannot establish the claim from available evidence.

UNKNOWN is not converted to PASS because the output looks good.

## HTTP endpoint

POST /v1/hermes/audit

Example:

{
  "response_text": "The system shipped the fix.",
  "plan": {
    "plan_sha256": "...",
    "source_sha256": "...",
    "theme": "technical",
    "bpm": 126,
    "key": "A",
    "scale": "minor",
    "performance_kind": "cinematic",
    "seed": 123
  },
  "audio_artifact": {
    "state": "PRODUCED",
    "path": "/path/to/output.wav",
    "sha256": "...",
    "manifest": "/path/to/output.wav.manifest.json"
  },
  "session_verification": {
    "ok": true
  }
}

The response includes an audit SHA-256, verdict, findings, and the invariants examined.

## Operator law

A plan is not a waveform.

A waveform is not a trained model.

A matching descriptor is not a copied source.

A provenance record is not proof of truth by itself.

The gate does not decide whether the work is beautiful.

It decides whether the system is allowed to pretend that something happened.

That is the difference between a renderer and an evidence-aware renderer.
