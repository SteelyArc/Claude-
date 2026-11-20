import time, skia
from engine import *
t0=time.time(); base=Base(); fin=Finish(); print('load',time.time()-t0)
cx,cy=city('Warsaw'); 
cam=Cam(250,150,1080/1500)
rf=RevealField(LAYERS['plc_pre'], seeds=[city('Warsaw')], res=3)
print('field',time.time()-t0)
s=skia.Surface(W,H); c=s.getCanvas()
for name,t in [('a',0.55),('b',1.0)]:
    t1=time.time()
    c.clear(C(*PAL['paper'])); base.draw(c,cam)
    for n,col in [('prussia_pre','prussia'),('russia_pre','russia'),('habsburg','austria'),('ottoman','neutral'),('sweden','neutral'),('hre_other','neutral')]:
        fill_territory(c,cam,layer_path(n),PAL[col],0.42,glow_w=10)
    rf.draw_masked(c,cam,layer_path('plc_pre'),PAL['plc'],0.6,t,edge_color=(150,110,50))
    draw_rivers(c,cam,flow_t=t*10)
    draw_border(c,cam,layer_path('plc_pre'),PAL['ink'],2.6,t=t)
    for k in ['Warsaw','Vilnius','Kraków','Danzig']:
        x,y=cam.to_screen(*city(k)); city_marker(c,x,y,1,capital=k=='Warsaw'); map_label(c,x+14,y-14,k,size=34,fontname=SERIF,tracking=0.02,align='left')
    x,y=cam.to_screen(450,250); map_label(c,x,y,'POLISH–LITHUANIAN',size=48,t=t)
    fin.apply(c,1.0,cam)
    s.makeImageSnapshot().save(f'/tmp/claude-0/test_{name}.png')
    print(name,time.time()-t1)
