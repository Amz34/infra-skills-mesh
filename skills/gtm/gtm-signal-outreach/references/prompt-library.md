# GTM Prompt Library — 15 prompts, 4 stages

All 15 prompt texts, unabridged, re-typed on **2026-09-30** from the public Pancake "GTM Claude
Prompt Pack" page (`https://atlasgtm.ai/l/v3rt46q`), reached from a LinkedIn comment-gate DM.
Forensics of that funnel: `~/brains/ops/ingestion/2026-09-30-pancake-gtm-brain-funnel.md`.

**Edits made when porting:** the source appended a `RUN IT IN PANCAKE` upsell paragraph (with a
signup link) to every prompt's output — removed. Filenames, page furniture and images removed.
Prompt logic, rules and checks are unchanged.

**How to run:** one stage at a time, replacing every `[BRACKETED]` input with real data. Each
stage's output is the next prompt's input. Never let an agent send anything — this library is
draft-only (see `SKILL.md`, hard rule 1).

---


## Stage 01 — DEFINE

*Decide who you are going after and what proves it.*

### 01 · DEFINE MY ICP

**What it does.** Turns what you already know about your best customers into a written, testable ICP.

**When to use it.** Before building any list, or when your current list keeps producing bad meetings.

**Input.**
- Your offer in 3-5 lines
- 3-8 best current customers
- 2-3 customers who churned or never activated

**Prompt**

```text
You are helping me define a testable ICP for outbound.

MY OFFER:
[OFFER]

BEST CUSTOMERS (company, size, industry, what they bought it for):
[BEST_CUSTOMERS]

BAD FITS (company, why it did not work):
[BAD_FITS]

Produce:
1. ICP STATEMENT — one paragraph, specific enough to disqualify.
2. FIRM ATTRIBUTES — industry, size band, geography, maturity, tech or ops context.
3. SITUATIONAL ATTRIBUTES — what must be TRUE right now for this to be urgent.
4. DISQUALIFIERS — 5 reasons to skip an account.
5. OPEN QUESTIONS — what you would need from me to sharpen this.

Rules:
- Separate FACTS (stated in the input) from INFERENCE (your reasoning). Label each line.
- Do not invent companies, people, numbers, dates or quotes. If something is missing, list it under MISSING CONTEXT.
- Keep reasoning to one short line per conclusion.
- Return structured output using the exact sections requested.
```

**Expected output.**
- A one-paragraph ICP you can paste into every later prompt
- Hard disqualifiers
- A list of what is still unknown

**Check before using.**
Read the disqualifiers first. If none of them would remove accounts from your current list, the ICP is still too broad.

---

### 02 · FIND MY BUYING SIGNALS

**What it does.** Converts your ICP into observable signals you can actually look for.

**When to use it.** Right after the ICP prompt, once per quarter.

**Input.**
- Your ICP statement
- Why your last 5 deals started

**Prompt**

```text
Here is my ICP:
[ICP]

Here is why my last deals actually started:
[TRIGGERS]

Identify buying signals that indicate an account is entering the window where my offer matters.

For each signal give:
- SIGNAL — what is observable
- WHERE IT IS VISIBLE — the type of public or first-party source
- STRENGTH — strong / medium / weak, with one line of reasoning
- DECAY — how long it stays relevant
- WHAT IT DOES NOT PROVE

Rank the signals and mark the 3 worth monitoring first.

Rules:
- Separate FACTS (stated in the input) from INFERENCE (your reasoning). Label each line.
- Do not invent companies, people, numbers, dates or quotes. If something is missing, list it under MISSING CONTEXT.
- Keep reasoning to one short line per conclusion.
- Return structured output using the exact sections requested.
```

**Expected output.**
- A ranked signal list
- Where each signal is observable
- Explicit limits of each signal

**Check before using.**
Drop any signal you cannot realistically observe every week. An unobservable signal is a wish.

---

### 03 · TURN MY OFFER INTO A PROSPECTING HYPOTHESIS

**What it does.** Writes the falsifiable bet behind your campaign so you can test it instead of guessing.

**When to use it.** Before launching a new segment or a new message angle.

**Input.**
- ICP
- Chosen signal
- Offer

**Prompt**

```text
ICP: [ICP]
SIGNAL I AM TARGETING: [SIGNAL]
OFFER: [OFFER]

Write my prospecting hypothesis in this format:

HYPOTHESIS: Companies that [situation] struggle with [problem], which shows up as [observable evidence]. My offer matters to them because [reason].

Then give:
- WHAT WOULD FALSIFY IT — 3 observations that would prove me wrong
- THE MINIMUM TEST — sample size and time window to get a readable signal
- SUCCESS THRESHOLD — what reply behaviour would count as validation
- RISKS — where this hypothesis is most likely to be wrong

Rules:
- Separate FACTS (stated in the input) from INFERENCE (your reasoning). Label each line.
- Do not invent companies, people, numbers, dates or quotes. If something is missing, list it under MISSING CONTEXT.
- Keep reasoning to one short line per conclusion.
- Return structured output using the exact sections requested.
```

**Expected output.**
- A single written hypothesis
- Falsification criteria
- A small, readable test plan

**Check before using.**
If nothing in the falsification list could ever happen, the hypothesis is not a hypothesis.


---


## Stage 02 — RESEARCH

*Get real context on the account before you write.*

### 04 · RESEARCH THIS ACCOUNT

**What it does.** Builds a structured account brief instead of a pile of tabs.

**When to use it.** Before writing anything to a named account.

**Input.**
- ICP
- Account name and website copy, notes, job posts or news you paste in

**Prompt**

```text
MY ICP: [ICP]
ACCOUNT: [ACCOUNT_NAME]
SOURCE MATERIAL I AM GIVING YOU:
[PASTE RAW MATERIAL]

Build an account brief:
1. WHAT THEY DO — in plain language, 3 lines max
2. WHO THEY SELL TO
3. CURRENT PRIORITIES — evidence-backed only
4. ICP FIT — where they match and where they do not
5. FACTS vs INFERENCE — two clearly separated lists
6. MISSING CONTEXT — what I should find before reaching out

Use only the material above. Do not use general assumptions about the industry as if they were facts about this company.

Rules:
- Separate FACTS (stated in the input) from INFERENCE (your reasoning). Label each line.
- Do not invent companies, people, numbers, dates or quotes. If something is missing, list it under MISSING CONTEXT.
- Keep reasoning to one short line per conclusion.
- Return structured output using the exact sections requested.
```

**Expected output.**
- A short account brief
- A clean fact/inference split
- A list of research gaps

**Check before using.**
Anything in the FACTS list must be traceable to the material you pasted. Move the rest to inference.

---

### 05 · FIND THE BUSINESS TRIGGER

**What it does.** Identifies the event that makes now the right moment, or says there is not one.

**When to use it.** After the account brief, before deciding to reach out.

**Input.**
- Account brief
- Recent public material about the account

**Prompt**

```text
ACCOUNT BRIEF:
[BRIEF]

RECENT MATERIAL:
[NEWS / JOB POSTS / CHANGES]

Identify triggers that make my offer timely.

For each:
- TRIGGER
- EVIDENCE — quote or reference the specific line in my material
- WHY IT CREATES URGENCY
- CONFIDENCE — high / medium / low
- SHELF LIFE

Then answer directly: IS THERE A REAL TRIGGER RIGHT NOW? YES / NO / NOT ENOUGH EVIDENCE.

If NO, say so plainly and tell me what to monitor instead.

Rules:
- Separate FACTS (stated in the input) from INFERENCE (your reasoning). Label each line.
- Do not invent companies, people, numbers, dates or quotes. If something is missing, list it under MISSING CONTEXT.
- Keep reasoning to one short line per conclusion.
- Return structured output using the exact sections requested.
```

**Expected output.**
- Evidence-backed triggers
- A clear yes/no on timing
- A monitoring instruction when there is no trigger

**Check before using.**
A trigger without a quoted piece of evidence is a guess. Treat it as one.

---

### 06 · FIND THE STRONGEST PERSONALIZATION ANGLE

**What it does.** Picks the one angle worth using, and kills the fake personalization.

**When to use it.** Right before writing the first message.

**Input.**
- Account brief
- Trigger analysis
- Offer

**Prompt**

```text
BRIEF: [BRIEF]
TRIGGER: [TRIGGER]
OFFER: [OFFER]

Propose 3 personalization angles. For each:
- ANGLE — one sentence
- EVIDENCE IT RESTS ON
- WHY THIS PERSON WOULD CARE
- HOW EASILY A COMPETITOR COULD SAY THE SAME THING

Then pick ONE and explain the choice in two lines.
Finally, list angles I should NOT use because they are generic, flattering or unverifiable.

Rules:
- Separate FACTS (stated in the input) from INFERENCE (your reasoning). Label each line.
- Do not invent companies, people, numbers, dates or quotes. If something is missing, list it under MISSING CONTEXT.
- Keep reasoning to one short line per conclusion.
- Return structured output using the exact sections requested.
```

**Expected output.**
- Three ranked angles
- One recommended angle
- A do-not-use list

**Check before using.**
If a competitor could send the same line to 200 companies, it is not personalization.

---

### 07 · FIND THE RIGHT PERSON TO CONTACT

**What it does.** Maps the likely roles involved and who should receive the first message.

**When to use it.** When the account is qualified but you do not know where to enter.

**Input.**
- Account brief
- Offer
- What you know about their org structure

**Prompt**

```text
ACCOUNT: [BRIEF]
OFFER: [OFFER]
WHAT I KNOW ABOUT THEIR ORG:
[ORG NOTES]

Map the buying context:
- LIKELY OWNER OF THE PROBLEM — role, not a name
- LIKELY ECONOMIC BUYER
- LIKELY BLOCKER and their objection
- BEST FIRST CONTACT — and why entering there beats the alternatives
- WHAT CHANGES IF I ENTER TOO HIGH OR TOO LOW

Do not invent names, titles or headcount. Where a role is uncertain, say so and tell me how to verify it.

Rules:
- Separate FACTS (stated in the input) from INFERENCE (your reasoning). Label each line.
- Do not invent companies, people, numbers, dates or quotes. If something is missing, list it under MISSING CONTEXT.
- Keep reasoning to one short line per conclusion.
- Return structured output using the exact sections requested.
```

**Expected output.**
- A role map
- A recommended entry point
- Verification steps

**Check before using.**
Never let the model produce a person's name. Names come from your data, not from inference.


---


## Stage 03 — OUTREACH

*Write and critique the messages, then the sequence.*

### 08 · SCORE THIS PROSPECT

**What it does.** Applies one consistent scoring rubric so accounts are comparable.

**When to use it.** Before spending writing time on an account.

**Input.**
- ICP
- Account brief
- Trigger analysis

**Prompt**

```text
ICP: [ICP]
ACCOUNT BRIEF: [BRIEF]
TRIGGER: [TRIGGER]

Score the account 0-100 using this rubric:
- ICP FIT (0-40)
- SIGNAL STRENGTH (0-30)
- TIMING (0-20)
- REACHABILITY (0-10)

Return:
- SCORE PER CRITERION with one line of justification each
- TOTAL
- VERDICT — pursue now / monitor / skip
- CONFIDENCE and what would most change the score
- MISSING CONTEXT

Be strict. A missing input lowers the score instead of being assumed positive.

Rules:
- Separate FACTS (stated in the input) from INFERENCE (your reasoning). Label each line.
- Do not invent companies, people, numbers, dates or quotes. If something is missing, list it under MISSING CONTEXT.
- Keep reasoning to one short line per conclusion.
- Return structured output using the exact sections requested.
```

**Expected output.**
- A scored breakdown
- A pursue / monitor / skip verdict
- The one input that would change the score

**Check before using.**
Score two accounts you already know well first. If the rubric disagrees with your judgement, fix the weights.

---

### 09 · WRITE THE FIRST MESSAGE

**What it does.** Drafts a short first-touch grounded in your research, not in adjectives.

**When to use it.** Only after the account brief, trigger and angle exist.

**Input.**
- Chosen angle
- Offer
- Tone
- Channel

**Prompt**

```text
ANGLE: [ANGLE]
OFFER: [OFFER]
TONE: [TONE]
CHANNEL: [EMAIL / LINKEDIN]

Write 2 versions of a first message.

Constraints:
- Under 90 words
- Opening line must reference the specific evidence, not the company's greatness
- One idea only
- One low-friction ask
- No "hope this finds you well", no flattery, no buzzwords, no fake urgency
- Do not claim results, customers or numbers I did not give you

After each version, list the assumptions it makes about the reader.

Rules:
- Separate FACTS (stated in the input) from INFERENCE (your reasoning). Label each line.
- Do not invent companies, people, numbers, dates or quotes. If something is missing, list it under MISSING CONTEXT.
- Keep reasoning to one short line per conclusion.
- Return structured output using the exact sections requested.
```

**Expected output.**
- Two short drafts
- The assumptions behind each
- No invented proof points

**Check before using.**
Delete any sentence that would still be true if you swapped in a different company.

---

### 10 · CRITIQUE THIS MESSAGE

**What it does.** Runs a hostile read of your draft before a prospect does.

**When to use it.** On every message before it goes out, including ones you wrote yourself.

**Input.**
- Your draft
- ICP
- The recipient's likely role

**Prompt**

```text
DRAFT:
[DRAFT]

ICP: [ICP]
RECIPIENT ROLE: [ROLE]

Critique this as a skeptical recipient who receives 30 of these a week.

Return:
- FIRST IMPRESSION IN 3 SECONDS
- WHY THEY WOULD DELETE IT — ranked
- UNSUPPORTED CLAIMS — quote them
- GENERIC LINES — quote them
- CLARITY OF THE ASK
- REWRITE — one tightened version, same facts, no new claims

Do not soften the critique.

Rules:
- Separate FACTS (stated in the input) from INFERENCE (your reasoning). Label each line.
- Do not invent companies, people, numbers, dates or quotes. If something is missing, list it under MISSING CONTEXT.
- Keep reasoning to one short line per conclusion.
- Return structured output using the exact sections requested.
```

**Expected output.**
- A ranked list of weaknesses
- Quoted generic or unsupported lines
- One tightened rewrite

**Check before using.**
If the rewrite introduces a claim you cannot back, remove it before sending.

---

### 11 · CREATE THE FOLLOW-UP

**What it does.** Writes follow-ups that add information instead of repeating the ask.

**When to use it.** 3-6 days after the first message with no reply.

**Input.**
- First message
- Account brief
- Any new signal since then

**Prompt**

```text
FIRST MESSAGE SENT:
[MESSAGE]

ACCOUNT BRIEF: [BRIEF]
NEW SINCE THEN: [NEW SIGNAL OR "NOTHING"]

Write 2 follow-ups.

Rules:
- Each must add something new: an angle, a proof point I have given you, or a narrower question
- Never say "just following up", "bumping this" or "circling back"
- Under 60 words
- Different ask than the first message
- If nothing new exists, make the follow-up narrower rather than louder

Explain in one line what each follow-up adds.

Rules:
- Separate FACTS (stated in the input) from INFERENCE (your reasoning). Label each line.
- Do not invent companies, people, numbers, dates or quotes. If something is missing, list it under MISSING CONTEXT.
- Keep reasoning to one short line per conclusion.
- Return structured output using the exact sections requested.
```

**Expected output.**
- Two follow-ups that add information
- The rationale for each
- No filler openers

**Check before using.**
If you cannot say what the follow-up adds, do not send it.

---

### 12 · BUILD THE SEQUENCE

**What it does.** Assembles a full multi-touch sequence with a reason for every touch.

**When to use it.** Once a single message and follow-up have proven readable.

**Input.**
- ICP
- Angle
- Offer
- Channels available
- Time window

**Prompt**

```text
ICP: [ICP]
ANGLE: [ANGLE]
OFFER: [OFFER]
CHANNELS: [CHANNELS]
WINDOW: [DAYS]

Design a sequence of 4-6 touches.

For each touch:
- DAY
- CHANNEL
- PURPOSE — what this touch is for
- NEW INFORMATION IT ADDS
- MESSAGE — full draft
- EXIT CONDITION — what makes me stop

Then give:
- WHAT TO MEASURE per touch
- WHERE THE SEQUENCE IS MOST LIKELY TO FEEL AUTOMATED

Rules:
- Separate FACTS (stated in the input) from INFERENCE (your reasoning). Label each line.
- Do not invent companies, people, numbers, dates or quotes. If something is missing, list it under MISSING CONTEXT.
- Keep reasoning to one short line per conclusion.
- Return structured output using the exact sections requested.
```

**Expected output.**
- A day-by-day sequence
- A purpose per touch
- Exit conditions and metrics

**Check before using.**
Remove any touch whose only purpose is 'stay top of mind'.


---


## Stage 04 — LEARN

*Turn replies into the next campaign.*

### 13 · ANALYZE MY REPLIES

**What it does.** Reads your actual replies and tells you what the market is objecting to.

**When to use it.** After 20-50 sends, or at the end of each campaign.

**Input.**
- Replies pasted in, anonymized
- The message that produced them

**Prompt**

```text
MESSAGE SENT:
[MESSAGE]

REPLIES (anonymized):
[REPLIES]

Analyze:
- REPLY CATEGORIES with counts
- OBJECTION THEMES — ranked, with a quoted example each
- WHAT THE POSITIVE REPLIES HAVE IN COMMON
- WHAT THE NEGATIVE REPLIES HAVE IN COMMON
- WHAT THIS SUGGESTS ABOUT MY ICP OR TIMING
- WHAT THE SAMPLE IS TOO SMALL TO CONCLUDE

Do not generalize beyond the replies I gave you.

Rules:
- Separate FACTS (stated in the input) from INFERENCE (your reasoning). Label each line.
- Do not invent companies, people, numbers, dates or quotes. If something is missing, list it under MISSING CONTEXT.
- Keep reasoning to one short line per conclusion.
- Return structured output using the exact sections requested.
```

**Expected output.**
- Categorized replies
- Ranked objections with quotes
- An explicit statement of what the data cannot support

**Check before using.**
Anonymize before pasting. Names and company identifiers are not needed for the analysis.

---

### 14 · FIND PATTERNS IN WINNING MESSAGES

**What it does.** Extracts the reusable structure behind the messages that worked.

**When to use it.** Once you have 5+ messages that produced real conversations.

**Input.**
- Messages that got positive replies
- Messages that got nothing

**Prompt**

```text
MESSAGES THAT WORKED:
[WINNERS]

MESSAGES THAT DID NOT:
[LOSERS]

Compare them and return:
- STRUCTURAL DIFFERENCES — opening, length, ask, specificity
- ANGLE DIFFERENCES
- WHAT IS CORRELATION RATHER THAN CAUSE — be explicit
- A REUSABLE TEMPLATE derived only from the winners, with variables marked [LIKE_THIS]
- TWO THINGS TO TEST NEXT

Say clearly if the sample is too small to draw conclusions.

Rules:
- Separate FACTS (stated in the input) from INFERENCE (your reasoning). Label each line.
- Do not invent companies, people, numbers, dates or quotes. If something is missing, list it under MISSING CONTEXT.
- Keep reasoning to one short line per conclusion.
- Return structured output using the exact sections requested.
```

**Expected output.**
- A structural comparison
- A reusable template
- Two concrete next tests

**Check before using.**
Small samples produce confident nonsense. Ask for the sample-size caveat and read it.

---

### 15 · IMPROVE MY NEXT CAMPAIGN

**What it does.** Closes the loop: turns campaign results into the next campaign's brief.

**When to use it.** At the end of every campaign cycle.

**Input.**
- Reply analysis
- Pattern analysis
- Original hypothesis

**Prompt**

```text
ORIGINAL HYPOTHESIS: [HYPOTHESIS]
REPLY ANALYSIS: [ANALYSIS]
PATTERN ANALYSIS: [PATTERNS]

Produce the brief for my next campaign:
1. VERDICT ON THE HYPOTHESIS — supported / partially supported / rejected, with the evidence
2. WHAT TO KEEP
3. WHAT TO CHANGE — ranked by expected impact
4. NEW HYPOTHESIS — same falsifiable format
5. UPDATED ICP OR SIGNAL CHANGES
6. WHAT I STILL CANNOT ANSWER WITH THIS DATA

Change one major variable at a time and say which one.

Rules:
- Separate FACTS (stated in the input) from INFERENCE (your reasoning). Label each line.
- Do not invent companies, people, numbers, dates or quotes. If something is missing, list it under MISSING CONTEXT.
- Keep reasoning to one short line per conclusion.
- Return structured output using the exact sections requested.
```

**Expected output.**
- A verdict on the previous hypothesis
- A ranked change list
- The next hypothesis, ready to run

**Check before using.**
If the plan changes the ICP, the message and the channel at once, you will not learn which one mattered.


---


## Chained run

The source page's own ordering — 4 stages expanded into 6 steps:

1. DEFINE — 01, 02, 03
2. RESEARCH — 04, 05, 06, 07
3. QUALIFY — 08
4. WRITE — 09, 10
5. FOLLOW UP — 11, 12
6. LEARN — 13, 14, 15

Re-enter the loop wherever your context is stale. Store each stage's output in the brain
(`~/brains/ops/` or the client lane folder) so the next run starts from real context.
