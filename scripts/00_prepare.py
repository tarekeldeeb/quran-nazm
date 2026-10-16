"""Prepare inputs for the other scripts.

1. Decompress the patched DigitalKhatt fonts shipped with quran-madina-html v2
   (WOFF2) into plain OpenType files that HarfBuzz can load.
2. If the King Fahd Complex PDF is present, extract its page images
   (720 x 1123 px each) for the scan-measurement scripts.

    python scripts/00_prepare.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import QMH, SCAN, SCAN_PDF, WORK

from fontTools.ttLib import TTFont

for name in ("madina", "oldmadina"):
    src = os.path.join(QMH, "assets", "db", "v2", f"{name}-qmh.woff2")
    font = TTFont(src)
    font.flavor = None
    font.save(os.path.join(WORK, f"{name}.otf"))
    print("font:", name)

amiri = TTFont(os.path.join(QMH, "assets", "fonts", "AmiriQuran.woff2"))
amiri.flavor = None
amiri.save(os.path.join(WORK, "amiri.ttf"))  # running heads and page numbers
print("font: amiri")

if os.path.exists(SCAN_PDF):
    import pymupdf
    os.makedirs(SCAN, exist_ok=True)
    doc = pymupdf.open(SCAN_PDF)
    for i in range(doc.page_count):
        xref = doc[i].get_images()[0][0]
        pix = pymupdf.Pixmap(doc, xref)
        if pix.n > 3:
            pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
        pix.save(os.path.join(SCAN, f"{i:03d}.png"))  # file index = Mushaf page number
    print("scan pages:", doc.page_count)
else:
    print("scan PDF not found; skipping page extraction (only needed for scripts 2x/3x)")
