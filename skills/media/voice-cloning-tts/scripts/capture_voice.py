#!/usr/bin/env python3
"""Capture user voice LIVE from Google Meet to build a clean XTTS reference.

WHY: Telegram voice notes can arrive as pure tones (see SKILL.md pitfall #13) —
XTTS clones a tone reference into beep replies. Recording the user's voice
directly from the Meet audio path (Chrome speaker sink monitor, the same sink
the meeting agent listens on) bypasses the corrupted Telegram delivery.

USAGE:
  python3 capture_voice.py            # user talks 40-60s while it runs
  # then: meeting_agent.py --ref /tmp/ref_voice.wav

Verified 2026-08: 6 chunks / 32.2s captured with pitch-verified speech
(pitch histogram clustered 180-240Hz = male voice; zcps≈1592 alone is NOT
decisive for tone vs speech — always confirm with pitch clustering).
"""
import subprocess, wave, struct, os, sys, time, glob

SINK = "alsa_output.platform-snd_aloop.0.analog-stereo"  # Chrome speaker sink (Meet audio)
OUT = "/tmp/voice_capture/"
os.makedirs(OUT, exist_ok=True)
for f in glob.glob(OUT + "*.wav"):
    os.remove(f)

NEEDED = 8  # ~40s of non-silent audio (8 x 5s)
collected = 0
start = time.time()

print("[capture] Bolo! ~40 sec non-silent awaz chahiye. Timeout 3 min.", flush=True)
while collected < NEEDED and time.time() - start < 180:
    chunk = f"{OUT}chunk_{collected:02d}.wav"
    r = subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "pulse", "-i", f"{SINK}.monitor",
         "-t", "5", "-ar", "16000", "-ac", "1", chunk],
        timeout=12, capture_output=True)
    if not os.path.exists(chunk) or os.path.getsize(chunk) < 20000:
        continue
    with wave.open(chunk, "rb") as wf:
        frames = wf.readframes(wf.getnframes())
    vals = struct.unpack(f"<{len(frames)//2}h", frames)
    rms = (sum(v * v for v in vals) / len(vals)) ** 0.5
    if rms > 60:  # speech threshold (real silence <10; speech 500+)
        collected += 1
        print(f"[capture] {collected}/{NEEDED} chunks saved (rms={rms:.0f})", flush=True)
    else:
        os.remove(chunk)
        print(f"[capture] silent chunk (rms={rms:.0f}) — bolo!", flush=True)

if collected == 0:
    print("[capture] FAIL: koi awaz nahi mili — user meeting me hai? mic ON hai?", flush=True)
    sys.exit(1)

# Concatenate all chunks
files = sorted(glob.glob(OUT + "chunk_*.wav"))
listfile = OUT + "list.txt"
with open(listfile, "w") as f:
    for p in files:
        f.write(f"file '{p}'\n")
out_wav = "/tmp/ref_voice.wav"
subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
                "-i", listfile, "-ar", "22050", "-ac", "1", out_wav], check=True)

# Verify speech vs tone: RMS variation + pitch (autocorrelation) histogram.
# zcps alone misleads (speech with sibilants hit 1500+); pitch clustering is decisive.
with wave.open(out_wav, "rb") as wf:
    n = wf.getnframes(); sr = wf.getframerate()
    vals = struct.unpack(f"<{n}h", wf.readframes(n))

# per-window RMS variation (speech varies, tone is flat)
import math
win = 4000  # 0.25s @ 16k
window_rms = []
for i in range(0, len(vals) - win, win):
    w = vals[i:i + win]
    window_rms.append((sum(v * v for v in w) / len(w)) ** 0.5)
rms_std = (sum((r - sum(window_rms) / len(window_rms)) ** 2 for r in window_rms) / len(window_rms)) ** 0.5

# pitch histogram via autocorrelation (50-300Hz fundamental range)
from collections import Counter
pitch_bins = Counter()
step, size = 1024, 2048
for i in range(0, len(vals) - size, step):
    frame = vals[i:i + size]
    best, bestlag = 0, 0
    for lag in range(int(sr / 300), int(sr / 50)):  # 50-300Hz
        s = sum(frame[j] * frame[j + lag] for j in range(0, len(frame) - lag, 4))
        if s > best:
            best, bestlag = s, lag
    if bestlag:
        pitch_bins[round(sr / bestlag, -1)] += 1
top = pitch_bins.most_common(3)

rms = (sum(v * v for v in vals) / len(vals)) ** 0.5
dur = n / sr
print(f"[capture] DONE: {out_wav} dur={dur:.1f}s rms={rms:.0f} rms_std={rms_std:.0f} top_pitch={top}", flush=True)
if rms_std < 200:
    print("[capture] WARNING: flat RMS — ho sakta hai tone ho. Dobara try karo.", flush=True)
else:
    print("[capture] SPEECH CONFIRMED (rms variation) — reference ready!", flush=True)
