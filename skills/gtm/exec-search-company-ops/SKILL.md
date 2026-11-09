---
name: exec-search-company-ops
description: "Use when continuing Aamir's exec-search company build."
author: hermes-curator
license: MIT
version: 1.0.0
metadata:
  hermes:
    tags: [exec-search, ksa, recruitment, company-strategy, gtm]
    related_skills: [whatsapp-channel-ops]
---

# Exec-Search Company Build (KSA Engineering Leadership)

## When to Use

Any session continuing Aamir's retained executive-search / talent-intelligence company for Saudi built environment (engineering & technical leadership niche): strategy, GTM, licensing, automation/tech, research, or execution assets.

## Master artifact

- Strategy blueprint: `/home/ubuntu/ops/kb/exec-search-company-strategy.md` (~210 lines) — the canonical doc. Read/extend it; never re-derive from scratch or contradict it without explicit user direction.
- Pending (offered, not yet accepted): add Regulatory + Competitive landscape section to the file; Proof-First offer-doc template; Search OS technical spec; Market Map template; first sourcing-agent demo.
- Built 2026-09-11: `/home/ubuntu/ops/kb/exec-search-candidate-funnel-playbook.md` — teardown of the recruiter-side LinkedIn job-post funnel (Ahsan Riaz / lnkd.in case) + "Talent Pool First" two-sided replication playbook (dual-CTA posts, PDPL-grade intake, pool→mandate conversion, 14-day pilot). Master doc §9 now carries the "Candidate-Supply Flywheel" summary. Open decision recorded there: personal-profile reach vs firm-as-brand rule → recommended company page + firm-owned associate profile.

## Hard framing rules (user corrections — do not violate)

1. **No personal details in any strategy/output**: never Aamir's name, background, experience years, SCE/PMI credentials, LinkedIn history, CV, or personal phone/email as business reference. Company-level, generic founder/persona framing ONLY ("dont mention my details", "dont take my exp details" — said twice).
2. Client-facing material: pure English (or bilingual EN/AR for KSA deliverables), one-word/company brand, no personal angle, no human faces/living beings in visuals.
3. Reply Hinglish to Aamir (Roman Urdu/Hindi mix), concise, "bhai" + "aap".

## Locked strategic positions (do not re-litigate)

- Niche: specialist retained search, engineering & technical leadership, KSA built environment. Generalist/contingency never. White space confirmed (no KSA pure-engineering-leadership specialist exists).
- Geo 3-layer: Sell=KSA (90%, first 2 yrs); Source=GCC+worldwide Day 1; Expand=UAE Phase 3 (Year 2-3). Worldwide never a market.
- Service mix: 60% retained search / 25% talent-intelligence retainers / 15% advisory. Fees 22-28% first-year comp, 1/3-1/3-1/3 milestones, minimum engagement fee.
- Speed as product: kickoff 3d, market map 2wk, shortlist 4-5wk, close 8-10wk (market standard 12-16wk).
- Proof-First client confidence: show market map + 3 qualified candidates before fee; interview-fee option; small advisory ticket (SAR 15-30K) first → retained (SAR 200K+) later; 12-month replacement warranty; no-fit-no-full-fee.
- Tech: Search OS 7-stage pipeline (brief→market map→warm-path→outreach→screening→shortlist dashboard→post-placement), human stays for final convos/negotiation/refs. Stack = n8n/Python agents + Notion CRM + DeepSeek API + embeddings; ~80% code reuse from lead-qualifier + AI DS SaaS.
- GPU stance: none before revenue. DeepSeek API for ~95% work; Kaggle free T4 only later for (a) QLoRA Arabic matcher fine-tune, (b) Whisper+TTS voice screening (Sanad voice stack reuse).
- Content moat: quarterly "KSA Engineering Leadership Market Report" + weekly bilingual LinkedIn insights.
- Entry: MISA license (foreign) / CR + Chamber → MHRSD International Recruitment License; advisory-first on consulting CR while license processes (~6 months); Nitaqat dual-track compliance as product.

## Market map asset

First data asset = "KSA Engineering Leadership Market Map v1" (Wk 3-6): 50-100 target companies + senior leaders = product + pitch + Search OS seed data. Sourcing research reference: references/ksa-competitor-regulatory-notes.md.

## Sourcing & timing signals (fresh postings)

LinkedIn's jobs search honours an **arbitrary seconds** value in the `f_TPR` URL parameter
(`r1800` = last 30 minutes, where the UI only offers 24h/7d/30d), and the logged-out guest endpoint
(`/jobs-guest/jobs/api/seeMoreJobPostings/search`) returns machine-readable cards without a login or a
browser. A posting inside that 30-minute window means the **req just opened and the hiring contact is
working on it right now** — the best available moment to pitch retained search or probe who owns the req.
Always stack `&sortBy=DD`, and treat the "apply first ⇒ better callback" claim as directional, not proven.
Verified commands, live result counts, honest caveats and the Telegram-alert automation sketch:
`references/linkedin-jobs-fresh-posting-sourcing.md`.

## Partner / collaboration targets (how to sell without a licence)

Built 2026-09-11: `/home/ubuntu/ops/kb/exec-search-partner-targets.md` — 20 firms to COLLABORATE with (not compete), each with verified public contact + LinkedIn, in four waves:

- **Wave 1 (highest fit, KSA-based):** TASC Outsourcing KSA (= legal entity "Top Talent Consulting Ltd.", Nitaqat Platinum, bulk staffing strong / AI-leadership weak), CGP Group KSA (KAFD, exec search + contract staffing + EOR on an AI-enabled platform), The Professionals (Saudi-owned exec search), Talowiz (Riyadh AI recruiting agents), Jadeer.
- **Wave 2 (large licensed Saudi HR/staffing — subcontract + EOR/JV track):** Maharah, SMASCO, Manpower Saudi Arabia, Sundus Global, Saudi Workforce (EOR vehicle), Tauzeef.
- **Wave 3 (global brands with KSA desks — associate / split-fee / vendor route):** Korn Ferry, Robert Walters, Hays, Michael Page, Cooper Fitch, Charterhouse ME, CSG Talent, Hanson Search, NES Fircroft (Dhahran/Riyadh/NEOM), Brunel.
- **Wave 4 (channels):** AI Tinkerers Riyadh (sells "talent access" job posts), Mercor, Jadarat.

Condensed matrix with contacts, LinkedIn slugs and the outreach cadence: `references/ksa-partner-collaboration-targets.md`.

Pitch that works on all of them: *"Licence and client relationship stay yours. I supply the technical layer you don't have — AI/engineering-leadership sourcing, technical screening panels, comp benchmarks, candidate market maps — flat fee per deliverable or subcontracted day rate."*

Rules: (a) engagement is a **services/consulting subcontract**, never a per-placement success fee in our name — that is the unlicensed-placement exposure (SAR 200–250K); (b) our invoicing needs a licensed vehicle (subcontract through the partner's CR, or Premium Residency / MISA CR) — see playbook §9; (c) global-brand vendor onboarding + conflict checks take 4–8 weeks, so run Wave 1 and Wave 3 in parallel; (d) harvested contacts are **generic company lines** (info@ / switchboard) unless a named person is listed — verify on the live site/LinkedIn before sending, and never present a contact that did not literally appear in tool output.

## Arabic-audience side idea

WhatsApp jobs-channel ecosystem plays (job-assistant bot, channel-admin tooling, scam-filter, broadcast marketplace) — see the `whatsapp-channel-ops` skill (its `references/arabic-jobs-channel-case.md` has the worked example + ecosystem sources).
