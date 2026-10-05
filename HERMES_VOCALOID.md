# Hermes Vocaloid Mode

This is the performance layer that turns Hermes into a local vocal instrument.

It is not the commercial Vocaloid product. It is a voice-performance architecture built from open/local components.

## Two modes

Performance-preserving mode:
Steven performs a guide, including singing, sustained notes, rasp, fry, breath, rap, or beatbox. RVC converts the guide's timbre into the trained Steven model while preserving the guide's timing and pitch trajectory. The current RVC CLI exposes pitch shifting, RMVPE F0 extraction, index rate and protection controls, and the project documents F0-aware training for singing. citeturn550500search0turn550500search9

Generated-performance mode:
lyrics -> melody/note map -> generic singing guide -> RVC -> Steven timbre -> expressive processing -> instrumental -> master

DiffSinger is an open singing-voice-synthesis project with MIDI-based singing workflows and an MIT-licensed codebase. citeturn550500search2turn338528search2

ACE-Step 1.5 can generate vocals and full songs locally and exposes BPM/key/scale control. Its current repository is MIT licensed. citeturn210887search0turn210887search6

## Expression vocabulary

Hermes explicitly tracks:
energy, breath, vibrato, rasp, grit, fry, attack, legato, sustain, cadence, articulation, beatbox.

These are control intentions, not guarantees. The actual acoustic result depends on the performance guide and model.

## Training data

Use the owner's own recordings:
normal speech, sustained vowels, chest voice, head/falsetto voice, sung phrases, breathy phrases, rasp/fry examples, rap diction, consonant-heavy syllables, and beatbox/percussive mouth sounds.

RVC's current documentation recommends roughly 10-50 minutes for a strong dataset and states that F0-aware training is important for singing. citeturn550500search4turn550500search3

Keep recordings and model weights private.

## Performance principle

The guide is the instrument.
RVC is the timbral body.
The expression processor is the character layer.
ACE-Step is the cinematic world around it.

That is how Hermes gets from cloned speech to something that can actually sing, rasp, rap and beatbox.
