---
name: voice-profile-extraction
description: Use when copy must match a proven voice.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [content, writing, voice, copy, brand-isolation, outreach]
    related_skills: [humanizer, hyderabadi-urdu-content, linkedin-content-engine, cold-email-tone-matrix, content-integrity-guardrail]
    source: affaan-m/ECC (MIT) skills/brand-voice -> rewritten for our brands and sources; see ~/ops/vendor/skills/affaan-m/brand-voice/PROVENANCE.md
---

# Voice Profile Extraction (source-derived, reusable)

Derive the writing voice from **real published material**, freeze it as a short reusable block, and
edit against it. The point is operational reuse, not literary criticism.

The mechanism came from ECC's `brand-voice`. Their default-voice fallback was dropped - we have
real corpora (our own posts, sent mail, client sites), so a profile is always derived, never
guessed.

## When to Use

- Writing on behalf of a brand or person where tone drift is the risk: LinkedIn posts and carousels,
  cold email, site copy, client one-pagers.
- A new lane starts (new client, new channel) and the voice is not yet written down anywhere.
- Someone says the copy "sounds like AI" or "sounds off" - that is the trigger to extract, not to
  re-write by feel.
- Adapting one proven voice across channels (X thread -> carousel -> email).

## Source priority (strongest real material first)

1. Recent original X posts/threads (`xurl`, original posts not reposts).
2. LinkedIn posts and carousels that actually performed.
3. Real outbound emails and messages that got real replies (`himalaya` Sent; exported chat logs).
4. Site copy, docs, changelogs of the brand itself (Sanad site, AVVS bilingual pages, AZ pages).

Never use platform exemplars, influencer templates, or another brand's copy as source material.
Brand isolation is a hard rule: Sanad, AVVS Triatek, Luxewave, and AZ Consultants each get their
**own** profile; a profile is never shared between them.

## Collection

- 5-20 representative samples; prefer recent unless the older material is explicitly canonical.
- Separate "public launch voice" from "private working voice" when the corpus splits (LinkedIn post
  voice vs WhatsApp reply voice) and keep both blocks.
- Record where each sample came from (URL/path + date) inside the profile - a profile with no
  citations cannot be re-derived when someone asks why the copy reads that way.

## What to extract (keep it to observable dimensions)

- Sentence length and rhythm; where the writer stops short.
- Compression vs explanation: does it assert or unpack?
- Capitalisation and punctuation norms (including the deliberate exceptions).
- Parenthetical use, dashes, dashes-as-asides.
- Question frequency and purpose (real question vs bait).
- How sharply claims are made; how hedges are expressed.
- Numbers, mechanisms, receipts: how often they appear and how they are formatted.
- How transitions and endings work (does it close with an ask, a line, or nothing?).
- What the author never does (the most useful section).

## Output contract - the VOICE PROFILE block

Produce one fenced block, short enough to paste into a session, e.g.:

```
VOICE PROFILE - <brand/person>  (derived from <n> samples, <date range>)
Sources: <url/path list, one per line>
Register:      <e.g. direct, concrete, unhurried>
Sentence:      <length + rhythm>
Compression:   <assert vs unpack, with an example>
Punctuation:   <norms + deliberate exceptions>
Questions:     <frequency + purpose>
Claims:        <how sharp, how hedged>
Receipts:      <numbers/mechanisms: how and how often>
Transitions:   <how sections and endings connect>
Never:         <verbatim list of banned moves>
Banned words:  <the specific list for this brand>
```

Store it with the brand's material (client dir or `~/brains`), date it, and cite it in the skill or
brain page that uses it. Re-derive when the corpus changes materially - a stale profile is worse
than none.

## Brand overlays that override the profile

- **Sanad (client-facing):** pure English, one-word brand, never the operator's name, AI-free
  wording, no emojis, no images in correspondence, diplomatic review language.
- **AVVS Triatek:** bilingual EN + AR, RTL-safe phrasing in the Arabic edition; lead-gen CTA.
- **Luxewave:** both links in posts; the Luxe Wave badge and voice-over in video.
- **Aamir's own peer content (LinkedIn/X):** Hyderabadi Roman Urdu register where it fits, per
  `hyderabadi-urdu-content`; neuromarketing hooks, value framing, urgency with honesty.
- **All client-facing work:** no imagery of people or living beings (with the documented
  exceptions), and every claim carries proof per `content-integrity-guardrail`.

## Hard bans (apply after drafting, and keep the list)

- Fake curiosity hooks, "not X, just Y" constructions, "no fluff", forced lowercase, em-dash
  pile-ups, "in today's fast-paced world", "unlock the power of", "game-changer".
- Generic AI closers: "Let me know if you have any questions", "I hope this email finds you well".
- Claiming results without a source, number, or receipt.
- Reusing another brand's voice, slogan, or number in this brand's output.

## Verification before shipping copy

1. Read the draft against the profile line by line; every "Never" item is a hard failure.
2. Compare one shipped sample side by side with the profile source - if the register moved, say so.
3. Run the humanizer pass for AI-isms, then `python3 ~/ops/verify/claim_integrity.py` on anything
   with a factual claim, and clear every HIGH finding.
4. Client-facing: no emojis, no named operator, no cross-brand links or numbers.
