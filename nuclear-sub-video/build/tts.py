import json,subprocess,wave,sys,os
S=sys.argv[1]; segs=json.load(open(f"{S}/build/script.json"))
os.makedirs(f"{S}/build/vo",exist_ok=True); tot=0; out=[]
for i,(sc,t) in enumerate(segs):
    clean=t.replace('*','')
    fn=f"{S}/build/vo/{i:02d}.wav"
    subprocess.run(["python3","-m","piper","-m",f"{S}/tts/en_US-ryan-high.onnx","--length-scale","1.05","--sentence-silence","0.25","-f",fn],input=clean.encode(),check=True,capture_output=True)
    w=wave.open(fn); d=w.getnframes()/w.getframerate(); tot+=d; out.append(d)
json.dump(out,open(f"{S}/build/vo_dur.json","w")); print(len(segs),"segments, speech total",round(tot,1), "rate",w.getframerate())
