"""Generates legacy launcher PNGs (API 24-25). Adaptive icon for 26+ is the vector in res/drawable."""
import os, sys
from PIL import Image, ImageDraw

out = sys.argv[1]
sizes = {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}
for dens, px in sizes.items():
    S = 4 * px
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, S - 1, S - 1], radius=S // 5, fill="#0F172A")
    k = S / 108.0
    # leaf
    d.ellipse([34 * k, 28 * k, 80 * k, 72 * k], fill="#34D399")
    d.line([42 * k, 64 * k, 68 * k, 40 * k], fill="#0F172A", width=int(3 * k))
    # cross
    for box in ([50, 72, 58, 92], [44, 78, 64, 86]):
        d.rectangle([c * k for c in box], fill="#38BDF8")
    im = im.resize((px, px), Image.LANCZOS)
    p = os.path.join(out, "mipmap-%s" % dens)
    os.makedirs(p, exist_ok=True)
    im.save(os.path.join(p, "ic_launcher.png"))
