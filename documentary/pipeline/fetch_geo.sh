#!/usr/bin/env bash
# Downloads Natural Earth 10m layers used by geom.py into assets/geo/
set -e; cd "$(dirname "$0")/../assets/geo"
B=https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson
for f in ne_10m_land ne_10m_rivers_lake_centerlines ne_10m_lakes; do curl -sSL -o $f.geojson $B/$f.geojson; done
# Elevation (Mapzen/AWS Terrain Tiles, terrarium encoding) is fetched and mosaicked by:
#   python3 pipeline/fetch_dem.py   (see maps2.py: assets/dem/mosaic.npy z6, world_z4.npy z4)
