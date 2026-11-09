"""Quick-look map: each park, its 5 km ring and the last 12 months of alerts."""
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
GPKG = ROOT / "data" / "processed" / "parks.gpkg"
OUT = ROOT / "data" / "processed" / "charts" / "alerts_map.png"
COLORS = {"nominal": "orange", "high": "red", "highest": "black"}


def main():
    parks = gpd.read_file(GPKG, layer="parks")
    rings = gpd.read_file(GPKG, layer="rings")
    alerts = gpd.read_file(GPKG, layer="alerts")

    fig, axes = plt.subplots(2, 2, figsize=(13, 13))
    for ax, name in zip(axes.flat, parks["NAME"]):
        rings[rings["NAME"] == name].boundary.plot(ax=ax, color="grey", linewidth=1)
        parks[parks["NAME"] == name].boundary.plot(ax=ax, color="green", linewidth=1.5)
        pts = alerts[alerts["zone"] == name]
        for conf, color in COLORS.items():
            sub = pts[pts["confidence"] == conf]
            if not sub.empty:
                sub.plot(ax=ax, color=color, markersize=2, label=f"{conf} ({len(sub):,})")
        ax.set_title(f"{name}: {len(pts):,} alerts")
        ax.legend(loc="lower left")
    fig.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=130)
    print(f"saved {OUT}")


if __name__ == "__main__":
    main()
