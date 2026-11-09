import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
import shapely
from pyproj import Transformer

SEED = 42
F = "data/processed/parks.gpkg"
TC = {
    20: "data/Hansen_GFC-2025-v1.13_treecover2000_00N_020E.tif",
    30: "data/Hansen_GFC-2025-v1.13_treecover2000_00N_030E.tif",
}
rng = np.random.default_rng(SEED)

parks = gpd.read_file(F, layer="parks")
rings = gpd.read_file(F, layer="rings")
allp = gpd.read_file(F, layer="patches_all")
srcs = {k: rasterio.open(p) for k, p in TC.items()}


def canopy(lon, lat):
    lon, lat = np.asarray(lon), np.asarray(lat)
    out = np.zeros(len(lon))
    for key, src in srcs.items():
        m = (lon >= key) & (lon < key + 10)
        if m.any():
            out[m] = [v[0] for v in src.sample(zip(lon[m], lat[m]))]
    return out


# 1. patches, stratified by size
names = ["< 0.1 ha", "0.1-0.5 ha", ">= 0.5 ha"]
allp["stratum"] = pd.cut(allp["area_ha"], bins=[0, 0.1, 0.5, np.inf],
                         labels=names, right=False)
quota = {">= 0.5 ha": 17, "0.1-0.5 ha": 17, "< 0.1 ha": 16}
sel = pd.concat([
    allp[allp["stratum"] == s].sample(n=min(n, (allp["stratum"] == s).sum()),
                                      random_state=SEED)
    for s, n in quota.items()
])
sel = gpd.GeoDataFrame(sel, crs=allp.crs)
pts = sel.geometry.representative_point()
patch_rows = pd.DataFrame({
    "sample_type": "patch",
    "stratum": sel["stratum"].astype(str).values,
    "zone": sel["zone"].values,
    "kind": sel["kind"].values,
    "candidate_row": sel.index.values,
    "area_ha": sel["area_ha"].round(3).values,
    "lon": pts.x.values,
    "lat": pts.y.values,
})

# 2. no-change points: forest in 2000, >100 m from any candidate patch
per_zone = {"Akagera": 13, "Gishwati-Mukura": 13, "Nyungwe": 12, "Volcans": 12}
nc_rows = []
for name, n in per_zone.items():
    epsg = int(rings.loc[rings["NAME"] == name, "utm_epsg"].iloc[0])
    zone = shapely.union_all([
        parks[parks["NAME"] == name].to_crs(epsg).union_all(),
        rings[rings["NAME"] == name].to_crs(epsg).union_all(),
    ])
    near = allp.to_crs(epsg).union_all().buffer(100)
    to_ll = Transformer.from_crs(epsg, 4326, always_xy=True)
    minx, miny, maxx, maxy = zone.bounds
    got, tries = [], 0
    while len(got) < n and tries < 200:
        tries += 1
        x = rng.uniform(minx, maxx, 2000)
        y = rng.uniform(miny, maxy, 2000)
        ok = shapely.contains_xy(zone, x, y) & ~shapely.contains_xy(near, x, y)
        lon, lat = to_ll.transform(x[ok], y[ok])
        lon, lat = np.asarray(lon), np.asarray(lat)
        f = canopy(lon, lat) >= 30
        got += list(zip(lon[f], lat[f]))
    got = got[:n]
    if len(got) < n:
        print(f"WARNING {name}: only {len(got)} of {n} points found")
    for lo, la in got:
        nc_rows.append({"sample_type": "no_change", "stratum": "no_change",
                        "zone": name, "kind": None, "candidate_row": None,
                        "area_ha": None, "lon": lo, "lat": la})

# 3. shuffle, blind IDs, write
key = pd.concat([patch_rows, pd.DataFrame(nc_rows)], ignore_index=True)
key = key.sample(frac=1, random_state=SEED).reset_index(drop=True)
key.insert(0, "id", [f"A{i + 1:03d}" for i in range(len(key))])
key["lon"] = key["lon"].round(6)
key["lat"] = key["lat"].round(6)

blind = key[["id", "lon", "lat"]].copy()
for c in ["verdict", "before_date", "after_date", "notes"]:
    blind[c] = ""

key.to_csv("data/processed/accuracy_key.csv", index=False)
blind.to_csv("data/processed/accuracy_blind.csv", index=False)
gpd.GeoDataFrame(blind[["id"]],
                 geometry=gpd.points_from_xy(blind["lon"], blind["lat"]),
                 crs=4326).to_file("data/processed/accuracy_blind.gpkg",
                                   layer="points", driver="GPKG")
print(key.groupby(["sample_type", "stratum"]).size())
print("total:", len(key))

