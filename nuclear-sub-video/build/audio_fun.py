# Funny music + cartoon SFX, no voiceover
import json, wave, numpy as np, sys
from scipy.signal import lfilter, butter
S=sys.argv[1]; SR=44100; TL=json.load(open(f"{S}/web/timeline.json")); T=TL['total']; N=int(T*SR)
rng=np.random.default_rng(3)
def lp(x,fc,o=2): b,a=butter(o,fc/(SR/2)); return lfilter(b,a,x)
def hp(x,fc,o=2): b,a=butter(o,fc/(SR/2),'high'); return lfilter(b,a,x)
def bp(x,lo,hi,o=2): b,a=butter(o,[lo/(SR/2),hi/(SR/2)],'band'); return lfilter(b,a,x)
L_=np.zeros((2,N),np.float32)
def add(x,t,g=1.0,pan=0.5):
    i=int(t*SR); 
    if i>=N or i+len(x)<=0: return
    j=min(N,i+len(x)); x=x[:j-i]
    L_[0,i:j]+=x*g*(1-pan)*2*0.7; L_[1,i:j]+=x*g*pan*2*0.7
def mtof(m): return 440*2**((m-69)/12)
def ts(d): return np.arange(int(d*SR))/SR
sc={s['scene']:s for s in TL['scenes']}; seg=TL['segs']
def sg(n,k): return seg[sc[n]['segs'][k]]['start']
def spd(n,k): s=seg[sc[n]['segs'][k]]; return s['speechEnd']-s['start']
# ---------- instruments ----------
def tuba(m,d):
    t=ts(d); f=mtof(m); y=np.zeros_like(t)
    for h in range(1,7): y+=np.sin(2*np.pi*f*h*t)/h**1.3
    e=np.clip(t/0.02,0,1)*np.exp(-t*4)*np.clip((d-t)/0.03,0,1); return lp(y*e,900)*0.5
def pizz(m,d=0.25):
    t=ts(d); f=mtof(m); y=sum(np.sin(2*np.pi*f*h*t)*np.exp(-t*(10+h*6))/h for h in range(1,5)); return y*0.5
def lead(m,d,kind):
    t=ts(d); f=mtof(m)*(1+0.006*np.sin(2*np.pi*6*t)*np.clip(t/0.12,0,1))
    ph=2*np.pi*np.cumsum(f)/SR
    if kind=='square': y=sum(np.sin(ph*h)/h for h in (1,3,5,7,9))*0.6
    elif kind=='xylo': y=(np.sin(ph)+0.35*np.sin(ph*4))*np.exp(-t*7)*1.3
    elif kind=='whistle': y=np.sin(ph)*0.9+0.03*rng.standard_normal(len(t))
    else: y=(np.sin(ph)+0.5*np.sin(2*ph)+0.3*np.sin(3*ph))*0.7  # kazoo-ish
    if kind=='kazoo': y=np.tanh(3*y)*0.5; y=bp(y,300,3000)
    e=np.clip(t/0.01,0,1)*np.clip((d-t)/0.03,0,1); return y*e
def kick():
    t=ts(0.25); f=55+90*np.exp(-t*25); return np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-t*11)
def snare():
    t=ts(0.18); return (bp(rng.standard_normal(len(t)),1500,7000)*0.7+np.sin(2*np.pi*190*t)*0.5)*np.exp(-t*20)
def hat(): t=ts(0.04); return hp(rng.standard_normal(len(t)),8000)*np.exp(-t*90)
def block(m=84): t=ts(0.08); return np.sin(2*np.pi*mtof(m)*t)*np.exp(-t*60)
def boing(f0=200,d=0.5):
    t=ts(d); f=f0*(1+1.2*np.exp(-t*8)*np.sin(2*np.pi*14*t)); return np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-t*4)*0.6
def slide(f0,f1,d):
    t=ts(d); f=f0*(f1/f0)**(t/d)*(1+0.02*np.sin(2*np.pi*7*t)); return np.sin(2*np.pi*np.cumsum(f)/SR)*np.clip(t/0.03,0,1)*np.clip((d-t)/0.05,0,1)*0.6
def bloop(): f0=300+rng.random()*500; t=ts(0.09); f=f0*(1+5*t/0.09); return np.sin(2*np.pi*np.cumsum(f)/SR)*np.sin(np.pi*t/0.09)
def wahwah():  # sad trombone
    out=[]
    for m,d in [(58,0.45),(57,0.45),(56,0.45),(55,1.3)]:
        t=ts(d); f=mtof(m)*(1+0.03*np.sin(2*np.pi*(5 if d>1 else 0)*t)); ph=2*np.pi*np.cumsum(f)/SR
        y=np.tanh(2.5*sum(np.sin(ph*h)/h for h in range(1,8)))*np.clip(t/0.04,0,1)*np.clip((d-t)/0.08,0,1); out.append(lp(y,1800))
    return np.concatenate(out)*0.35
def noise(d,lo,hi,dec): t=ts(d); return bp(rng.standard_normal(len(t)),lo,hi)*np.exp(-t*dec)
# ---------- arrangement ----------
bpm=132; beat=60/bpm; bar=4*beat; e8=beat/2
scale=[60,62,64,65,67,69,71]
def deg(d): o,i=divmod(d,7); return scale[i]+12*o
chords=[0,5,3,4, 0,5,1,4]   # C Am F G C Am Dm G
motifs={'A':[(0,1),(2,1),(4,1),(2,1),(4,2),(7,2)],'B':[(4,1),(None,1),(4,1),(5,1),(4,1),(2,1),(0,2)],
 'C':[(7,1),(6,1),(4,1),(2,1),(3,1),(1,1),(0,2)],'D':[(0,3),(1,1),(2,2),(None,2)],'E':[(4,1),(4,1),(None,1),(2,1),(None,1),(0,1),(-1,1),(0,1)]}
phr=['A','B','A','C','A','E','D','C']
def section(t):
    # (lead kind or None, lead vol, drums, pizz, sneaky)
    for name,kind,lv,dr,pz,sn in [('surface','square',1,0.6,1,0),('ballast','xylo',0.9,0.3,1,0),('dive','xylo',0.9,0.4,1,0),('deep','whistle',0.7,0.0,1,1),
        ('reactor','square',0.9,0.8,1,0),('fission','xylo',1,0.8,1,0),('chain','square',1,1,1,0),('rods','kazoo',0.8,0.8,1,0),('reactor2','kazoo',0.8,0.8,1,0),
        ('primary','square',0.9,0.9,1,0),('steamgen','xylo',1,0.9,1,0),('turbine','kazoo',0.9,1,1,0),('condenser','square',0.9,0.9,1,0),('gears','xylo',1,1,1,0),
        ('shaft','xylo',1,1,1,0),('prop','square',1,1,1,0),('life','whistle',0.9,0.7,1,0),('sonar',None,0,0,1,1),('food','kazoo',0.9,0.8,1,0),
        ('surfacing','square',1,1,1,0),('recap','square',1,1,1,0),('end','xylo',1,0.6,1,0)]:
        if name in sc and sc[name]['start']<=t<sc[name]['end']: return kind,lv,dr,pz,sn
    return 'square',1,1,1,0
nb=int(T/bar)+1
for b in range(nb):
    t0=b*bar
    if t0>T-1.2: break
    kind,lv,dr,pz,sn=section(t0+0.01)
    if t0<1.8: kind,dr=None,0   # little intro: bass only
    ch=chords[b%8]; root=deg(ch)-24
    # oom-pah
    for k in range(4):
        if k%2==0: add(tuba(root+(0 if k==0 else 7),beat*0.8),t0+k*beat,0.55*(0.6 if sn else 1))
        elif pz and not sn: 
            for d in (0,2,4): add(pizz(deg(ch+d)),t0+k*beat,0.12,0.3+0.2*d/4)
    if sn:  # sneaky staccato pizz walking
        for k in range(8):
            if k%2==0: add(pizz(deg(ch+[0,2,4,5,4,2,0,-1][k])-12,0.2),t0+k*e8,0.22,0.4)
        if b%2==0: add(block(88),t0+3.5*beat,0.15,0.7)
    # drums
    if dr>0:
        for k in range(4):
            if k in (0,2): add(kick(),t0+k*beat,0.5*dr)
            else: add(snare(),t0+k*beat,0.25*dr,0.55)
            add(hat(),t0+k*beat+e8,0.12*dr,0.65)
        if b%4==3: add(block(84),t0+3.75*beat,0.2*dr,0.3); add(block(79),t0+3.5*beat,0.2*dr,0.7)
    # melody
    if kind:
        mot=motifs[phr[b%8]]; pos=0; sw=0.06*beat
        for d,n in mot:
            tt=t0+pos*e8+(sw if pos%2==1 else 0); dur=n*e8*0.9
            if d is not None:
                m=deg(ch+d)+12 if kind!='whistle' else deg(ch+d)+24
                add(lead(m,dur,kind),tt,0.11*lv,0.55)
            pos+=n
        if b%8==7 and kind!='whistle': add(boing(260,0.4),t0+3.5*beat,0.12,0.6)
# ---------- cartoon SFX ----------
for s in TL['scenes'][1:]:
    add(noise(0.4,600,4000,7)*np.sin(np.pi*ts(0.4)/0.4),s['start']-0.2,0.08)
add(slide(1400,300,1.6),sc['dive']['start']+0.2,0.25)                 # slide whistle down
vent=sg('ballast',2)+1.6
for k in range(60): add(bloop(),vent+rng.random()*6,0.12,rng.random())
for t in [sc['deep']['start']+1.0, sg('deep',2)+1.0, sc['sonar']['start']+0.8, sg('sonar',2)+0.4]:
    p=np.sin(2*np.pi*1350*ts(2))*np.exp(-ts(2)*3.5); add(p,t,0.15); add(p,t+0.5,0.06)
hit=sg('fission',0)+spd('fission',0)*0.38; add(boing(500,0.3),hit,0.25); add(noise(1.2,300,5000,4),hit+0.8,0.3); add(slide(300,1800,0.25),hit+0.8,0.2)
for k in range(120):
    t=sc['chain']['start']+1.2+rng.gamma(4,0.9)
    if t<sc['chain']['end']: add(pizz(72+int(rng.random()*24),0.12),t,0.12,rng.random())
scram=sg('rods',2)+spd('rods',2)*0.38
for k in range(4): add(lead(76 if k%2==0 else 71,0.25,'kazoo'),scram+0.1+k*0.3,0.35)   # silly siren
add(boing(120,0.6),sg('gears',0)+1.0,0.3)
add(wahwah(),sg('food',2)+spd('food',2)*0.5,0.9)                      # sad trombone on "limit is the food"
br=sg('surfacing',1)-0.4+0.66
add(slide(300,1500,1.3),sg('surfacing',0)+0.8,0.22)                   # slide whistle up
for k in range(60): add(bloop(),sg('surfacing',0)+0.8+rng.random()*6,0.12,rng.random())
add(noise(2.5,150,5000,1.6),br-0.2,0.45)
# ta-da ending
for m in (60,64,67,72): add(lead(m,1.6,'square')*np.exp(-ts(1.6)*1.5),T-2.4,0.12,0.3+0.1*(m-60)/12)
add(kick(),T-2.4,0.6); add(noise(1.5,3000,9000,3),T-2.4,0.12)
# ---------- master ----------
tt=np.arange(N)/SR; L_*=np.clip(tt/0.3,0,1)*np.clip((T-tt)/0.6,0,1)
L_/=np.max(np.abs(L_))*1.05
w=wave.open(f"{S}/build/"+(sys.argv[2] if len(sys.argv)>2 else 'mix_fun.wav'),'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((L_.T*32767).astype(np.int16).tobytes()); w.close(); print('ok')
