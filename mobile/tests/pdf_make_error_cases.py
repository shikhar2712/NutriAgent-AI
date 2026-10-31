"""Builds an encrypted PDF and an image-only (scanned-style) PDF for the UI error-path tests."""
import io, pathlib, sys
from PIL import Image, ImageDraw
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

out = pathlib.Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
src = pathlib.Path(__file__).resolve().parents[2] / "sample_blood_test_report.pdf"
w = PdfWriter()
for pg in PdfReader(str(src)).pages: w.add_page(pg)
w.encrypt("secret"); w.write(str(out / "encrypted.pdf"))

im = Image.new("RGB", (600, 800), "white"); d = ImageDraw.Draw(im)
for i in range(30): d.rectangle([40, 40 + i * 24, 560 - (i * 7) % 200, 52 + i * 24], fill=(60, 60, 60))   # fake scanned text lines
buf = io.BytesIO(); im.save(buf, "PNG"); buf.seek(0)
c = canvas.Canvas(str(out / "scanned.pdf"), pagesize=(600, 800)); c.drawImage(ImageReader(buf), 0, 0, 600, 800); c.save()
print("wrote", out)
