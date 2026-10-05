# Hermes Music Memory

Hermes can build a private index of your own listening library.

The index stores musical descriptors, not copies of the tracks:

- SHA-256
- duration
- BPM
- estimated key/mode
- loudness
- spectral centroid
- spectral bandwidth
- zero-crossing rate
- pulse density

That creates a reusable musical fingerprint.

## Build it

Install the audio extras:

\`\`\`bash
pip install -e '.[audio]'
\`\`\`

Then:

\`\`\`bash
python scripts/index-music-library.py ~/Music data/hermes/music-memory.json
\`\`\`

The JSON index is intentionally metadata-only.

## How Hermes uses it

A response gets a semantic performance profile first.

Example:

- investigation -> lower BPM, negative-space arrangement
- technical -> sequenced precision
- dramatic -> long sustain and slower harmonic movement
- surreal -> harmonic instability and texture
- punchline -> rap cadence
- hype -> beatbox/percussive attack

Hermes then retrieves a few nearby musical fingerprints.

The fingerprints are converted into descriptors for a new ACE-Step generation.

The original songs are not supplied as source audio in this default mode.

ACE-Step 1.5 currently supports explicit BPM/key/scale controls, audio understanding, reference audio and multiple audio-generation/editing modes. citeturn835746search1turn835746search3

## Why this matters

Your listening history becomes a latent style vocabulary:

\`response -> emotion -> performance -> musical fingerprint -> new score\`

So a response can feel like it belongs to the same personal musical universe without simply reproducing a song.

For tracks you own or are authorized to transform, a separate source-audio path can be enabled explicitly. Keep the default as fingerprint-only.
