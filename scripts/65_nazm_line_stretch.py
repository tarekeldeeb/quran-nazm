"""Per-line stretch of the Quran-Nazm layout, for the paper's comparison figure.

    python scripts/65_nazm_line_stretch.py      # writes data/nazm_line_stretch.json

Stretch of a line = common line width / natural width of its words.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import DATA

import render_mushaf as R

txt = R.Text()
book, W, _ = R.build_layout(txt, 0.25)
pages = [dict(page=i, hizb=p["hizb"], stretch=[round(W / r[2], 4) for r in p["rows"] if r[0] == "text"])
         for i, p in enumerate(book, 1)]
json.dump(dict(line_width=W, pages=pages), open(os.path.join(DATA, "nazm_line_stretch.json"), "w"))
print(f"{len(pages)} pages written")
