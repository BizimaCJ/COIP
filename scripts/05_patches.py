"""Step 5: join neighbouring alert pixels into patches; drop patches under 0.5 ha."""
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import box
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parent.parent
GPKG = ROOT / "data" / "processed" / "parks.gpkg"
MIN_HA = 0.5
HALF = 0.00005     # half the width of one 0.0001-degree alert pixel
JOIN = 0.000001    # tiny buffer so pixels touching only at a corner still join
EQUAL_AREA = 6933
RANK = {"nominal": 1, "high": 2, "highest": 3}


def patches_for_group(pts):
    """Merge the pixel squares of these alert points into patch polygons."""
    squares = [box(x - HALF, y - HALF, x + HALF, y + HALF).buffer(JOIN)
               for x, y in zip(pts.geometry.x, pts.geometry.y)]
    merged = unary_union(squares)
    parts = list(merged.geoms) if merged.geom_type == "MultiPolygon" else [merged]
    return gpd.GeoDataFrame(geometry=parts, crs=4326)


def main():
    alerts = gpd.read_file(GPKG, layer="alerts")
    alerts["date"] = pd.to_datetime(alerts["date"])

    out = []
    for (zone, kind), pts in alerts.groupby(["zone", "kind"]):
        patches = patches_for_group(pts)
        patches["area_ha"] = patches.to_crs(EQUAL_AREA).area / 1e4
        joined = gpd.sjoin(pts, patches, predicate="within")
        agg = joined.groupby("index_right").agg(
            n_pixels=("date", "size"),
            first_detected=("date", "min"),
            last_detected=("date", "max"),
            top_confidence=("confidence", lambda s: max(s, key=RANK.get)),
        )
        patches = patches.join(agg)
        patches["zone"], patches["kind"] = zone, kind
        out.append(patches)

    allp = pd.concat(out, ignore_index=True)
    allp["kept"] = allp["area_ha"] >= MIN_HA
    kept = allp[allp["kept"]].drop(columns="kept").reset_index(drop=True)
    kept.insert(0, "patch_id", range(1, len(kept) + 1))

    summary = (allp.assign(kept_ha=allp["area_ha"].where(allp["kept"], 0))
               .groupby(["zone", "kind"])
               .agg(patches=("kept", "size"), kept=("kept", "sum"),
                    kept_ha=("kept_ha", "sum"), all_ha=("area_ha", "sum")))
    print(summary.round(1))
    
    allp.to_file(GPKG, layer="patches_all", driver="GPKG")
    kept.to_file(GPKG, layer="patches", driver="GPKG")
    print(f"\nSaved {len(kept)} patches in layer 'patches' of {GPKG}")


if __name__ == "__main__":
    main()

