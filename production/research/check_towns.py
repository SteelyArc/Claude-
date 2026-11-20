import json, numpy as np, sys
sys.path.insert(0,'tools')
from georef_overlay import proj
from PIL import Image
from shapely.geometry import shape, Point
rump=shape(json.load(open('data/geo/2692510.geojson'))['geometry'])
im=Image.open('research/diagnostics/ref_rozbiory3.png').convert('RGB')
# documented year each town left the Commonwealth (Russian partition)
T={'Minsk':(27.56,53.90,1793),'Pinsk':(26.10,52.11,1793),'Slutsk':(27.55,53.03,1793),'Nesvizh':(26.67,53.22,1793),'Mir':(26.47,53.45,1793),
   'Barysaw':(28.50,54.23,1793),'Rivne':(26.25,50.62,1793),'Ostroh':(26.52,50.33,1793),'Zhytomyr':(28.66,50.25,1793),'Kamianets-Podilskyi':(26.58,48.68,1793),
   'Starokostiantyniv':(27.21,49.76,1793),'Iziaslav':(26.80,50.12,1793),
   'Vilnius':(25.28,54.69,1795),'Hrodna':(23.83,53.68,1795),'Navahrudak':(25.82,53.60,1795),'Brest':(23.69,52.10,1795),'Lutsk':(25.32,50.75,1795),
   'Kremenets':(25.71,50.10,1795),'Kovel':(24.71,51.21,1795),'Dubno':(25.73,50.42,1795),'Lida':(25.30,53.89,1795),'Kobryn':(24.36,52.21,1795),
   'Ashmyany':(25.94,54.43,1795),'Vileyka':(26.92,54.49,1795),'Braslaw':(27.03,55.64,1795),'Druja':(27.45,55.79,1795)}
for n,(lo,la,yr) in T.items():
    ohm = 'rump' if rump.contains(Point(lo,la)) else 'RUSSIA'
    x,y=proj([[lo,la]])[0];
    c=max(im.crop((int(x)-4,int(y)-4,int(x)+5,int(y)+5)).getcolors(200))[1]
    ref='1795-pink' if abs(c[0]-230)<12 and abs(c[1]-183)<14 else ('1793-grey' if abs(c[0]-200)<12 and abs(c[1]-170)<14 else str(c))
    exp='rump' if yr==1795 else 'RUSSIA'
    print(f"{n:20s} documented:{yr}  OHM:{ohm:7s}{'  ' if ohm==exp else ' X'}  ref:{ref}")
