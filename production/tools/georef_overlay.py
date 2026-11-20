"""Georeference a reference raster via city control points (2nd-order polynomial) and overlay OHM borders."""
import json, sys, numpy as np
from PIL import Image, ImageDraw
from shapely.geometry import shape
CP = {  # pixel (x,y) on Rzeczpospolita_Rozbiory_3.png : (lon,lat)
 'Krakow':((403,1225),(19.94,50.06)),'Warsaw':((500,962),(21.01,52.23)),'Wilno':((846,648),(25.28,54.69)),
 'Lwow':((747,1278),(24.03,49.84)),'Kijow':((1269,1170),(30.52,50.45)),'Ryga':((749,352),(24.10,56.95)),
 'Poznan':((179,911),(16.93,52.41)),'Gdansk':((330,683),(18.65,54.35)),'Smolensk':((1343,609),(32.05,54.78)),
 'Kamieniec':((962,1413),(26.58,48.68)),'Minsk':((1017,739),(27.56,53.90)),'Krolewiec':((486,644),(20.51,54.71)),
 'Lublin':((625,1088),(22.57,51.25)),'Breslau':((178,1086),(17.04,51.11)),'Pskov':((1043,224),(28.33,57.82)),
 'Polock':((1096,525),(28.80,55.49)),'Witebsk':((1205,560),(30.20,55.19)),'Zytomierz':((1126,1205),(28.66,50.25)),
 'Brzesc':((717,977),(23.69,52.10)),'Luck':((853,1150),(25.33,50.75)),'Torun':((324,841),(18.60,53.01)),'Vienna':((86,1447),(16.37,48.21))}
def feats(lon,lat):
    lon,lat=np.asarray(lon),np.asarray(lat); return np.stack([np.ones_like(lon),lon,lat,lon*lon,lon*lat,lat*lat],-1)
L=np.array([v[1] for v in CP.values()]); P=np.array([v[0] for v in CP.values()],float)
coef,*_=np.linalg.lstsq(feats(L[:,0],L[:,1]),P,rcond=None)
res=feats(L[:,0],L[:,1])@coef-P; print('control-point RMS error px:',np.sqrt((res**2).sum(1).mean()).round(2),' max',np.abs(res).max().round(1))
def proj(c): c=np.asarray(c); return feats(c[:,0],c[:,1])@coef
if __name__=='__main__':
    im=Image.open('research/diagnostics/ref_rozbiory3.png').convert('RGB'); d=ImageDraw.Draw(im)
    for rid,col in [(int(a.split(':')[0]),a.split(':')[1]) for a in sys.argv[2:]]:
        g=shape(json.load(open(f'data/geo/{rid}.geojson'))['geometry'])
        for p in getattr(g,'geoms',[g]):
            for ring in [p.exterior,*p.interiors]:
                d.line([tuple(x) for x in proj(ring.coords)],fill=col,width=3)
    for k,((x,y),_) in CP.items(): d.ellipse([x-4,y-4,x+4,y+4],outline='black')
    im.save(sys.argv[1]); print('saved',sys.argv[1])
