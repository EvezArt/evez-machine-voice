from __future__ import annotations
import re
from dataclasses import dataclass

@dataclass(frozen=True)
class Theme:
    name: str
    bpm: int
    mode: str
    texture: str
    arrangement: str

THEMES = {
    "investigation": Theme("investigation", 88, "minor", "tape hiss, granular shadows, muted analog pulse", "sparse negative space"),
    "discovery": Theme("discovery", 118, "dorian", "glass harmonics, arpeggiated pulse, widening stereo field", "gradual lift"),
    "danger": Theme("danger", 142, "phrygian", "sub pressure, broken percussion, metallic transients", "dense escalating layers"),
    "technical": Theme("technical", 126, "minor", "sequencer ticks, FM plucks, restrained sub bass", "precise modular repetition"),
    "reflection": Theme("reflection", 72, "aeolian", "felt piano, bowed texture, soft tape movement", "slow breathing space"),
    "surreal": Theme("surreal", 101, "harmonic minor", "detuned bells, reverse tails, granular shadows", "asymmetric phrases and sudden negative space"),
}

KEYWORDS = {
    "investigation": {"evidence","records","foia","investigate","source","proof","forensics","claim"},
    "discovery": {"discover","found","new","breakthrough","learn","research","pattern"},
    "danger": {"danger","attack","breach","urgent","threat","risk","failure","warning"},
    "technical": {"code","system","architecture","deploy","runtime","api","database","build","engine"},
    "reflection": {"remember","memory","meaning","reflect","history","loss","past"},
    "surreal": {"surreal","dream","strange","impossible","liminal","alien","uncanny","reality"},
}

def select_theme(text: str, explicit: str | None = None) -> Theme:
    if explicit and explicit in THEMES:
        return THEMES[explicit]
    tokens = set(re.findall(r"[a-z0-9']+", text.lower()))
    scores = {name: len(tokens & terms) for name, terms in KEYWORDS.items()}
    winner = max(scores, key=scores.get)
    return THEMES[winner] if scores[winner] else THEMES["surreal"]

def musical_prompt(theme: Theme, text: str, energy: float, surrealism: float) -> str:
    return (
        f"cinematic instrumental score, {theme.name} atmosphere, {theme.bpm} BPM, {theme.mode}; "
        f"{theme.texture}; {theme.arrangement}; energy {energy:.2f}; surrealism {surrealism:.2f}; "
        f"semantic motifs derived from this spoken response: {text[:1400]}; "
        "original composition, no quotation of existing melodies, no recognizable sampled song material, instrumental"
    )
