# Template: competitor landscape report outline

Copy into `~/ops/kb/<topic>/<slug>-YYYY-MM.md`, fill in, then `sources.py verify`
before delivering. Written in English, no emojis. Delete this header block after
copying.

---

# <Product/category> — Competitor & Adjacent-Service Landscape

Compiled: <DD Month YYYY> · Scope: <what is in and out> · Method: <n search batches,
m extracted sources, all links in Sources>

## 1. Market segmentation

Six buckets, one short paragraph each, then the vendor table:
- A. Certified / enterprise vendors
- B. Hardware & OEM makers
- C. Software-only analytics layers (closest analogue)
- D. Hardware + human monitored service
- E. Adjacent sensing modalities competing for the same budget
- F. Free / open-source floor

## 2. Vendor table

| Segment | Vendor | Country | What it is | Tech | Certification / claim | Public price | Link |

One row per vendor. "What it is" = one operator-language sentence, not marketing copy.

## 3. Public price anchors

| Reference | Amount | Basis | What it proves | Source |

Only public/verifiable numbers. State explicitly that the rest is quote-only —
that absence is itself a finding.

## 4. Standards & claim boundaries

What a product in this class may legally claim; the exact wording vendors in the
category use for the same limitation; the disclaimer this product must carry.

## 5. Free / open-source alternatives

What a motivated buyer or a DIY operator can reach for $0 — datasets, models,
platforms, trials. This caps pricing; it is mandatory, not optional.

## 6. Naming & trademark risk

Existing brands that collide; whether the phrase is a generic regulated service
term; what the brand must not imply.

## 7. Where <our product> fits

- Differentiators vs each segment (or "no observed vendor does X" — mark `[unverified]`)
- Realistic buyer profile and the price anchor it must sit under
- What we must NOT claim
- Sales objections we will hit, with the number that answers each

## 8. Gaps in this research / next steps

What was searched and not found (regional vendors, pricing, certification paths),
and the follow-up rounds worth running.

## Sources

Rendered by `sources.py render --cited-in <draft> --append`; verified with
`sources.py verify <draft>` (exit 0 before delivery). Coverage and uncited
warnings are read, not ignored.
