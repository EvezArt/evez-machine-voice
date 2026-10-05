# Hermes Performance Conductor

The Performance Conductor is the continuity layer above the Scene Director.

The Scene Director answers:

What should this individual response feel like over time?

The Conductor answers:

How should the soundtrack remember what just happened?

## State

Each session carries a deterministic state containing:

- semantic theme
- BPM
- key and scale
- tension
- density
- brightness
- surrealism
- current vocal mode
- cumulative scene time
- motif identity and interval pattern
- previous state hash

A new turn inherits the previous harmonic center and motif lineage instead of starting from an unrelated random score.

## Semantic event grammar

Hermes extracts bounded semantic events from each response:

- REVEAL
- CONTRADICTION
- DANGER
- HUMOR
- QUESTION
- REFLECTION
- TECHNICAL
- RESOLUTION
- UNCANNY

Events alter musical state rather than directly generating audio. This keeps meaning, control, and rendering separate.

## Motif continuity

Each turn receives a four-step interval motif.

The first turn creates a root motif from the source hash.

Later turns inherit that motif and deterministically mutate one interval. The result is variation with lineage, not unrelated randomness.

The motif is a control artifact. It does not claim that an audible motif exists until a renderer consumes the plan.

## Session ledger

Each committed turn produces:

- conductor state JSON
- scene JSON
- performance plan JSON
- turn summary JSON
- append-only session-ledger.jsonl
- session-manifest.json

The ledger hashes each record to its predecessor.

GET /v1/hermes/session/verify/{session_id} replays the chain and reports any break.

## Conversation album

POST /v1/hermes/session/export creates:

- album JSON
- album manifest
- ZIP bundle

The album is marked control_only when no actual audio files have been produced.

That distinction is intentional.

PLAN is not WAVEFORM.

PRODUCED is not TRAINED.

DESCRIPTOR MATCH is not SOURCE TRANSFORMATION.

## CLI

Advance a session:

python scripts/conduct-hermes-session.py "We found the contradiction." --session-id steven-001

Export it:

python scripts/export-hermes-album.py data/hermes/sessions/steven-001

## Renderer boundary

The Conductor can hand its scene and performance plan to RVC, F5-TTS, ACE-Step, FFmpeg, or another local renderer.

No control artifact asserts that rendering occurred.

When rendering actually happens, the resulting file should enter the audio artifact state machine as PRODUCED with its SHA-256 and provenance manifest.
