# Replica costing & capability model ("build exactly this, high-pitch")

Deliver **four numbers**: dev-days, calendar weeks, one-time cash, monthly run cost — plus the
capability-gap verdict. All figures are estimates: label them as such and tell the user to
re-confirm pricing at quote time.

## Dev-day table (1 dev-day = ~8h)

| Workstream | Parity | Hardened ("high-pitch") |
|---|---|---|
| Spec, schema, security rules | 4 | 6 |
| Backend (Firestore + Functions + FCM + aggregation) | 10 | 18 |
| App (auth, tabs, wizard, camera, map, offline sync) | 32 | 45 |
| AI pipeline (species/health, tips, fallback, rate limit) | 4 | 8 |
| Admin / moderation panel (usually missing in the original) | 8 | 14 |
| Arabic i18n + RTL + EN copy polish | 4 | 8 |
| QA (device matrix, rules tests, load, RTL) | 6 | 14 |
| Store compliance + assets + account deletion | 5 | 8 |
| **Total** | **~73** | **~121** |

Calendar: parity 2 devs ≈ 5–7 weeks (solo 11–14). Hardened 3 devs ≈ 10–14 weeks.
**Add 3–5 weeks for the store window** on top of code.

## One-time cash lanes

- Offshore senior (PK/EG/IN, $15–25/h): parity $6–12k | hardened $18–35k.
- Gulf/EU agency ($40–80/h): parity $25–45k | hardened $60–120k.
- AI-assisted lane (1 specialist contractor + our agents/CI): parity $3–6k cash | hardened $8–15k.
- Extras: Play $25 one-time, Apple $99/yr, branding $0.5–2k, AR/EN copy $0.3–0.8k,
  security + PDPL review $1–3k, ASO/store assets $0.3–1k.

## Monthly run cost

- Pilot ≤1k users: **$0–5** (inside free tiers; Blaze needed only for Functions/triggers).
- 10k MAU: **$150–450** (Firestore $30–80, storage+egress $20–60, AI $10–40, Functions $5–15).
- 100k MAU: **$1.5–4k**.

**The map stack is the single biggest architectural cost decision — decide it before writing code.**
Google Maps mobile SDK "Dynamic Maps" is billed per map load: 10k MAU × 20 loads ≈ +$1,200/mo,
100k MAU ≈ **+$21k/mo**, against MapLibre + self-hosted pmtiles ≈ ~$0–50/mo even at 100k MAU.
Same for photo storage: force ~250 KB client-side compression or 2M uploads (~1.5 TB) make egress
dominate the bill. AI scans are cheap: Flash-class ≈ sub-cent/scan → 100k scans/mo ≈ $20–100
(plant ID can also use Pl@ntNet / Plant.id APIs).

## Store & legal gates

- New **personal** Play account: 12 testers × 14 consecutive days of closed testing before production.
- **Organization** account: D-U-N-S verification, 2–4 weeks.
- Firebase/Firestore **region is immutable** — pick `me-central2` (Dammam) at project creation when
  KSA PDPL residency matters; it is also a differentiator for government-adjacent work.
- Account-deletion path + privacy policy on a real page (not a raw storage blob) are hard requirements.

## Infra-capability verdict (our side)

Probe the build toolchain rather than assuming: `for c in flutter dart javac gradle sdkmanager adb
docker node firebase gcloud; do printf "%s=%s " $c "$(command -v $c>/dev/null&&echo Y||echo N)"; done`
in short batches, plus `nproc`, `free -g`, `df -h /`.

Typical split: everything server-side, web/admin, AI services, notifications, storage/CDN, CI/CD and
Arabic RTL is already in place; the usual single missing lane is the **native build + store submit**
toolchain. Cheapest fix, in order:
1. **Cloud CI (recommended, $0):** GitHub Actions ubuntu runner + Flutter/JDK 17/Android SDK → AAB/IPA,
   Firebase App Distribution for testers, fastlane for Play upload. Keep the VM as control plane —
   a 2-vCPU / limited-RAM VM with gateway guardrails is the wrong place to run Gradle (slow + risk).
2. Local lane, only if offline builds are required: Flutter SDK + JDK 17 + cmdline-tools +
   build-tools/platform ≈ 12–15 GB disk, with a real RAM/time penalty.
3. Device QA on a device cloud (Test Lab / Maestro / commercial device farms); aarch64 emulators on
   these VMs are impractical.

## Hard truth to include

A true 1:1 replica **copies the original's defects** (open rules, arrays-in-doc, client-derived
leaderboards, missing moderation). Recommend "replicate the features, fix the architecture", and
name explicitly which original choices must NOT be copied. Expected shape of the answer:
capability score (~"75–80% ready today"), the one missing lane with its cheapest fix, then
cost/time.
