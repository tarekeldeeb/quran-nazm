"""Quran-Nazm research script. Paths come from paths.py (QMH, SCAN_PDF, NAZM_WORK)."""
import sys,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from paths import *
import json,collections,re
def load(layout):
    d=json.load(open(fQMH+'/assets/db/v2/Madina-{layout}.json'))
    txt=collections.defaultdict(list)
    for si,s in enumerate(d['suras']):
        for ai,a in enumerate(s['ayas']):
            for r in a['r']:
                txt[(a['p'],r['l'])].append((r['t'].strip(),ai))
    return d,txt
