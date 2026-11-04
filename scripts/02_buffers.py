"""Step 2: build 5 km buffer rings (buffer minus park) around each park."""
from pathlib import Path

import geopandas as gpd

ROOT = Path(__file__).resolve().parent.parent
GPKG = ROOT / "data" / "processed" / "parks.gpkg"
BUFFER_M = 5000
EQUAL_AREA = 6933  # for areas only, never for buffering


def km2(geom):
    """Area of a lon/lat geometry in km2, measured in an equal-area CRS."""
    return gpd.GeoSeries([geom], crs=4326).to_crs(EQUAL_AREA).area.iloc[0] / 1e6


def main():
    parks = gpd.read_file(GPKG, layer="parks")

    rows = []
    for _, row in parks.iterrows():
        gs = gpd.GeoSeries([row.geometry], crs=4326)
        utm = gs.estimate_utm_crs()          # metric CRS suited to this park
        park_m = gs.to_crs(utm).iloc[0]
        ring_m = park_m.buffer(BUFFER_M).difference(park_m)
        ring = gpd.GeoSeries([ring_m], crs=utm).to_crs(4326).iloc[0]
        rows.append({"NAME": row["NAME"], "utm_epsg": utm.to_epsg(),
                     "park_km2": km2(row.geometry), "ring_km2": km2(ring),
                     "geometry": ring})

    rings = gpd.GeoDataFrame(rows, crs=4326)
    print(rings[["NAME", "utm_epsg", "park_km2", "ring_km2"]].to_string())

    print("\nOverlaps (km2):")
    for i, a in rings.iterrows():
        for j, b in parks.iterrows():
            if a["NAME"] != b["NAME"]:
                ov = km2(a.geometry.intersection(b.geometry))
                if ov > 0:
                    print(f"  ring of {a['NAME']} overlaps park {b['NAME']}: {ov:.2f}")
        for j, b in rings.iterrows():
            if i < j:
                ov = km2(a.geometry.intersection(b.geometry))
                if ov > 0:
                    print(f"  ring of {a['NAME']} overlaps ring of {b['NAME']}: {ov:.2f}")

    rings.to_file(GPKG, layer="rings", driver="GPKG")
    print(f"\nSaved layer 'rings' in {GPKG}")


if __name__ == "__main__":
    main()
