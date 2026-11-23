import json,sys
S=sys.argv[1]; old=json.load(open(f"{S}/web/timeline_5min.json"))
plan=[("surface",7,["How does a *nuclear submarine* work?","It can hide underwater for *months*!"]),
("ballast",8,["*Ballast tanks* fill up with *seawater*...","...the sub gets heavy and *sinks*."]),
("dive",4,["*Diving planes* steer it down."]),
("deep",7,["Down here there's *no air* to burn fuel...","...so it runs on a *nuclear reactor*."]),
("reactor",4,["The fuel rods are full of *uranium*."]),
("fission",6,["A *neutron* smashes a uranium atom...","...it *splits* and fires out more neutrons!"]),
("chain",5,["A *chain reaction*! It all turns into *heat*."]),
("rods",7,["*Control rods* soak up neutrons...","...push them in and the reaction *slows*. Drop them all: *STOP!*"]),
("primary",6,["Super hot water loops through the core. *High pressure* stops it boiling."]),
("steamgen",6,["The *steam generator* passes the heat on...","...and a second loop boils into *steam*."]),
("turbine",6,["Steam spins the *turbines* super fast."]),
("gears",4,["*Gears* slow that spin down..."]),
("prop",6,["...to turn the *propeller*. Water goes back, sub goes *forward*!"]),
("life",6,["The power also makes *fresh water* and *oxygen* for the crew."]),
("sonar",5,["It stays *silent*, and listens with *sonar*."]),
("food",6,["The fuel lasts *30+ years*...","...the real limit? The *food*."]),
("surfacing",7,["To go up, *air* blasts the water out!","*Splash!*"]),
("end",5,["Follow for more *how things work*!"])]
segs=[];scenes=[];caps=[];t=0.0;oseg=old['segs']
for name,D,texts in plan:
    osc=next(s for s in old['scenes'] if s['scene']==name)
    ids=osc['segs']; w=[oseg[i]['end']-oseg[i]['start'] for i in ids]; tw=sum(w)
    st=t+0.3; new_ids=[]
    for i,wi in zip(ids,w):
        slot=(D-0.5)*wi/tw; segs.append(dict(i=len(segs),scene=name,text='',start=round(st,3),speechEnd=round(st+slot*0.8,3),end=round(st+slot,3))); new_ids.append(len(segs)-1); st+=slot
    scenes.append(dict(scene=name,start=round(t,3),end=round(t+D,3),segs=new_ids))
    n=len(texts)
    for k,tx in enumerate(texts): caps.append(dict(text=tx,start=round(t+0.2+k*D/n,3),end=round(t+(k+1)*D/n-0.1,3)))
    t+=D
segs[-1]['end']=t
json.dump(dict(total=t,segs=segs,scenes=scenes,caps=caps),open(f"{S}/web/timeline.json","w"),indent=0); print("total",t)
