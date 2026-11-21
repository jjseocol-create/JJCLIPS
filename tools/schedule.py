#!/usr/bin/env python3
"""Build per-network posting plan. Usage: schedule.py final.json meta.json start_date(YYYY-MM-DD) out.json"""
import json, random, sys, datetime as dt
picks = [p["id"] for p in json.load(open(sys.argv[1]))]
meta = json.load(open(sys.argv[2]))
start = dt.date.fromisoformat(sys.argv[3])
SLOTS = ["08:10", "09:05", "10:00", "10:55", "11:50", "12:45", "13:40", "14:35", "15:30",
         "16:25", "17:20", "18:15", "19:10", "20:05", "21:00"]
BASE = "https://raw.githubusercontent.com/jjseocol-create/jjclips/main/clips/"
def slots(n, offset_min=0):
    out = []
    for i in range(n):
        d = start + dt.timedelta(days=i // len(SLOTS))
        h, m = map(int, SLOTS[i % len(SLOTS)].split(":"))
        t = dt.datetime(d.year, d.month, d.day, h, m) + dt.timedelta(minutes=offset_min)
        out.append(t.strftime("%Y-%m-%dT%H:%M:%S"))
    return out
tt_order = picks[:]
yt_order = picks[:]
random.Random(7).shuffle(yt_order)
# make sure no clip lands within the same slot on both networks
for i in range(len(yt_order)):
    if yt_order[i] == tt_order[i]:
        j = (i + 3) % len(yt_order)
        yt_order[i], yt_order[j] = yt_order[j], yt_order[i]
plan = []
for net, order, off in (("tiktok", tt_order, 0), ("youtube", yt_order, 20)):
    for cid, when in zip(order, slots(len(order), off)):
        m = meta[cid]
        q = m["q"]
        tags = " ".join(m["tags"])
        if net == "tiktok":
            text = f"{q}\n\n{m['d']}\n\n{tags} #gaming #fyp #parati #elmune"
            info = {"autoPublish": True, "draft": False, "text": text, "media": [BASE + cid + ".mp4"],
                    "providers": [{"network": "tiktok"}],
                    "publicationDate": {"dateTime": when, "timezone": "America/Bogota"},
                    "tiktokData": {"privacyOption": "PUBLIC_TO_EVERYONE", "disableComment": False,
                                   "disableDuet": False, "disableStitch": False, "autoAddMusic": False,
                                   "commercialContentThirdParty": False, "commercialContentOwnBrand": False,
                                   "isAigc": False}}
        else:
            title = (q.split("\"")[1] if "\"" in q else q)
            title = f"\"{title}\" | GTA VI #shorts"[:100]
            text = f"{m['d']}\n\n{tags} #gaming #shorts #elmune"
            info = {"autoPublish": True, "draft": False, "text": text, "media": [BASE + cid + ".mp4"],
                    "providers": [{"network": "youtube"}],
                    "publicationDate": {"dateTime": when, "timezone": "America/Bogota"},
                    "youtubeData": {"title": title, "type": "short", "privacy": "public",
                                    "category": "GAMING", "madeForKids": False,
                                    "tags": [t.lstrip("#") for t in m["tags"]] + ["gta 6", "gameplay", "elmune"],
                                    "isAiGeneratedContent": False}}
        plan.append({"net": net, "id": cid, "date": when + "-05:00", "info": info})
json.dump(plan, open(sys.argv[4], "w"), ensure_ascii=False, indent=1)
for p in plan:
    print(p["net"], p["date"], p["id"])
