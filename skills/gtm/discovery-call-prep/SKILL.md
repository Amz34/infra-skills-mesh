---
name: discovery-call-prep
description: Use when preparing discovery calls and questions.
version: 1.0.0
author: Aamir Zameer — Hermes
license: MIT (ported from Prospeda claude-gtm-skills)
metadata:
  hermes:
    tags: [gtm, sales, discovery, calls, spin]
    related_skills: [meddpicc-deal-qualification, follow-up-cadence, meeting-action-items]
---

# Discovery Call Prep

Ported from Prospeda's GTM library (MIT). Ask better questions, understand deeper, sell smarter —
SPIN and MEDDIC question generation, pre-call research briefs, call structure, post-call CRM
summary, and conversation openers that don't feel like sales.

## When to Use

- Before any AVVS/Triatek or Sanad discovery call (first call, deep discovery, demo prep).
- Generating questions when you're stuck or the call is in an unfamiliar industry.
- Turning raw call notes into a CRM-ready summary.
- Aamir's PM consulting intake calls — same structure, consulting lens.

## Question Generation

### SPIN Questions

```
Generate SPIN questions for selling [PRODUCT] to [PERSONA]:

Situation Questions (4): understand their current state
Problem Questions (4): uncover challenges and frustrations
Implication Questions (4): explore consequences of problems
Need-Payoff Questions (4): help them envision the solution

Make them specific to their industry: [INDUSTRY]
```

### MEDDIC Discovery

```
Generate discovery questions following MEDDIC:

Metrics: What they measure
Economic Buyer: Who approves budget
Decision Criteria: How they'll decide
Decision Process: Steps to purchase
Identify Pain: The real problem
Champion: Who will sell internally

Context:
- Product: [WHAT YOU SELL]
- Typical deal size: [AMOUNT]
- Buyer: [PERSONA]

Give me 2-3 questions for each category.
```

### Budget Without Asking "What's Your Budget?"

```
Generate 5 ways to discover budget for [PRODUCT/SERVICE] without asking "What's your budget?"

Context:
- Price range: [LOW to HIGH]
- Typical buyer: [PERSONA]
- Industry: [INDUSTRY]

Make questions natural and conversational.
```

Examples: "Are you looking for a point solution or something more comprehensive?"
"How does your team typically make investments like this? Is there a threshold where you need
VP approval?" "What are you spending on [current approach] today?"

### Timeline Discovery

```
Generate 5 questions to understand timeline and urgency for [PURCHASE].

I need to know:
- When they need a solution
- What's driving the timeline
- What happens if they do nothing
- Any hard deadlines (contracts, events)

Make them natural, not salesy.
```

## Call Structure

### The Perfect Discovery Call (30 min)

```
Create a discovery call structure for a 30-minute call with [PERSONA].

Product: [WHAT YOU SELL]
Goals: [WHAT I NEED TO LEARN]

Include:
- Opening (build rapport, set agenda) — 3 min
- Situation questions — 5 min
- Problem exploration — 10 min
- Impact/implication questions — 5 min
- Vision of solution — 5 min
- Next steps — 2 min

For each section: transition language, 2-3 key questions, what to listen for.
```

### Deep Problem Discovery (surface → root cause)

```
I need to deeply understand [PROBLEM] that [PERSONA] faces.

Give me a question chain that goes from surface to root cause:
1. Surface question (what's happening)
2. Follow-up (get specifics)
3. Impact question (what does this cost)
4. Root cause (why is this happening)
5. Vision (what would solving this look like)

Make it feel like a conversation, not an interview.
```

### Competitive Discovery (non-defensive)

```
Generate questions to discover competitive situation without being defensive:
1. What else they're evaluating
2. What they like about alternatives
3. What concerns them about alternatives
4. How they'll compare options
5. Their evaluation criteria

Context: [YOUR PRODUCT vs. likely competitors]
```

## By Persona

- **Executives:** strategic impact, business outcomes, fewer & better questions, board-level
  concerns. Respect time.
- **Technical buyers:** technical environment, integration concerns, implementation
  requirements, security/compliance.
- **End users:** daily workflows, current frustrations, what good looks like, what they've tried.

## Pre-Call Research Brief

```
I have a discovery call with [PERSON], [TITLE] at [COMPANY].

Create a prep brief:
1. ABOUT THEM — role scope, recent LinkedIn activity, career background relevant to my pitch
2. ABOUT THE COMPANY — what they do, how they make money, recent news, likely pain points
3. HYPOTHESES TO TEST — 3 things I think might be true + questions to validate each
4. QUESTIONS TO ASK — opening question, 5 core discovery questions, closing question
5. OBJECTIONS TO PREPARE FOR — what they might push back on + how to handle each

My product: [WHAT YOU SELL]
```

## Agenda Email (before the call)

```
Write an email to send before my discovery call with [PERSON].

Include:
- Confirm time/logistics
- Set expectations for the call
- Ask them to think about something specific
- Keep it brief

Tone: [SELECT]
Call is: [FIRST CALL / FOLLOW-UP / etc.]
```

## Post-Call: CRM Summary

```
Summarize this discovery call for my CRM:

[PASTE NOTES OR TRANSCRIPT]

Format:
1. Key pain points
2. Current situation and stack
3. Decision process and timeline
4. Budget indicators
5. Competition mentioned
6. Champion vs. skeptics
7. Next steps agreed
8. Risk factors
9. Recommended approach
```

## Discovery → Demo Bridge

```
Based on this discovery call, create a custom demo agenda:

Discovery findings:
- Pain points: [LIST]
- Priorities: [WHAT MATTERS MOST]
- Decision criteria: [HOW THEY'LL EVALUATE]
- Stakeholders: [WHO ELSE IS INVOLVED]

Create:
1. Demo opening that references their specific pain
2. 3 features to focus on (matched to their needs)
3. 2 features to skip (not relevant)
4. Questions to ask during demo
5. Closing approach
```

## Openers That Don't Feel Like Sales

```
Give me 10 ways to start a discovery call that don't sound like "So tell me about your biggest challenges."

Context:
- Persona: [WHO]
- Industry: [WHAT]
- Product: [WHAT I SELL]
```

Examples: "I did some homework on [Company] before the call. Mind if I share what I found and you
can tell me where I'm wrong?" / "Before we dive in — what made you take this call?" / "I saw
you've been at [Company] for [X years]. What's changed the most in that time?"

### When They're Guarded

```
The prospect seems guarded and is giving short answers.

Give me questions that:
- Are low-threat
- Build trust
- Get them talking
- Don't feel like qualification

Their role: [PERSONA]
They seem concerned about: [YOUR GUESS]
```

## Adaptation Notes

**AVVS Triatek:** discovery calls are often bilingual — prepare both EN and AR versions of the
core questions; engineering contacts need technical depth (calibration history, valve models,
BMS integration), procurement needs paper process. Post-call summary goes to the CRM as the
deal record — feed it straight into meddpicc-deal-qualification.

**Sanad:** discovery often happens on WhatsApp/Telegram chat, not a call — the SPIN chain works
as a message sequence. Keep questions short, one per message, pure English, AI-free.

**Aamir PM consulting:** use SPIN for project health (schedule variance, budget burn, stakeholder
pressure), MEDDIC for engagement qualification. Pre-call brief applies the same — company
research first, always.

## Pitfalls

- Don't interrogate — SPIN is a conversation; skip questions that were already answered.
- Never ask "What's your budget?" cold — use the 5 indirect patterns.
- Guarded prospect = trust problem, not a question problem — slow down, low-threat questions.
- Send the agenda email 24h before — it raises show-up rate and sets seriousness.

## Related

- `meddpicc-deal-qualification` — score the deal after discovery.
- `follow-up-cadence` — post-discovery call follow-up templates.
- `meeting-action-items` — decisions/owners/tickets from the call.
