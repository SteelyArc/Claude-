import fs from 'fs';
import {geoMercator, geoPath} from 'd3-geo';
import {feature} from 'topojson-client';
const topo=JSON.parse(fs.readFileSync('node_modules/world-atlas/countries-10m.json'));
const all=feature(topo,topo.objects.countries).features;
const byId=id=>all.find(f=>+f.id===id);
const vn=byId(704);
const W=900,H=1500;
const proj=geoMercator().fitExtent([[40,40],[W-40,H-40]],vn);
const path=geoPath(proj);
const out={W,H,vn:path(vn),neighbors:{}};
for(const [k,id] of Object.entries({china:156,laos:418,cambodia:116,thailand:764})) out.neighbors[k]=path(byId(id));
const pts={hanoi:[105.85,21.03],saigon:[106.70,10.78],dbp:[103.02,21.39],hue:[107.59,16.46],danang:[108.2,16.05],pacbo:[106.05,22.98],tonkin:[107.3,19.6]};
out.pts={};for(const [k,v] of Object.entries(pts)) out.pts[k]=proj(v).map(n=>+n.toFixed(1));
// 17th parallel across the map
out.p17=[proj([100,17])[1]].map(n=>+n.toFixed(1))[0];
// wider indochina view
const indo={type:'FeatureCollection',features:[vn,byId(418),byId(116)]};
const proj2=geoMercator().fitExtent([[40,40],[1400-40,1500-40]],indo);const p2=geoPath(proj2);
out.indo={W:1400,H:1500,vn:p2(vn),laos:p2(byId(418)),cambodia:p2(byId(116)),china:p2(byId(156)),thailand:p2(byId(764))};
fs.writeFileSync('map.json',JSON.stringify(out));
console.log(Object.keys(out), out.pts, out.p17, out.vn.length);
