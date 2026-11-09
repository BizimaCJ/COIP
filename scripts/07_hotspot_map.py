import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

F = "data/processed/parks.gpkg"
parks = gpd.read_file(F, layer="parks")
rings = gpd.read_file(F, layer="rings")
patches = gpd.read_file(F, layer="patches")

# hotspot = last detected within 90 days of the newest detection in the data
patches["last_detected"] = pd.to_datetime(patches["last_detected"])
ref = patches["last_detected"].max()
patches["hotspot"] = patches["last_detected"] >= ref - pd.Timedelta(days=90)
print("reference date:", ref.date())

# size bands, same as case severity
labels = ["< 1 ha", "1-5 ha", "5-20 ha", "> 20 ha"]
colors = ["#fee08b", "#fdae61", "#f46d43", "#a50026"]
sizes = [30, 60, 110, 180]
patches["band"] = pd.cut(
    patches["area_ha"], bins=[0, 1, 5, 20, float("inf")],
    labels=labels, right=False,
)

for name in parks["NAME"]:
    epsg = int(rings.loc[rings["NAME"] == name, "utm_epsg"].iloc[0])
    park = parks[parks["NAME"] == name].to_crs(epsg)
    ring = rings[rings["NAME"] == name].to_crs(epsg)
    pt = patches[patches["zone"] == name].to_crs(epsg).copy()
    pt["geometry"] = pt.geometry.centroid

    fig, ax = plt.subplots(figsize=(8, 8))
    ring.boundary.plot(ax=ax, color="grey", linewidth=1, linestyle="--")
    park.boundary.plot(ax=ax, color="darkgreen", linewidth=1.5)

    for lab, col, s in zip(labels, colors, sizes):
        sub = pt[pt["band"] == lab]
        if len(sub) == 0:
            continue
        hot = sub[sub["hotspot"]]
        old = sub[~sub["hotspot"]]
        ax.scatter(old.geometry.x, old.geometry.y, s=s, c=col,
                   edgecolors="none", alpha=0.9)
        ax.scatter(hot.geometry.x, hot.geometry.y, s=s, c=col,
                   edgecolors="black", linewidths=1.8, alpha=0.9)

    handles = [Line2D([], [], marker="o", ls="", color=c, markersize=8, label=l)
               for l, c in zip(labels, colors)]
    handles += [
        Line2D([], [], marker="o", ls="", mfc="white", mec="black",
               mew=1.8, markersize=8, label="hotspot (last 90 days)"),
        Line2D([], [], color="darkgreen", lw=1.5, label="park boundary"),
        Line2D([], [], color="grey", lw=1, ls="--", label="5 km ring"),
    ]
    ax.legend(handles=handles, loc="upper left", fontsize=8, framealpha=0.9)
    ax.set_aspect("equal")
    ax.set_xlabel(f"Easting (m, EPSG:{epsg})")
    ax.set_ylabel("Northing (m)")
    ax.set_title(f"{name}: kept alert patches (>= 0.5 ha), n={len(pt)}, "
                 f"hotspots={int(pt['hotspot'].sum())}")

    out = f"data/processed/hotspot_{name}.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(name, len(pt), "patches ->", out)
