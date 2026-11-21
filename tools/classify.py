#!/usr/bin/env python3
import json, sys
import cv2, numpy as np
def kind(f):
    h=cv2.cvtColor(f,cv2.COLOR_BGR2HSV); H,W=f.shape[:2]
    m=np.ones((H,W),bool); m[:int(H*.32),int(W*.72):]=False; m[:int(H*.32),:int(W*.28)]=False
    purple=(((h[...,0]>120)&(h[...,0]<165)&(h[...,1]>70)&(h[...,2]>60))&m).mean()
    e=cv2.Canny(cv2.cvtColor(f,cv2.COLOR_BGR2GRAY),80,160).mean()/255
    if purple>0.04: return "cam"
    if e>0.14 and h[...,2].mean()<60: return "dash"
    return "game"
src,pj,out=sys.argv[1:4]
cap=cv2.VideoCapture(src); data=json.load(open(pj))
for p in data["peaks"]:
    tags=[]
    for dt in (-20,-10,0,10,20,30):
        cap.set(cv2.CAP_PROP_POS_MSEC,(p["t"]+dt)*1000); ok,f=cap.read()
        tags.append(kind(f) if ok else "none")
    p["tags"]=tags; p["game"]=tags.count("game")
json.dump(data,open(out,"w"),indent=1)
print(sum(1 for p in data["peaks"] if p["game"]>=5),"gameplay of",len(data["peaks"]))
