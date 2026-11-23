import json, wave, numpy as np, sys
from scipy.signal import lfilter, butter, resample_poly
S=sys.argv[1]; SR=44100; TL=json.load(open(f"{S}/web/timeline.json")); T=TL['total']; N=int(T*SR)
rng=np.random.default_rng(1)
def rd(fn):
    w=wave.open(fn); a=np.frombuffer(w.readframes(w.getnframes()),dtype=np.int16).astype(np.float32)/32768; return a,w.getframerate()
def smooth(x,k):
    c=np.cumsum(np.concatenate([[0],x])); y=(c[k:]-c[:-k])/k; pad=len(x)-len(y); return np.concatenate([np.full(pad//2,y[0]),y,np.full(pad-pad//2,y[-1])])
def lp(x,fc,o=2): b,a=butter(o,fc/(SR/2)); return lfilter(b,a,x)
def hp(x,fc,o=2): b,a=butter(o,fc/(SR/2),'high'); return lfilter(b,a,x)
def bp(x,lo,hi,o=2): b,a=butter(o,[lo/(SR/2),hi/(SR/2)],'band'); return lfilter(b,a,x)
def addat(buf,x,t,g=1.0):
    i=int(t*SR); j=min(N,i+len(x));
    if i<N: buf[i:j]+=x[:j-i]*g
tt=np.arange(N)/SR
# ---------------- voice ----------------
vo=np.zeros(N,np.float32)
for s in TL['segs']:
    a,sr=rd(f"{S}/build/vo/{s['i']:02d}.wav"); a=resample_poly(a,SR,sr).astype(np.float32); addat(vo,a,s['start'])
vo=hp(vo,70); vo=vo/np.max(np.abs(vo))*0.9
# voice presence env for ducking
env=np.abs(vo); k=int(0.25*SR); env=smooth(env,k); duck=1-0.55*np.clip(env/0.04,0,1)
# ---------------- music ----------------
def mtof(m): return 440*2**((m-69)/12)
bpm=96; beat=60/bpm; bar=4*beat
prog=[[57,60,64],[53,57,60],[48,52,55],[55,59,62],[57,60,64],[53,57,60],[50,53,57],[52,56,59]]  # Am F C G Am F Dm E
def section_level(t):
    # (pad, arp, bass, drums)
    if t<15: return (0.8,0.5,0.0,0.0)
    if t<62: return (1.0,0.25,0.4,0.0)
    if t<116: return (0.9,0.7,0.8,0.5)
    if t<205: return (0.9,0.8,0.9,0.7)
    if t<239: return (0.9,0.6,0.7,0.4)
    if t<254: return (1.0,0.2,0.3,0.0)
    if t<293: return (0.9,0.7,0.9,0.6)
    return (1.0,0.4,0.5,0.0)
music=np.zeros((2,N),np.float32)
chord_len=2*bar; nch=int(T/chord_len)+2
def saw(f,t,nh=7):
    y=np.zeros_like(t)
    for h in range(1,nh+1): y+=np.sin(2*np.pi*f*h*t)/h
    return y
def sq(f,t,nh=7):
    y=np.zeros_like(t)
    for h in range(1,nh+1,2): y+=np.sin(2*np.pi*f*h*t)/h
    return y
for c in range(nch):
    t0=c*chord_len; ch=prog[c%len(prog)]
    if t0>=T: break
    if t0>=293: ch=[57,61,64]  # A major resolve
    L=int((chord_len+1.5)*SR); t=np.arange(L)/SR
    e=np.clip(t/1.2,0,1)*np.clip((chord_len+1.5-t)/1.5,0,1)
    lv=section_level(t0)
    pad=np.zeros(L)
    for i,m in enumerate(ch):
        f=mtof(m-12); pad+=saw(f*1.003,t,6)+saw(f*0.997,t,6)
    pad=lp(pad,1400)*e*0.035*lv[0]
    addat(music[0],pad,t0); addat(music[1],np.roll(pad,300),t0)
    # bass
    if lv[2]>0:
        for b in range(8):
            tb=b*beat; Lb=int(beat*0.9*SR); tbb=np.arange(Lb)/SR; f=mtof(ch[0]-24)
            y=(np.sin(2*np.pi*f*tbb)+0.3*np.sin(4*np.pi*f*tbb))*np.exp(-tbb*3)*0.12*lv[2]
            addat(music[0],y,t0+tb); addat(music[1],y,t0+tb)
    # arp 8ths
    if lv[1]>0:
        pat=[0,1,2,1,0,2,1,2]
        for k in range(16):
            m=ch[pat[k%8]]+12+(12 if k%4==3 else 0); ta=k*beat/2; La=int(0.35*SR); ta_=np.arange(La)/SR
            y=sq(mtof(m),ta_,9)*np.exp(-ta_*9)*0.03*lv[1]
            pan=0.5+0.35*np.sin(k)
            addat(music[0],y*(1-pan)*2,t0+ta); addat(music[1],y*pan*2,t0+ta)
    # drums: kick + hat
    if lv[3]>0:
        for b in range(8):
            Lk=int(0.25*SR); tk=np.arange(Lk)/SR; f=60*np.exp(-tk*18)+45
            kick=np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-tk*12)*0.18*lv[3]
            addat(music[0],kick,t0+b*beat); addat(music[1],kick,t0+b*beat)
            Lh=int(0.05*SR); hat=hp(rng.standard_normal(Lh),7000)*np.exp(-np.arange(Lh)/SR*80)*0.03*lv[3]
            addat(music[0],hat,t0+b*beat+beat/2); addat(music[1],hat,t0+b*beat+beat/2)
# simple stereo echo
d=int(beat*0.75*SR)
for ch in range(2): music[ch][d:]+=0.25*music[1-ch][:-d]
music*=duck
# ---------------- sfx ----------------
sfx=np.zeros(N,np.float32)
sc={s['scene']:s for s in TL['scenes']}; seg=TL['segs']
def sg(name,k): return seg[sc[name]['segs'][k]]['start']
def spd(name,k): s=seg[sc[name]['segs'][k]]; return s['speechEnd']-s['start']
def ping(t,g=0.25):
    L=int(3*SR); x=np.arange(L)/SR; y=np.sin(2*np.pi*1350*x)*np.exp(-x*3.5)
    for dly,a in [(0.45,0.4),(0.9,0.2),(1.4,0.1)]: i=int(dly*SR); y[i:]+=a*np.sin(2*np.pi*1350*x[:L-i])*np.exp(-x[:L-i]*3.5)
    addat(sfx,y*g,t)
def bubbles(t0,dur,g=0.12,dens=40):
    n=int(dur*dens)
    for k in range(n):
        t=t0+rng.random()*dur; L=int((0.02+rng.random()*0.05)*SR); x=np.arange(L)/SR; f0=300+rng.random()*700
        y=np.sin(2*np.pi*(f0*x+f0*6*x*x/ (L/SR)))*np.sin(np.pi*x/(L/SR)); addat(sfx,y*g*(0.5+rng.random()),t)
def noiseburst(t,dur,lo,hi,g,att=0.05):
    L=int(dur*SR); x=np.arange(L)/SR; y=bp(rng.standard_normal(L),lo,hi)*np.clip(x/att,0,1)*np.exp(-x*3/dur); addat(sfx,y*g,t)
def whoosh(t,g=0.05):
    L=int(0.7*SR); x=np.arange(L)/SR; y=bp(rng.standard_normal(L),400,3000)*np.sin(np.pi*x/0.7)**2; addat(sfx,y*g,t-0.35)
for s in TL['scenes'][1:]: whoosh(s['start'])
# ocean surface ambience
surf=lp(rng.standard_normal(N),600)*0.05*(0.6+0.4*np.sin(2*np.pi*tt/6))
mask=((tt<15.5)|(tt>sc['surfacing']['start']+sg('surfacing',1)-sc['surfacing']['start']-0.4)).astype(np.float32)
mask=smooth(mask,SR); sfx+=surf*mask
# underwater rumble
uw=lp(rng.standard_normal(N),180)*0.08
um=np.zeros(N,np.float32)
for name in ['ballast','dive','deep','prop','sonar']:
    a,b=sc[name]['start'],sc[name]['end']; um[int(a*SR):int(b*SR)]=1
um[int(sc['surfacing']['start']*SR):int((sg('surfacing',1)-0.4)*SR)]=1
um=smooth(um,SR); sfx+=uw*um
# events
vent=sg('ballast',2)+1.6; bubbles(vent,6.5,0.1,60); noiseburst(vent,2.5,200,1500,0.12,0.02)
for t in [sc['deep']['start']+1.0, sg('deep',1)+0.5, sg('deep',2)+1.0, sc['sonar']['start']+0.8, sg('sonar',2)+0.4, sg('sonar',2)+2.4]: ping(t,0.18)
hit=sg('fission',0)+spd('fission',0)*0.38; split=hit+0.8
L=int(2.5*SR); x=np.arange(L)/SR; zap=np.sin(2*np.pi*(900*x-200*x*x))*np.exp(-x*2.5)*0.15+bp(rng.standard_normal(L),300,4000)*np.exp(-x*4)*0.2; addat(sfx,zap,split)
for k in range(140):
    t=sc['chain']['start']+1.2+rng.gamma(4,0.9)*1.0
    if t<sc['chain']['end']: noiseburst(t,0.08,1500,6000,0.08,0.002)
scram=sg('rods',2)+spd('rods',2)*0.38
for k in range(5):
    L=int(0.18*SR); x=np.arange(L)/SR; addat(sfx,sq(880,x,7)*0.06,scram+0.1+k*0.32)
L=int(0.6*SR); x=np.arange(L)/SR; addat(sfx,np.sin(2*np.pi*70*x)*np.exp(-x*8)*0.4,scram+0.3)
# turbine whine
a,b=sc['turbine']['start'],sc['turbine']['end']; L=int((b-a)*SR); x=np.arange(L)/SR; f=200+600*(1-np.exp(-x/1.5)); ph=2*np.pi*np.cumsum(f)/SR
wh=(np.sin(ph)+0.4*np.sin(2*ph))*0.03*np.clip(x/0.5,0,1)*np.clip(((b-a)-x)/0.5,0,1); addat(sfx,wh,a)
# electrolysis / life bubbles
bubbles(sg('life',2)+0.5,4.5,0.05,25); bubbles(sg('surfacing',0)+0.8,7,0.1,70); noiseburst(sg('surfacing',0)+0.8,3,300,3000,0.15,0.05)
breach=sg('surfacing',1)-0.4+1.1*0.6; noiseburst(breach-0.2,2.5,150,5000,0.35,0.05)
# prop churn
a,b=sc['prop']['start'],sc['prop']['end']; L=int((b-a)*SR); x=np.arange(L)/SR
churn=bp(rng.standard_normal(L),80,600)*(0.6+0.4*np.sin(2*np.pi*7*x))*0.12*np.clip(x/0.5,0,1)*np.clip(((b-a)-x)/0.5,0,1); addat(sfx,churn,a)
sfx*=(0.55+0.45*duck)
# mix
mix=np.stack([vo+music[0]+sfx, vo+music[1]+sfx])
fade=np.clip((T-tt)/1.5,0,1)*np.clip(tt/0.5,0,1); mix*=fade
mix/=np.max(np.abs(mix))*1.05
w=wave.open(f"{S}/build/mix.wav",'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((mix.T*32767).astype(np.int16).tobytes()); w.close(); print("ok", mix.shape)
