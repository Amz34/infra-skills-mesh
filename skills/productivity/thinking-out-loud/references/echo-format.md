# Echo Format — template and worked example

One reply, five sections, dense. The reader should be able to find and fix a
wrong item in seconds. Target well under 250 words for a ten-minute ramble.

Compression rules:

- Nothing appears twice.
- No recap of the input — everything outside **My additions** is the
  requester's material by definition, so repeating it back is pure noise.
- One line per bullet.
- Vague quantifiers ("usual", "standard", "soon", "the normal one") go to
  **Open** or **My additions** — they are never silently resolved into a
  locked value.
- Order **Locked** and **My additions** by how load-bearing each item is.

## Template

```markdown
## Mission
<one sentence: what is actually being achieved>

## Locked (your decisions and constraints)
- <one line each; mark the stated priority **top priority**>

## Open (needs your answer)
- <question the ramble raised but did not answer>

## Ledger
- Flipped: <position A>, then <position B>. Going with B.
- Parked: <tangent, one line>

## My additions (correct these first)
- Inferred: <implied but never stated>
- Guessed: <gap I filled>
```

Close with: "Correct anything that's off, especially My additions. Want the
interview for the Open items?"

## Worked example

**Ramble (compressed, Hinglish as it arrived):** "ok voice pe switch kar raha
hu, typos ignore karo. matlab mujhe ek daily digest chahiye — jo main build kar
raha hu uske hisaab se rank ho, sirf points se nahi. email pe bhejo roz subah,
bina mere touch ke — agar manually trigger karna pada to useless hai. ek client
ke liye bhi chahiye, uske interests alag hain. also random thought, ye baad me
product ban sakta hai but chhodo. aur haan subah ka matlab subah hi hai, koi
timezone drama nahi."

**Echo:**

```markdown
## Mission
A zero-touch daily digest, ranked by personal relevance, delivered by email
every morning.

## Locked
- Relevance ranking over raw points
- Two recipients with separate interest profiles (requester + one client)
- Email delivery
- **Top priority**: fully automatic — a manual trigger makes it useless

## Open
- What defines "relevance to what I'm building": a written interest profile,
  recent repo activity, something else?
- Which timezone is "morning", and for which recipient?

## Ledger
- Parked: possible commercial product later

## My additions (correct these first)
- Inferred: each recipient gets their own ranking, not one shared list
- Guessed: source pool is a public front page plus new items
- Guessed: "no timezone drama" means a single fixed local time for both

Correct anything that's off, especially My additions. Want the interview for
the Open items?
```

## Why the example works

- The contradiction-free parts (ranking, email, automation) are Locked; the
  one soft spot ("subah", timezone) is Open **and** also shows up in My
  additions, because the echo had to assume something to write the Mission.
- "Product ban sakta hai but chhodo" is Parked, not deleted — the tangent is
  cheap to keep and often returns.
- Nothing appears in two sections: the automation priority is Locked; its
  implication (no manual trigger path) is not restated elsewhere.
- The closing line points the reader at the section most likely to be wrong
  before they read anything else.
