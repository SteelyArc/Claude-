import json,sys
S=sys.argv[1]; TOTAL=300.0
segs=json.load(open(f"{S}/build/script.json")); dur=json.load(open(f"{S}/build/vo_dur.json"))
lead,tail=1.2,4.0
gaps=[]
for i in range(len(segs)-1):
    gaps.append(1.6 if segs[i][0]!=segs[i+1][0] else 0.6)
free=TOTAL-lead-tail-sum(dur)
k=free/sum(gaps); gaps=[g*k for g in gaps]
t=lead; out=[]
for i,(sc,txt) in enumerate(segs):
    out.append(dict(i=i,scene=sc,text=txt,start=round(t,3),speechEnd=round(t+dur[i],3)))
    t+=dur[i]+(gaps[i] if i<len(gaps) else 0)
for i,s in enumerate(out):
    s['end']=out[i+1]['start'] if i+1<len(out) else TOTAL
out[0]['start0']=0
# scenes
scenes=[]
for s in out:
    if scenes and scenes[-1]['scene']==s['scene']: scenes[-1]['end']=s['end']; scenes[-1]['segs'].append(s['i'])
    else: scenes.append(dict(scene=s['scene'],start=0 if not scenes else s['start']-0.0,end=s['end'],segs=[s['i']]))
# scene boundary at midpoint of gap before first speech
for j in range(1,len(scenes)):
    a=out[scenes[j]['segs'][0]]; prev=out[a['i']-1]
    b=round((prev['speechEnd']+a['start'])/2,3); scenes[j]['start']=b; scenes[j-1]['end']=b
json.dump(dict(total=TOTAL,segs=out,scenes=scenes),open(f"{S}/web/timeline.json","w"),indent=0)
print("gap scale",round(k,2)); [print(f"{x['scene']:10s} {x['start']:6.1f} {x['end']:6.1f} {x['end']-x['start']:5.1f}") for x in scenes]
