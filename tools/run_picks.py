#!/usr/bin/env python3
"""Render picks sequentially. picks file: list of {id, a, b, cover, sub?}; a/b are offsets vs peak t."""
import json, os, subprocess, sys
URL = {"A": "https://kick.com/elmune/videos/01a1f1d5-91e0-758f-a3a4-8f0583dcd0de",
       "B": "https://kick.com/elmune/videos/01a1f66d-80f0-7ced-8b15-6820cda6841d",
       "C": "https://kick.com/elmune/videos/01a1fb4a-7010-7cb6-a80e-60ad6f9c882f"}
picks = json.load(open(sys.argv[1]))
tr = {}
for f in sys.argv[2:]:
    for c in json.load(open(f)):
        tr[c["id"]] = c
os.makedirs("/home/claude/clips", exist_ok=True)
for p in picks:
    out = f"/home/claude/clips/{p['id']}.mp4"
    if os.path.exists(out):
        continue
    c = tr[p["id"]]
    spec = {"id": p["id"], "url": URL[p["id"][0]], "start": c["t"] + p["a"], "end": c["t"] + p["b"],
            "peak": c["t"] + p.get("pk", 0), "words": c["words"], "cover_title": p["cover"],
            "cover_sub": p.get("sub", ""), "out": out}
    os.makedirs(f"/home/claude/vods/work/{p['id']}", exist_ok=True)
    sp = f"/home/claude/vods/work/{p['id']}/spec.json"
    json.dump(spec, open(sp, "w"))
    r = subprocess.run(["python3", "/home/claude/scripts/render.py", sp], capture_output=True, text=True)
    print(p["id"], r.stdout.strip()[-80:], r.stderr.strip()[-300:], flush=True)
