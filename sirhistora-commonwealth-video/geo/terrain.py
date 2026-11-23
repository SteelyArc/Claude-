import json,math,numpy as np
from PIL import Image,ImageDraw,ImageFilter
from shapely.geometry import shape
from shapely.ops import unary_union
from shapely.validation import make_valid
from shapely.geometry import box
import importlib.util,sys
# reuse projection
src=open('geo/build_geo.py').read().split("D={y:load")[0]
g={};exec(src.split("def load(y)")[0],g)
toPx=g['toPx'];W,H=g['W'],g['H']
S=1  # full res
land=unary_union([make_valid(shape(f['geometry'])) for f in json.load(open('geo/land-10m.geojson'))['features']]).intersection(box(-10,30,70,72))
mask=Image.new('L',(W,H),0);d=ImageDraw.Draw(mask)
polys=[land] if land.geom_type=='Polygon' else list(land.geoms)
for p in polys:
    if p.geom_type!='Polygon':continue
    d.polygon([toPx(x,y) for x,y in p.exterior.coords],fill=255)
    for r in p.interiors: d.polygon([toPx(x,y) for x,y in r.coords],fill=0)
m=np.asarray(mask).astype(np.float32)/255
rng=np.random.default_rng(11)
def noise(scale,blur):
    n=rng.random((H//scale+2,W//scale+2)).astype(np.float32)
    return np.asarray(Image.fromarray((n*255).astype(np.uint8)).resize((W,H),Image.BICUBIC).filter(ImageFilter.GaussianBlur(blur))).astype(np.float32)/255
fb=(noise(160,30)*1+noise(50,8)*.5+noise(14,2)*.25)/1.75
# mountains
mt=Image.new('L',(W,H),0);dm=ImageDraw.Draw(mt)
ranges={'carp':([(17.3,48.6),(19.5,49.3),(21.5,49.4),(23.0,49.0),(24.5,48.2),(25.5,47.5),(26.0,46.3),(25.6,45.5),(24.0,45.4),(22.5,45.2),(21.9,44.8)],70),
'alps':([(6.0,44.5),(7.0,45.8),(8.5,46.4),(10.5,46.5),(12.5,47.0),(14.5,47.2),(16.0,47.6)],95),
'scan':([(5.5,58.5),(7.5,60.5),(10,62),(12.5,63.5),(14.5,65.5),(16.5,67.5)],110),
'dinar':([(14.5,45.8),(16.5,44.0),(18.5,43.0),(20.0,42.0),(21.5,41.0)],80),
'stara':([(22.5,43.6),(25.0,42.8),(27.5,42.7)],45),'sudet':([(12.5,50.5),(14.5,50.8),(16.5,50.4),(17.5,50.0)],40),
'cauc':([(37.5,44.5),(40,43.5),(43,42.8),(46,41.8)],80),'crim':([(33.5,44.6),(35.0,44.9)],22),
'apen':([(8.5,44.3),(11,44),(13.5,42.5),(15.5,40.8),(16.2,39)],60),'pind':([(20.5,40.5),(21.5,39.0),(22.0,38.0)],45),
'anat':([(29,40),(33,39.8),(37,40.3),(41,40.2)],70),'taur':([(30,37.2),(33,36.8),(36,37.4)],60)}
for k,(pts,wd) in ranges.items():
    dm.line([toPx(*p) for p in pts],fill=255,width=wd,joint='curve')
mtn=np.asarray(mt.filter(ImageFilter.GaussianBlur(55))).astype(np.float32)/255
mtn=np.clip(mtn/(mtn.max()+1e-6)*1.3,0,1)
height=fb*0.3+mtn*(0.55+0.35*noise(24,5))
# hillshade
gy,gx=np.gradient(np.asarray(Image.fromarray((height*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2))).astype(np.float32))
shade=np.clip(0.5+(-gx*0.7-gy*0.7)*0.09,0,1)
# colors
yy=np.linspace(0,1,H)[:,None]*np.ones((1,W))
low=np.array([118,128,78]);north=np.array([84,104,70]);dry=np.array([150,140,92]);mcol=np.array([140,124,100]);snow=np.array([215,212,205])
c=low*(1-yy[...,None]*0)+0
c=low[None,None,:]*(1-np.clip((0.35-yy)*3,0,1))[...,None]+north[None,None,:]*np.clip((0.35-yy)*3,0,1)[...,None]
c=c*(1-np.clip((yy-0.75)*3,0,1))[...,None]+dry[None,None,:]*np.clip((yy-0.75)*3,0,1)[...,None]
c=c+(fb[...,None]-0.5)*28
c=c*(1-mtn[...,None]*0.8)+mcol[None,None,:]*mtn[...,None]*0.8
sn=np.clip((mtn-0.7)*1.6,0,0.35)[...,None]
c=c*(1-sn)+snow*sn
c=c*(0.72+0.56*shade[...,None])
# sea
dist=np.asarray(mask.filter(ImageFilter.GaussianBlur(40))).astype(np.float32)/255
sea=np.array([70,104,122])[None,None,:]*(1-dist[...,None]*0)+np.array([40,30,20])[None,None,:]*0
sea=np.array([62,94,112])[None,None,:]+np.array([40,38,30])[None,None,:]*dist[...,None]+(noise(80,20)[...,None]-0.5)*10
out=c*m[...,None]+sea*(1-m[...,None])
edge=np.asarray(mask.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.GaussianBlur(1.5))).astype(np.float32)/255
out=out*(1-np.clip(edge*2.5,0,0.6)[...,None])+np.array([200,205,190])*np.clip(edge*2.5,0,0.6)[...,None]*0.5
img=Image.fromarray(np.clip(out,0,255).astype(np.uint8))
# rivers
dr=ImageDraw.Draw(img)
rivers=[[(18.9,49.6),(19.9,50.05),(21.6,50.6),(21.8,51.5),(21.0,52.25),(19.5,52.6),(18.6,53.1),(18.8,54.3)],
[(33.5,55.9),(32.0,54.8),(30.4,54.0),(30.2,52.5),(30.5,51.3),(30.55,50.45),(31.5,49.6),(33.0,49.0),(34.8,48.3),(35.1,47.8),(34.2,47.0),(33.0,46.8),(32.2,46.5)],
[(23.0,49.3),(24.7,49.0),(26.5,48.5),(27.8,48.0),(28.8,47.2),(29.6,46.6),(30.2,46.2)],
[(32.8,56.7),(30.0,55.9),(27.3,55.8),(26.5,55.9),(25.0,56.6),(24.1,57.0)],
[(27.0,53.6),(25.8,53.5),(24.0,53.9),(23.8,54.5),(23.3,55.0),(22.0,55.1),(21.3,55.3)],
[(10,48.4),(12.1,48.7),(14.3,48.3),(16.4,48.2),(17.9,47.8),(18.9,47.8),(19.0,47.0),(18.9,45.8),(20.4,44.8),(22.6,44.6),(24.0,43.7),(26.0,43.9),(27.5,44.2),(28.1,45.3),(29.6,45.2)],
[(17.9,49.8),(17.0,51.1),(15.5,51.9),(14.6,52.5),(14.3,53.4)],
[(38.5,53.5),(39.2,52.0),(40.0,50.5),(41.5,49.5),(43,48.8),(41.5,47.6),(39.5,47.2)],
[(30.6,52.0),(28.0,52.1),(26.0,52.0),(24.5,51.9)],[(22.5,52.3),(21.2,52.6)],[(16.0,52.6),(17.5,52.3),(19.0,52.5)]]
for r in rivers:
    dr.line([toPx(*p) for p in r],fill=(78,112,130),width=7,joint='curve')
img=img.filter(ImageFilter.GaussianBlur(0.8))
img.save('site/assets/terrain.jpg',quality=88)
img.resize((800,900)).save('geo/terrain_small.jpg')
print('ok',W,H)
