#!/usr/bin/env python3
"""Place multiple VO clips onto one timeline at exact sample offsets.

WHY: ffmpeg adelay/amix chains SILENTLY DROP lines with several inputs.
This deterministic numpy placement is the verified replacement.

Usage:
  python3 place_vo_on_timeline.py OUT.wav TOTAL_SEC \
      vo1.raw=0.5 vo2.raw=5.6 vo3.raw=11.0 ...

Each VO file is raw s16le mono 24000 Hz (smallest.ai output). Offsets in
seconds. OUT.wav is 16-bit PCM mono 24000 Hz of TOTAL_SEC length.
"""
import sys
import wave
import numpy as np

SR = 24000


def read_raw(path: str) -> np.ndarray:
    data = np.fromfile(path, dtype=np.int16)
    return data.astype(np.float64) / 32768.0


def main() -> None:
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    out_path = sys.argv[1]
    total = float(sys.argv[2])
    specs = sys.argv[3:]  # path=offset_sec

    track = np.zeros(int(total * SR), dtype=np.float64)
    for spec in specs:
        path, off = spec.rsplit("=", 1)
        start = int(float(off) * SR)
        clip = read_raw(path)
        end = min(start + len(clip), len(track))
        track[start:end] += clip[: end - start]

    # normalize to 0.95 peak (avoid clipping when lines overlap slightly)
    peak = np.max(np.abs(track)) or 1.0
    track = track / peak * 0.95

    pcm = (track * 32767.0).astype(np.int16)
    with wave.open(out_path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(f"wrote {out_path}: {total:.3f}s, {len(specs)} VO lines")


if __name__ == "__main__":
    main()
