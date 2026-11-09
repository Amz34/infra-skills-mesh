# Aliyun slider captcha — CDP automation observations (2026-09-03)

Context: automating the signup captcha on developer.amd.com.cn (Aliyun 滑块验证
widget) from a headless VM. **Outcome: NOT SOLVED.** ~40+ trusted-CDP drags with
exact piece placement were ALL rejected; the user stopped the run over token
cost. This file records VERIFIED mechanics so a future session either wins fast
or — more likely — recognizes the wall early. Do not treat this as a working
recipe.

## Widget anatomy (verified)
- Root class `.aliyunCaptcha-top` (presence ⇒ captcha open).
- Puzzle area: background image ~296×200 natural, displayed 300×200 (dpr
  scaled) around viewport x≈570, y≈234 (varies per page/layout).
- `.slider-move` = the **40px-wide HANDLE** element in the bottom slider row
  (starts at x == bg.x, y≈462). **It is NOT the puzzle piece.** Trap: reading
  `.slider-move` offset measures handle motion, which follows a non-linear law
  vs the mouse — do not confuse it with piece geometry.
- Puzzle piece = a separate ~52×200 image. Its PNG often has alpha≈0 / is
  nearly empty (piece art may be CSS-composited), and the piece element can
  return `None` from DOM queries during/after a drag — track the handle rect
  instead of the piece rect.
- State texts: 验证失败 (fail toast, ~1–2 s), 验证超时，请关闭后重试 (instance idle
  timeout — recover via full page reload), 重新初始化验证码 (re-init button ⇒ fresh
  puzzle), send button 发送验证码.
- **Real success signal = the send-code button flips to a countdown
  重新发送(Ns).** Widget collapse alone is NOT success — it transiently
  collapses between puzzle refreshes (caused a false-positive "SUCCESS").

## Persistence (verified)
- A failed drag does NOT refresh the puzzle: same uuid + same background image
  persist ⇒ per-puzzle calibration/sweeps (deltas around a detected target) are
  possible instead of one-shot guesses. But persistence did NOT help when
  validation rejected every position (below).
- Puzzle images come sometimes as `data:` URLs, sometimes from the CDN
  (static-captcha.aliyuncs.com). VM-side curl of the CDN often fails, and
  `data:` URLs produce no Network events — do not build the pipeline on
  downloading the images.

## Drag mechanics (measured; mechanism unverified)
- The handle does NOT track the mouse 1:1. Bulk-fit of handle offset vs mouse
  displacement (5 px/40 ms steps, trusted CDP `Input.dispatchMouseEvent`):
  `off ≈ 0.003533·X² + 0.0767·X`; to land the handle at offset T, mouse
  `X = (√(0.00588 + 0.014132·T) − 0.0767)/0.007066`. This non-linearity is
  itself suspicious (input-stream easing / risk-control filter) — treat as
  empirical and re-measure each session.
- Mid-drag pauses of 450–500 ms+ → widget freezes the drag (timeout). Long
  oscillations / huge accumulated travel (~1300 px+) → freeze (robot
  signature). Keep 30–40 ms cadence, monotonic motion, clamped total travel.

## Detection (worked reliably)
- Screenshot-clip detection beats image downloading: `Page.captureScreenshot`
  with clip `{x, y, width, height, scale: 1}` over the puzzle box → PIL crop →
  column-edge scan for the gap. Screenshot px == CSS px at dpr 1; no
  CDN/data-URL dependency.
- Detection bias ±6 px observed once (detected 2, accepted only at 8) — when
  validation IS reachable, sweep ±~10 px per puzzle.

## Instrumentation
- Wrapping `window.fetch` / XHR to log widget network traffic logged NOTHING —
  captcha traffic bypasses main-frame fetch/XHR. Don't rely on it.

## The wall (conclusive)
- Synthetic JS `.click()`/Event dispatch on the slider: rejected outright.
- Every trusted-CDP trajectory (adaptive servo, stepped, clean quadratic,
  various speeds): validation failed even with the piece within ±2 px of the
  pixel-detected target.
- Full position sweep on one persistent puzzle (piece offsets 15–245 — the
  entire feasible range): NO accepted position ⇒ rules out detection-offset
  theories entirely.
- ~40+ attempts, zero sustained pass. Implication: Aliyun validates the INPUT
  STREAM / trajectory fingerprint, not final geometry — accuracy of placement
  is not the variable you can win on.

## Discipline for the next attempt
- Do NOT re-engage this captcha class with more drag tuning — it is a token
  sink with a ~0% observed success rate from a datacenter VM.
- If a task genuinely requires it: budget ~10 clean drags max, then hand the
  captcha to the user (one human solve) or drop it — same honest-limit rule as
  the Cloudflare/Turnstile and reCAPTCHA sections in SKILL.md.
- A fundamentally different input method (physical mouse / real desktop /
  human) is required — never more synthetic drags.
