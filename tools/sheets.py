#!/usr/bin/env python3
"""Contact sheets: per candidate 3 frames (t-12, t, t+12). Usage: sheets.py video peaks.json prefix outdir"""
import json, os, subprocess, sys
import cv2, numpy as np

src, pj, prefix, outdir = sys.argv[1:5]
os.makedirs(outdir, exist_ok=True)
peaks = json.load(open(pj))["peaks"]
cap = cv2.VideoCapture(src)
def frame(t):
    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
    ok, f = cap.read()
    return f if ok else np.zeros((160, 284, 3), np.uint8)
rows = []
for i, p in enumerate(peaks):
    t = p["t"]
    fs = [cv2.resize(frame(x), (284, 160)) for x in (t - 12, t, t + 12)]
    row = np.hstack(fs)
    lab = np.zeros((160, 90, 3), np.uint8)
    cv2.putText(lab, f"{prefix}{i}", (4, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    cv2.putText(lab, f"{p['score']}", (4, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
    rows.append(np.hstack([lab, row]))
for k in range(0, len(rows), 10):
    img = np.vstack(rows[k:k + 10])
    cv2.imwrite(f"{outdir}/{prefix}_{k//10:02d}.jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 70])
print("ok", len(rows))
