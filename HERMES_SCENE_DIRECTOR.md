# Hermes Scene Director

The Scene Director is the cinematic control layer above the performance compiler.

It answers:

What should this response feel like over time?

Instead of rendering one flat voice clip and one flat music bed, it creates a timed scene.

## Scene grammar

OPEN -> BUILD -> TURN -> ASCEND -> IMPACT -> AFTERMATH

Each section has:

- time range
- intensity
- vocal mode
- musical role
- transition cue

Cue types include:

- fade-in
- transition
- reality-glitch
- pressure
- breath
- impact
- release

## Example

python scripts/direct-hermes-scene.py "The evidence survived the system that was supposed to erase it." --duration 36 --energy 0.78 --surrealism 0.91 --seed 1337

The output is a deterministic scene JSON.

## Why this exists

The voice model should not be responsible for dramaturgy.

The music model should not be responsible for meaning.

Hermes decides the dramatic structure first.

Then each renderer receives a concrete plan.

## Mix contract

Speech remains primary.

Music ducks under speech.

Impact moments can temporarily change the ducking envelope.

Surrealism can increase stereo width and tail length.

Nothing in the Scene Director asserts that an audio file exists. It creates the control artifact that a renderer can execute.
