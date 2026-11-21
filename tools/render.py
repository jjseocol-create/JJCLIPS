#!/usr/bin/env python3
"""Render one vertical clip.
Usage: render.py spec.json
spec: {id, url, start, end, peak, words:[[s,e,w]...], cover_title, cover_sub, out}
Layout 1080x1920: facecam on top (1080x680), gameplay center crop below (1080x1240).
Facecam punch-in zoom around the peak. Spanish karaoke-style subtitles. Cover as first 0.5 s.
"""
import json, os, subprocess, sys
import cv2, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

S = json.load(open(sys.argv[1]))
W, H = 1080, 1920
CAM_H = 680
work = f"/home/claude/vods/work/{S['id']}"
os.makedirs(work, exist_ok=True)
raw = f"{work}/raw.mp4"
if not os.path.exists(raw):
    subprocess.run(["yt-dlp", "-q", "-f", "1080p60", "--download-sections",
                    f"*{S['start']:.2f}-{S['end']:.2f}", "--force-keyframes-at-cuts",
                    "-o", raw, S["url"]], check=True, stderr=subprocess.DEVNULL)
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                            "csv=p=0", raw], capture_output=True, text=True).stdout)

# ---- locate facecam (purple-room overlay) ----
CANDS = {"right": (1483, 302, 437, 275), "right3": (1483, 283, 437, 275), "topright": (1483, 0, 437, 275), "topleft": (0, 0, 528, 360)}
def purple_frac(img, r):
    x, y, w, h = r
    hsv = cv2.cvtColor(img[y:y + h, x:x + w], cv2.COLOR_BGR2HSV)
    return float(((hsv[..., 0] > 120) & (hsv[..., 0] < 165) & (hsv[..., 1] > 70) & (hsv[..., 2] > 60)).mean())
cap = cv2.VideoCapture(raw)
votes = {k: 0.0 for k in CANDS}
frames = []
for f in np.linspace(0.1, 0.9, 7):
    cap.set(cv2.CAP_PROP_POS_MSEC, f * dur * 1000)
    ok, img = cap.read()
    if ok:
        frames.append(img)
        for k, r in CANDS.items():
            votes[k] += purple_frac(img, r)
best = max(votes, key=votes.get)
cam = CANDS[best] if votes[best] / max(1, len(frames)) > 0.08 else None

# ---- cover image ----
peak_rel = min(max(S["peak"] - S["start"], 0.5), dur - 0.5)
cap.set(cv2.CAP_PROP_POS_MSEC, peak_rel * 1000)
ok, still = cap.read()
cap.release()
still = cv2.cvtColor(still, cv2.COLOR_BGR2RGB)
simg = Image.fromarray(still)
if cam:
    x, y0, w, h = cam
    face = simg.crop((x + int(w * 0.18), y0 + int(h * 0.04), x + int(w * 0.82), y0 + int(h * 0.80)))
    face = face.resize((W, int(W * face.height / face.width)), Image.LANCZOS)
    fh = min(face.height, 900)
    gh = H - fh
    gw_src = int(1080 * W / gh)
    gxx = max(0, (1483 - gw_src) // 2) if best != "topleft" else 528 + (1392 - gw_src) // 2
    game = simg.crop((gxx, 0, gxx + gw_src, 1080)).resize((W, gh), Image.LANCZOS)
    bg = Image.new("RGB", (W, H))
    bg.paste(game, (0, fh))
    bg.paste(face.crop((0, 0, W, fh)), (0, 0))
else:
    gx0 = (1920 - 608) // 2
    bg = simg.crop((gx0, 0, gx0 + 608, 1080)).resize((W, H), Image.LANCZOS)
# Vice-sunset grade
grad = Image.new("RGB", (W, H))
gd = ImageDraw.Draw(grad)
for yy in range(H):
    t = yy / H
    c = (int(255 * (1 - t) + 70 * t), int(70 * (1 - t) + 20 * t), int(150 * (1 - t) + 120 * t))
    gd.line([(0, yy), (W, yy)], fill=c)
cover = Image.blend(bg, grad, 0.22)
dark = Image.new("RGBA", (W, H), (0, 0, 0, 0))
dd = ImageDraw.Draw(dark)
for yy in range(H // 2, H):
    a = int(200 * (yy - H // 2) / (H // 2))
    dd.line([(0, yy), (W, yy)], fill=(10, 0, 25, a))
cover = Image.alpha_composite(cover.convert("RGBA"), dark)
d = ImageDraw.Draw(cover)
F = "/usr/share/fonts/truetype/anton/Anton-Regular.ttf"
if not os.path.exists(F):
    F = subprocess.run(["fc-match", "-f", "%{file}", "Anton"], capture_output=True, text=True).stdout
def fit(text, maxw, size):
    while size > 40:
        f = ImageFont.truetype(F, size)
        if d.textlength(text, font=f) <= maxw:
            return f
        size -= 4
    return ImageFont.truetype(F, size)
lines = S["cover_title"].upper().split("\n")
y = 1180
for ln in lines:
    f = fit(ln, 980, 190)
    tw = d.textlength(ln, font=f)
    x = (W - tw) / 2
    for dx in range(-8, 9, 4):
        for dy in range(-8, 9, 4):
            d.text((x + dx, y + dy), ln, font=f, fill=(0, 0, 0))
    # pink->orange fill via mask
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).text((x, y), ln, font=f, fill=255)
    fillimg = Image.new("RGBA", (W, H))
    fd = ImageDraw.Draw(fillimg)
    bb = f.getbbox(ln)
    for yy in range(int(y + bb[1]), int(y + bb[3]) + 1):
        t = (yy - (y + bb[1])) / max(1, bb[3] - bb[1])
        fd.line([(0, yy), (W, yy)], fill=(255, int(220 - 120 * t), int(90 + 60 * t), 255))
    cover.paste(fillimg, (0, 0), m)
    y += bb[3] + 20
sub = S.get("cover_sub", "")
if sub:
    f = ImageFont.truetype(F, 64)
    tw = d.textlength(sub.upper(), font=f)
    d.rounded_rectangle([(W - tw) / 2 - 30, y + 20, (W + tw) / 2 + 30, y + 120], 24, fill=(255, 40, 140))
    d.text(((W - tw) / 2, y + 28), sub.upper(), font=f, fill=(255, 255, 255))
fb = ImageFont.truetype(F, 54)
d.rounded_rectangle([40, 70, 40 + d.textlength("JJ CLIPS", font=fb) + 50, 170], 20, fill=(20, 10, 40))
d.text((65, 82), "JJ CLIPS", font=fb, fill=(255, 190, 90))
fg = ImageFont.truetype(F, 72)
gt = "GTA VI"
gtw = d.textlength(gt, font=fg)
d.rounded_rectangle([W - gtw - 100, 60, W - 40, 180], 24, fill=(255, 255, 255))
d.text((W - gtw - 70, 70), gt, font=fg, fill=(20, 10, 40))
cover = cover.convert("RGB")
cover.save(f"{work}/cover.jpg", quality=92)
cover.save(S["out"].replace(".mp4", "_portada.jpg"), quality=92)

# ---- subtitles (ASS) ----
def ts(t):
    t = max(0, t); h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"
OFF = 0.5  # cover duration
sub_y = CAM_H + 210 if cam else 1450
ass = [
    "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "",
    "[V4+ Styles]",
    "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
    "Style: S,Anton,96,&H00FFFFFF,&H0000D7FF,&H00000000,&H64000000,0,0,0,0,100,100,1,0,1,7,3,8,60,60,0,1",
    "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
words = [w for w in S["words"] if w[1] > S["start"] and w[0] < S["end"]]
groups, cur = [], []
for w in words:
    cur.append(w)
    txt = w[2].strip()
    if len(cur) >= 3 or txt.endswith((".", "?", "!", ",")):
        groups.append(cur); cur = []
if cur:
    groups.append(cur)
for gi, g in enumerate(groups):
    gs = g[0][0] - S["start"] + OFF
    ge = (groups[gi + 1][0][0] if gi + 1 < len(groups) else g[-1][1] + 0.4) - S["start"] + OFF
    ge = min(ge, g[-1][1] - S["start"] + OFF + 0.6)
    for wi, w in enumerate(g):
        ws = w[0] - S["start"] + OFF
        we = (g[wi + 1][0] - S["start"] + OFF) if wi + 1 < len(g) else ge
        parts = []
        for k, ww in enumerate(g):
            t = ww[2].strip().upper().replace("{", "").replace("}", "")
            parts.append("{\\c&H0000D7FF&}" + t + "{\\c&H00FFFFFF&}" if k == wi else t)
        start = gs if wi == 0 else ws
        ass.append(f"Dialogue: 0,{ts(start)},{ts(max(we, start + 0.05))},S,,0,0,{sub_y},,{{\\fad(0,0)}}" + " ".join(parts))
open(f"{work}/subs.ass", "w").write("\n".join(ass))

# ---- ffmpeg compose ----
zs = max(0.0, peak_rel - 1.2); ze = min(dur, peak_rel + 2.3)
if cam:
    x, y0, w, h = cam
    zx, zy, zw, zh = x + int(w * 0.2), y0 + int(h * 0.1), int(w * 0.6), int(h * 0.6)
    gw = int(1080 * 1080 / (H - CAM_H)) // 2 * 2
    gx = (1483 - gw) // 2 if best != "topleft" else 528 + (1920 - 528 - gw) // 2
    fc = (f"[0:v]fps=30,split=3[a][b][c];"
          f"[a]crop={gw}:1080:{gx}:0,scale=1080:{H-CAM_H}[g];"
          f"[b]crop={w}:{h}:{x}:{y0},scale=1080:{CAM_H}[cm];"
          f"[c]crop={zw}:{zh}:{zx}:{zy},scale=1080:{CAM_H}[cz];"
          f"[cm][cz]overlay=0:0:enable='between(t,{zs:.2f},{ze:.2f})'[camf];"
          f"[camf][g]vstack[v0];")
else:
    fc = (f"[0:v]fps=30,split=2[a][b];"
          f"[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20[bgv];"
          f"[b]scale=1080:-2[fg];[bgv][fg]overlay=0:(H-h)/2[v0];")
fc += (f"[v0]subtitles={work}/subs.ass:fontsdir=/usr/share/fonts[v1];"
       f"[1:v]scale=1080:1920,fps=30,format=yuv420p[cv];"
       f"[v1]format=yuv420p,tpad=start_duration={OFF}:start_mode=clone[v2];"
       f"[v2][cv]overlay=0:0:eof_action=pass:enable='lt(t,{OFF})',format=yuv420p[vout];"
       f"[0:a]adelay={int(OFF*1000)}:all=1,loudnorm=I=-14:TP=-1.5:LRA=11[aout]")
cmd = ["ffmpeg", "-v", "error", "-y", "-i", raw, "-loop", "1", "-t", str(OFF + 0.04), "-i", f"{work}/cover.jpg",
       "-filter_complex", fc, "-map", "[vout]", "-map", "[aout]",
       "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-profile:v", "high", "-pix_fmt", "yuv420p",
       "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-movflags", "+faststart", "-t", str(dur + OFF), S["out"]]
subprocess.run(cmd, check=True)
print("OK", S["out"], "cam=", best if cam else None)
