"""Step 1: merge WDPA polygon parts, keep Rwanda's national parks,
check our area calculation against WDPA's, save for later steps."""
from pathlib import Path

import geopandas as gpd
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
WDPA_DIR = ROOT / "data" / "WDPA"
OUT = ROOT / "data" / "processed" / "parks.gpkg"
UTM_35S = 32735  # metric CRS for western Rwanda; used only for measuring


def load_wdpa():
    files = sorted(WDPA_DIR.glob("*/*-polygons.shp"))
    wdpa = pd.concat([gpd.read_file(f) for f in files], ignore_index=True)
    return gpd.GeoDataFrame(wdpa, crs="EPSG:4326")


def main():
    wdpa = load_wdpa()
    print("All records:")
    print(wdpa[["NAME", "DESIG_ENG", "STATUS", "GIS_AREA"]].to_string())

    parks = wdpa[wdpa["DESIG_ENG"] == "National Park"].copy()
    print(f"\nKept {len(parks)} national parks: {parks['NAME'].tolist()}")

    parks["my_km2"] = parks.to_crs(epsg=UTM_35S).geometry.area / 1e6
    
    parks["ea_km2"] = parks.to_crs(epsg=6933).geometry.area / 1e6
    print(parks[["NAME", "GIS_AREA", "my_km2", "ea_km2"]].to_string())
    print("Valid geometries:", parks.geometry.is_valid.tolist())

    OUT.parent.mkdir(parents=True, exist_ok=True)
    parks[["NAME", "GIS_AREA", "geometry"]].to_file(OUT, layer="parks", driver="GPKG")
    print(f"\nSaved {OUT}")


if __name__ == "__main__":
    main()
