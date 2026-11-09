"""Step 6: ranking metrics for each protected area."""
from pathlib import Path

import geopandas as gpd
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "data" / "processed" / "loss_by_year.csv"
GPKG = ROOT / "data" / "processed" / "parks.gpkg"
OUT = ROOT / "data" / "processed" / "ranking.csv"
RECENT = [str(y) for y in range(2023, 2026)]    # the last 3 years
PREVIOUS = [str(y) for y in range(2013, 2023)]  # the 10 years before
ACTIVE_DAYS = 90                                # "active" = detected in last 90 days


def main():
    loss = pd.read_csv(CSV)
    patches = gpd.read_file(GPKG, layer="patches_all")
    patches["last_detected"] = pd.to_datetime(patches["last_detected"])
    patches["kept"] = patches["kept"].astype(bool)
    cutoff = patches["last_detected"].max() - pd.Timedelta(days=ACTIVE_DAYS)

    rows = []
    for name in loss["zone"].unique():
        row = {"area": name}
        for kind in ["park", "ring"]:
            r = loss[(loss["zone"] == name) & (loss["kind"] == kind)].iloc[0]
            f2000 = r["forest_2000_ha"]
            recent = r[RECENT].astype(float).mean()
            prev = r[PREVIOUS].astype(float).mean()
            row[f"{kind}_recent_ha_yr"] = recent
            row[f"{kind}_prev_ha_yr"] = prev
            
            
            row[f"{kind}_trend"] = recent / prev
            row[f"{kind}_recent_pct_yr"] = 100 * recent / f2000
            row[f"{kind}_loss_3y_ha"] = r[RECENT].astype(float).sum()
            p = patches[(patches["zone"] == name) & (patches["kind"] == kind)]
            row[f"{kind}_alert_ha_12m"] = p["area_ha"].sum()
            row[f"{kind}_hotspots"] = int((p["kept"] & (p["last_detected"] >= cutoff)).sum())
        total = row["park_loss_3y_ha"] + row["ring_loss_3y_ha"]
        row["inside_share_pct"] = 100 * row["park_loss_3y_ha"] / total
        rows.append(row)

    df = pd.DataFrame(rows)
    df = df.sort_values("park_recent_ha_yr", ascending=False).reset_index(drop=True)
    df.insert(0, "rank", df.index + 1)
    df.to_csv(OUT, index=False)
    print(df.set_index("area").T.round(2).to_string())
    print(f"\nSaved {OUT}")


if __name__ == "__main__":
    main()

