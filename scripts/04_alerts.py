"""Step 4: last 12 months of GFW integrated alerts for each park and ring."""
import os
import time
from datetime import date, timedelta
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
GPKG = ROOT / "data" / "processed" / "parks.gpkg"
URL = "https://data-api.globalforestwatch.org/dataset/gfw_integrated_alerts/latest/query/json"
SIMPLIFY_DEG = 0.001  # about 100 m; smooths the outline we SEND to keep requests small
SINCE = (date.today() - timedelta(days=365)).isoformat()

load_dotenv(ROOT / ".env")
HEADERS = {"x-api-key": os.environ["GFW_API_KEY"], "Origin": "localhost"}


def fetch_alerts(geom):
    """Ask the API for every alert pixel inside (a slightly simplified) geom."""
    sql = ("SELECT longitude, latitude, gfw_integrated_alerts__date, "
           "gfw_integrated_alerts__confidence FROM results "
           f"WHERE gfw_integrated_alerts__date >= '{SINCE}'")
    sent = geom.simplify(SIMPLIFY_DEG).buffer(SIMPLIFY_DEG, quad_segs=1)
    r = requests.post(URL, json={"sql": sql, "geometry": sent.__geo_interface__},
                      headers=HEADERS, timeout=300)
    r.raise_for_status()
    return pd.DataFrame(r.json()["data"])


def main():
    parks = gpd.read_file(GPKG, layer="parks").assign(kind="park")
    rings = gpd.read_file(GPKG, layer="rings").assign(kind="ring")
    zones = pd.concat([parks, rings], ignore_index=True)

    parts = []
    for _, z in zones.iterrows():
        print(f"fetching {z['NAME']} ({z['kind']}) since {SINCE} ...")
        df = fetch_alerts(z.geometry)
        if df.empty:
            print("  0 alerts")
            continue
        pts = gpd.GeoDataFrame(
            df, geometry=gpd.points_from_xy(df["longitude"], df["latitude"]), crs=4326)
        pts = pts[pts.within(z.geometry)].copy()
        pts["zone"], pts["kind"] = z["NAME"], z["kind"]
        print(f"  {len(df)} returned, {len(pts)} inside the real boundary")
        parts.append(pts)
        time.sleep(1)

    alerts = gpd.GeoDataFrame(pd.concat(parts, ignore_index=True), crs=4326)
    alerts = alerts.rename(columns={"gfw_integrated_alerts__date": "date",
                                    "gfw_integrated_alerts__confidence": "confidence"})
    alerts = alerts[["zone", "kind", "date", "confidence", "geometry"]]
    alerts.to_file(GPKG, layer="alerts", driver="GPKG")
    print(alerts.groupby(["zone", "kind", "confidence"]).size().unstack(fill_value=0))
    print(f"\nSaved layer 'alerts' in {GPKG}")


if __name__ == "__main__":
    main()

