# Hermes Audio Sidecar

This turns Hermes responses into a synthetic Steven voice plus an original cinematic response score.

## Models

F5-TTS provides reference-conditioned synthesis from a short voice sample. Its upstream documentation recommends keeping the reference under roughly 12 seconds. The code is MIT, while pretrained weights are CC-BY-NC because of the Emilia training data. Re-check the exact model license before commercial distribution. citeturn627053search0turn627053search1

ACE-Step 1.5 is an open-source local music generation system and documents consumer-hardware/local deployment. Its repository is MIT licensed. citeturn627053search5turn627053search7

## Voice setup

Record a clean sample of your own voice and store it only on the machine running Hermes:

`data/hermes/voices/steven/reference.wav`

Use a quiet room, one speaker, dry audio, natural speaking, and about 8-12 seconds. Do not commit this recording to GitHub.

## Start

Install the package with the Hermes optional dependencies, install F5-TTS and ACE-Step locally, then run:

`python -m evez_machine_voice.hermes_audio.server`

The sidecar listens on port `9113`.

## Hermes request

POST `/v1/hermes/respond`:

```json
{"response_text":"The contradiction survived the test.","voice":"steven","voice_style":"cinematic","music":true,"theme":"surreal","duration_seconds":24,"energy":0.66,"surrealism":0.92}
```

The response returns paths for the synthesized voice, generated score, and final mix.

## Surreal remix principle

The default system does not copy the songs you listen to. Instead, it can be extended with a personal music-profile extractor that maps your permitted reference library into descriptors such as BPM, key/mode, energy, spectral centroid, rhythmic density, instrumentation and texture. Hermes then generates a new composition matching those descriptors.

Source-audio remix mode is intentionally gated by `rights_asserted=true`. Use that only with audio you own or are authorized to transform.
