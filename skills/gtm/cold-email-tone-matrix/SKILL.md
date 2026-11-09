---
name: cold-email-tone-matrix
description: Use when choosing a cold email tone (6 tones, bilingual).
version: 1.0.0
---

# Cold Email Tone Matrix

Ported from Prospeda's GTM outreach library (MIT). Six repeatable voices for cold email, each with
its exact rules and a worked example. Pick the tone that fits the buyer, then adapt for AVVS
(bilingual EN+AR, corporate) or Sanad (pure English, service consult) — see Adaptation Notes.

## When to Use

- Choosing the voice for a first-touch cold email (or a follow-up) per prospect segment.
- A/B variants: same message, different tone, test reply rates.
- Matching tone to buyer: execs → Direct; complex sales → Consultative; differentiated offer →
  Challenger; SMB/startups → Casual; regulated/enterprise → Formal; owner-to-owner → Founder.

## The 6 Tones

### 1. Direct (No Fluff) — busy executives

```
Write a cold email to [PERSON], [TITLE] at [COMPANY].

Tone: Direct. No fluff. Respect their time.
Context:
- They [RELEVANT SIGNAL: raised / hired / launched / expanded]
- We help [TYPE OF COMPANY] with [PROBLEM]
- Desired outcome: [SPECIFIC RESULT]

Rules:
- Under 75 words
- No "hope this finds you well"
- No buzzwords
- Clear ask at the end
- Subject line under 5 words
```

Example subject: `Quick question` — open with the signal, one line of value, one clear ask.

### 2. Consultative (Question-Led) — complex sales

```
Write a cold email to [PERSON], [TITLE] at [COMPANY].

Tone: Consultative. Lead with a question. Genuine curiosity about their situation.
Context:
- Company info: [WHAT YOU KNOW]
- We help with: [PROBLEM AREA]
- Common challenge for their type: [PAIN POINT]

Rules:
- Start with an observation, then a question
- No pitch in the first email
- Goal is a conversation, not a sale
- Under 100 words
```

### 3. Challenger (Share an Insight) — differentiated products

```
Write a cold email to [PERSON], [TITLE] at [COMPANY].

Tone: Challenger. Share a contrarian insight that makes them think differently.
Context:
- Industry assumption to challenge: [COMMON BELIEF]
- Our contrarian view: [DIFFERENT PERSPECTIVE]
- Evidence or data point: [PROOF]

Rules:
- Lead with the insight, not with us
- Confident but not arrogant
- End with a soft question
- Under 100 words
```

AVVS example angle: "Your Triatek valves are not obsolete" — age ≠ failure; calibration, genuine
parts and expert hands determine reliability (proven pattern, see b2b-outreach-email).

### 4. Casual (Human, Conversational) — SMB/startup buyers

```
Write a cold email to [PERSON] at [COMPANY].

Tone: Casual. Like emailing a colleague. Conversational, no corporate speak.
Context:
- Why you're reaching out: [TRIGGER]
- What you might help with: [GENERAL AREA]
- Something specific about them: [PERSONALIZATION]

Rules:
- Write like you talk
- Lowercase subject is fine
- Short sentences
- No jargon
- Under 60 words
```

### 5. Formal (Corporate-Friendly) — enterprise / regulated industries

```
Write a cold email to [PERSON], [TITLE] at [COMPANY].

Tone: Formal and professional. Appropriate for enterprise/corporate environments.
Context:
- Company: [DETAILS]
- Your company: [WHO YOU ARE]
- Value prop: [WHAT YOU OFFER]

Rules:
- Professional greeting and sign-off
- Clear and structured
- Mention relevant credentials or clients
- Under 120 words
```

### 6. Founder-to-Founder (Peer Level) — owner-operated prospects

```
Write a cold email from a founder to another founder.

Tone: Peer-to-peer. No sales language. One builder talking to another.
Context:
- My company: [WHAT YOU'RE BUILDING]
- Their company: [WHAT THEY'RE BUILDING]
- Shared challenge: [COMMON PROBLEM]

Rules:
- Be real about what you're doing
- Reference shared experiences
- No pitch, just connection
- Ask for advice or input, not a meeting
- Under 80 words
```

## Adaptation Notes

**AVVS Triatek (B2B, FM/hospitals):** Formal or Direct for hospital/corporate buyers; Challenger
works for the "obsolete product" objection angle; Consultative for complex multi-stakeholder
accounts. Keep bilingual: EN body + one Arabic accent line per section. No emojis, no ALL-CAPS.

**Sanad (service business):** Direct or Consultative for business owners; Founder-to-Founder when
the prospect is an owner-operator. Pure English, AI-free copy, one-word brand, no images.

**Aamir's own outreach (founder persona):** Founder-to-Founder tone matches his style —
no sales speak, real about what he's building.

## Pitfalls

- Don't mix tones in one email — pick one voice and stay in it.
- Casual ≠ sloppy: still no spam words, no emojis in client-facing AVVS mail.
- Challenger requires a TRUE insight with evidence — a fake contrarian take reads as clickbait.
- Formal is for regulated/enterprise — using it on startups kills reply rates.

## Related

- `signal-based-outreach` — the trigger/hook content to pair with any tone.
- `b2b-outreach-email` — HTML build, spam safety, genuine-not-generic checklist.
- `follow-up-cadence` — tone-consistent follow-ups after the first email.
