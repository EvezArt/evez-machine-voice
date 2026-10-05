# Hermes Operator Contract

Hermes is a response engine with an audio renderer.

It must decide what the response means before deciding how the response sounds.

## Resolution order

1. Determine semantic intent.
2. Determine emotional temperature.
3. Select performance mode.
4. Select a musical theme.
5. Retrieve personal musical fingerprints.
6. Generate a new score.
7. Render speech or performance.
8. Mix and master.
9. Emit provenance.

## Performance resolver

| Signal | Mode |
|---|---|
| ordinary answer | spoken |
| explanatory answer | cinematic |
| emotional reflection | sustain |
| lyric / chorus / melody | vocaloid |
| bars / rhyme / flow | rap |
| hype / rhythmic punctuation | beatbox |
| rage / grit / confrontation | rasp |
| uncanny / liminal | vocaloid + surreal |

## Musical resolver

The system modifies:

- tempo
- harmonic mode
- density
- texture
- rhythmic pressure
- stereo movement
- negative space
- perceived brightness
- arrangement size

It does not need to copy a song's melody to feel like part of the same musical universe.

## User performance mode

When an owner-recorded guide exists:

guide -> RVC -> expression processing -> score -> mix

This is preferred for unusual vocal technique because timing, pitch contour, breath, consonants, rasp, and beatbox articulation already exist in the performance.

## Generated performance mode

When no guide exists:

lyrics -> generated singing guide -> RVC -> expression -> score

ACE-Step 1.5 is the preferred current local score/guide backend because its documented API supports lyrics, BPM, key/scale, duration, reference audio, model selection, deterministic seeds, and asynchronous task results. citeturn846377view0turn333896view0

## Evidence law

A waveform exists only after the renderer actually produces it.

A model is only "trained" after the training run exists.

A musical match is only a descriptor match unless a reproducible source-audio transformation was actually performed.

A beautiful output is not evidence of the mechanism that produced it.

Each output gets a manifest containing:

- input hashes
- prompt-derived hash
- model/backend
- task identifier
- musical theme
- energy/surrealism
- fingerprint references
- output SHA-256
- rights state
