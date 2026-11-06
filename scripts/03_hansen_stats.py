"""Step 3: forest area in 2000 and forest loss per year, for each park and ring."""
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.mask import mask
from shapely.geometry import box

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
GPKG = DATA / "processed" / "parks.gpkg"
OUT = DATA / "processed" / "loss_by_year.csv"
VERSION = "GFC-2025-v1.13"

TILES = ["00N_020E", "00N_030E"]
CANOPY_MIN = 30   # % canopy cover that counts as forest in 2000
R = 6371008.8     # mean Earth radius in metres


def tile_path(layer, tile):
    return DATA / f"Hansen_{VERSION}_{layer}_{tile}.tif"


def find_tile(geom):
    """Name of the tile that fully contains this geometry, or None."""
    for tile in TILES:
        with rasterio.open(tile_path("treecover2000", tile)) as src:
            if box(*src.bounds).contains(geom):
                return tile
    return None


def row_areas_ha(transform, n_rows):
    """True area (ha) of one pixel in each raster row; it shrinks with latitude."""
    dlon = np.radians(transform.a)
    lat_top = transform.f + np.arange(n_rows) * transform.e
    lat_bot = lat_top + transform.e
    return R**2 * dlon * (np.sin(np.radians(lat_top)) - np.sin(np.radians(lat_bot))) / 1e4


def zone_stats(geom, tc_src, loss_src):
    shapes = [geom.__geo_interface__]
    tc, tf = mask(tc_src, shapes, crop=True, filled=False)
    loss, _ = mask(loss_src, shapes, crop=True, filled=False)
    tc, loss = tc[0], loss[0]
    inside = ~np.ma.getmaskarray(tc)
    forest = inside & (tc.data >= CANOPY_MIN)
    area = row_areas_ha(tf, tc.shape[0])

    stats = {"forest_2000_ha": (forest.sum(axis=1) * area).sum()}
    for code in range(1, 26):  # lossyear 1..25 means 2001..2025
        hit = forest & (loss.data == code)
        stats[2000 + code] = (hit.sum(axis=1) * area).sum()
    return stats


def main():
    parks = gpd.read_file(GPKG, layer="parks").assign(kind="park")
    rings = gpd.read_file(GPKG, layer="rings").assign(kind="ring")
    zones = pd.concat([parks, rings], ignore_index=True)

    rows = []

    for _, z in zones.iterrows():
        tile = find_tile(z.geometry)
        if tile is None:
            print(f"skip {z['NAME']} ({z['kind']}): not inside any single tile")
            continue
        print(f"working on {z['NAME']} ({z['kind']}) in tile {tile} ...")
        with rasterio.open(tile_path("treecover2000", tile)) as tc_src, \
             rasterio.open(tile_path("lossyear", tile)) as loss_src:
            rows.append({"zone": z["NAME"], "kind": z["kind"],
                         **zone_stats(z.geometry, tc_src, loss_src)})

    df = pd.DataFrame(rows)
    years = list(range(2001, 2026))
    df["loss_total_ha"] = df[years].sum(axis=1)
    df["loss_pct"] = 100 * df["loss_total_ha"] / df["forest_2000_ha"]
    df.to_csv(OUT, index=False)
    print(df[["zone", "kind", "forest_2000_ha", "loss_total_ha", "loss_pct"]]
          .round(1).to_string())
    print(f"\nSaved {OUT}")


if __name__ == "__main__":
    main()

