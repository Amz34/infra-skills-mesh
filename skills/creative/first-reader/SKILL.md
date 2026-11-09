---
name: first-reader
description: "Use when checking whether a client-facing draft survives a skimming reader: fixation tokens, bold-variant headers, cost per screen, burstiness. Offline, stdlib-only copy QA."


license: Apache-2.0
compatibility: Python 3 stdlib only. Offline, no dependencies, no network.

metadata:
  hermes:
    tags: [copywriting, qa, linkedin, outreach, readability]
metadata:
  version: 1.0.0
  platforms: [linux, macos]
  author: Hermes + Aamir
---

# First Reader

## When to use

- Before a client-facing post, carousel, cold email or landing section goes out.
- When a draft "reads fine" to its author but you need the skimming-reader view.
- After a rewrite, to compare whether attention cost actually dropped.

This is the second reader the author cannot be. It answers one question: what does a
reader who gives ten seconds actually take away?

## When not to use

- Not a grammar or spelling checker.
- Not a fact checker and not a claim reviewer.
- No model is called, nothing is published, the draft is not modified.

## Run it

```bash
python3 scripts/skim.py <draft.md>              # scanner view
python3 scripts/signals.py <draft.md> --json    # measured signals
```

Both take a single file path and print to stdout.

## What each tool gives you

**skim.py - the scanner view.** Simulates the ten-second pass:

- word count, full-read time and screen count;
- the fixation tokens: which numbers, list markers and bold-variant headings the eye
  lands on first;
- every heading followed by its opening line only, the rest withheld.

Read the scanner view as a reader would: if the withheld middles do not tempt you to
continue, the draft has a skim problem, not a length problem.

**signals.py - the measured signals.**

| Signal | How to read it |
|---|---|
| `burstiness` | Sentence-length variation. Very low = flat monotone; healthy prose mixes short punches with longer lines |
| `sentence_len.max` | A sentence over ~45 words is a reading cost, not a style choice |
| `costly.numbers.per100w` | Numbers per 100 words. High density taxes a skimming reader |
| `costly.named_entities.per100w` | Named-entity density - too many proper nouns per screen and nothing is memorable |

## How to act on it

1. Run both tools on the draft as written. Do not edit while measuring.
2. Fix in this order: several dense paragraphs with no short line -> vary sentence length;
   high number density -> move figures to a table, one figure per claim in prose; headings
   that do not carry a claim -> rewrite the heading, not the paragraph under it.
3. Re-run. Compare screen count and burstiness. If attention cost did not drop, the
   rewrite was decoration.

## Pitfalls

- Do not over-tune for the metrics. Burstiness is a symptom, not a target; a draft written
  to score well reads like a machine wrote it - check the result with `humanizer` after.
- Word counts differ slightly between the two tools (markup and list markers are stripped
  differently). Use one tool per comparison, not both.
- Copy that follows a house format with faint/bold unicode headings will show those
  glyph variants as fixation tokens. That is expected, not a defect.

## Verification

```bash
# both tools must run against a real draft and print a stats line
python3 scripts/skim.py SKILL.md | head -3
python3 scripts/signals.py SKILL.md --json | head -5
```

## Origin

Adapted from `Shubhamsaboo/awesome-llm-apps` (`agent_skills/first-reader`, Apache-2.0).
The upstream skill drives a multi-reader simulated room through local subagents; this
adoption keeps only the two deterministic, offline pieces (`skim.py`, `signals.py`) and
drops the LLM-driven room, page renderer and per-reader interview scripts. Verified
against a real client draft on 2026-10-16.
