import sys, csv, io, urllib.request
import ee
from PIL import Image, ImageDraw

ee.Initialize(project="coip-1410")
N = int(sys.argv[1]) if len(sys.argv) > 1 else 5
BEFORE = ("2025-08-15", "2025-10-31")
AFTER = ("2026-08-15", "2026-11-13")

def comp(pt, start, end):
    col = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
           .filterBounds(pt).filterDate(start, end)
           .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 40)))
    def mask(im):
        scl = im.select("SCL")
        bad = scl.eq(3).Or(scl.eq(8)).Or(scl.eq(9)).Or(scl.eq(10)).Or(scl.eq(11))
        return im.updateMask(bad.Not())
    return col.map(mask).median(), col.size().getInfo()

def thumbnail(img, region):
    url = img.visualize(bands=["B4", "B3", "B2"], min=0, max=3000).getThumbURL(
        {"region": region, "dimensions": 600, "format": "png"})
    return Image.open(io.BytesIO(urllib.request.urlopen(url).read())).convert("RGB")

import os
os.makedirs("data/processed/thumbnails", exist_ok=True)
rows = list(csv.DictReader(open("data/processed/accuracy_blind.csv")))[:N]
for r in rows:
    pt = ee.Geometry.Point([float(r["lon"]), float(r["lat"])])
    region = pt.buffer(300).bounds()
    try:
        b, nb = comp(pt, *BEFORE)
        a, na = comp(pt, *AFTER)
        ib, ia = thumbnail(b, region), thumbnail(a, region)
    except Exception as e:
        print(r["id"], "FAILED", str(e)[:80]); continue
    w, h = ib.size
    out = Image.new("RGB", (w * 2 + 10, h), "white")
    out.paste(ib, (0, 0)); out.paste(ia, (w + 10, 0))
    d = ImageDraw.Draw(out)
    for x0 in (0, w + 10):
        cx, cy = x0 + w // 2, h // 2
        d.ellipse([cx - 30, cy - 30, cx + 30, cy + 30], outline="yellow", width=2)
    d.text((5, 5), f"{r['id']} BEFORE n={nb}", fill="yellow")
    d.text((w + 15, 5), f"AFTER n={na}", fill="yellow")
    out.save(f"data/processed/thumbnails/{r['id']}.png")
    print(r["id"], "ok", nb, na)
