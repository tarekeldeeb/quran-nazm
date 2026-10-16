"""Shared paths for the Quran-Nazm scripts.

Set these environment variables (or accept the defaults):
  QMH        checkout of github.com/tarekeldeeb/quran-madina-html on its v2.0 branch
             (provides the 1441H/1405H layout data, the patched DigitalKhatt fonts
             and the HarfBuzz justifier in src/db/v2)
  SCAN_PDF   the King Fahd Complex Madina Mushaf PDF (archive.org item "quran-madinah"),
             only needed for the scan-measurement scripts (2x, 3x)
  NAZM_WORK  folder for generated intermediates (default: build/)
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.join(ROOT, "scripts")
DATA = os.path.join(ROOT, "data")
QMH = os.environ.get("QMH", os.path.join(os.path.dirname(ROOT), "quran-madina-html"))
SCAN_PDF = os.environ.get("SCAN_PDF", os.path.join(ROOT, "quran-madina.pdf"))
WORK = os.environ.get("NAZM_WORK", os.path.join(ROOT, "build"))
SCAN = os.path.join(WORK, "scan")
os.makedirs(WORK, exist_ok=True)
