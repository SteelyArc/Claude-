import json,sys,matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
from shapely.geometry import shape
def G(i): return shape(json.load(open(f'data/geo/{i}.geojson'))['geometry'])
def draw(ax,g,**k):
    for p in getattr(g,'geoms',[g]):
        x,y=p.exterior.xy;ax.fill(x,y,**k)
fig,axs=plt.subplots(1,3,figsize=(24,9))
for ax,(t,layers) in zip(axs,[('1773-93',[(2692511,'#d9c38f')]),('Jul-Sep 1793',[(2748128,'#d9c38f')]),('1793-95',[(2692510,'#d9c38f')])]):
    draw(ax,G(2851944) if t=='1773-93' else G(2890609),fc='#b9c7a6',ec='k',lw=.3)
    draw(ax,G(2830452) if t=='1773-93' else G(2748500),fc='#a9b8cc',ec='k',lw=.3)
    draw(ax,G(2748049),fc='#e3c9a8',ec='k',lw=.3)
    for i,c in layers: draw(ax,G(i),fc=c,ec='r',lw=1)
    for n,(x,y) in {'Warsaw':(21.01,52.23),'Vilnius':(25.28,54.69),'Pinsk':(26.1,52.11),'Minsk':(27.56,53.9),'Lutsk':(25.32,50.75),'Kremenets':(25.71,50.1),'Zhytomyr':(28.66,50.25),'Kamianets':(26.58,48.68),'Grodno':(23.83,53.68),'Druja':(27.45,55.79),'Nesvizh':(26.67,53.22),'Kraków':(19.94,50.06),'Gdańsk':(18.65,54.35),'Toruń':(18.6,53.01),'Poznań':(16.93,52.41),'Mitau':(23.72,56.65)}.items():
        ax.plot(x,y,'k.');ax.text(x+.1,y+.1,n,fontsize=8)
    ax.set_xlim(14,33);ax.set_ylim(47.5,58);ax.set_aspect(1.65);ax.set_title(t)
plt.savefig('research/diagnostics/ohm_plt_check.png',dpi=70,bbox_inches='tight')
