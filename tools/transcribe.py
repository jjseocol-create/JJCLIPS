#!/usr/bin/env python3
import json, sys, subprocess, numpy as np
from faster_whisper import WhisperModel
m=WhisperModel("small",device="cpu",compute_type="int8",cpu_threads=2)
cands=json.load(open(sys.argv[1])); out=sys.argv[2]
res=[]
for c in cands:
    s=max(0,c["t"]-45)
    a=np.frombuffer(subprocess.run(["ffmpeg","-v","error","-ss",str(s),"-t","85","-i",c["src"],"-vn","-ac","1","-ar","16000","-f","s16le","-"],capture_output=True).stdout,np.int16).astype(np.float32)/32768
    segs,_=m.transcribe(a,language="es",word_timestamps=True,vad_filter=True,condition_on_previous_text=False)
    words=[]; sents=[]
    for sg in segs:
        sents.append([round(sg.start+s,2),round(sg.end+s,2),sg.text.strip()])
        for w in (sg.words or []): words.append([round(w.start+s,2),round(w.end+s,2),w.word])
    c["sents"]=sents; c["words"]=words; res.append(c)
    json.dump(res,open(out,"w"))
print("done",len(res))
