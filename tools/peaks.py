#!/usr/bin/env python3
"""Find loud/hype moments in a VOD. Usage: peaks.py video.mp4 out.json [max_candidates]"""
import json, subprocess, sys
import numpy as np

src, out = sys.argv[1], sys.argv[2]
maxc = int(sys.argv[3]) if len(sys.argv) > 3 else 120
SR = 8000
p = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-vn", "-ac", "1", "-ar", str(SR),
                    "-f", "s16le", "-"], capture_output=True, check=True)
a = np.frombuffer(p.stdout, dtype=np.int16).astype(np.float32) / 32768
n = len(a) // SR
rms = np.sqrt((a[: n * SR].reshape(n, SR) ** 2).mean(axis=1) + 1e-9)
db = 20 * np.log10(rms)
# local baseline over 5 min, excitement = loudness above baseline
win = 300
pad = np.pad(db, (win // 2, win // 2), mode="edge")
base = np.array([np.median(pad[i:i + win]) for i in range(0, n)])
exc = db - base
# smooth over 4s windows
k = np.ones(4) / 4
score = np.convolve(exc, k, mode="same")
order = np.argsort(-score)
picked = []
for t in order:
    if len(picked) >= maxc:
        break
    if score[t] < 4:  # at least ~4 dB above local baseline
        break
    if t < 120 or t > n - 60:
        continue
    if any(abs(t - q) < 75 for q in picked):
        continue
    picked.append(int(t))
picked.sort()
json.dump({"duration": int(n), "peaks": [{"t": t, "score": round(float(score[t]), 2)} for t in picked]},
          open(out, "w"), indent=1)
print(len(picked), "candidates of", n, "s")
