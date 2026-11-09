"""Yearly forest loss bar charts: one image per park, park panel and ring panel."""
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "data" / "processed" / "loss_by_year.csv"
OUT = ROOT / "data" / "processed" / "charts"
YEARS = [str(y) for y in range(2001, 2026)]  # CSV column names are text


def main():
    df = pd.read_csv(CSV)
    OUT.mkdir(parents=True, exist_ok=True)

    for name in df["zone"].unique():
        fig, axes = plt.subplots(1, 2, figsize=(12, 3.8))
        for ax, kind in zip(axes, ["park", "ring"]):
            row = df[(df["zone"] == name) & (df["kind"] == kind)].iloc[0]
            ax.bar(YEARS, row[YEARS].astype(float))
            ax.set_title(f"{name} {kind}")
            ax.set_ylabel("Forest loss (ha)")
            ax.set_xticks(YEARS[::2])
            ax.tick_params(axis="x", rotation=90)
        fig.tight_layout()
        fig.savefig(OUT / f"{name}_loss.png", dpi=150)
        plt.close(fig)
        print(f"saved {name}_loss.png")


if __name__ == "__main__":
    main()
