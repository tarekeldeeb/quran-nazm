"""Quran-Nazm research script. Paths come from paths.py (QMH, SCAN_PDF, NAZM_WORK)."""
import sys,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from paths import *
import numpy as np
exec(open(HERE+'/43_hizb_free_breaks.py').read().split('res={}')[0])
for shrink in (0.0,0.10):
  print(f'--- max shrink {shrink*100:.0f}%')
  for pages in (8,10):
    G=[];L=[]
    for h in range(58):
        ws=[w for r in range(4*h,4*h+4) for _,w in U[r]];heads=[s for r in range(4*h,4*h+4) for s in R[r]['heads']]
        G.append(ws);L.append(pages*15-hdr(heads,'B'))
    Wr=np.array([minmax(g,l) for g,l in zip(G,L)]);Wcap=Wr.max();W=Wcap*(1-shrink)
    st=[];pg=[];hz=[]
    for g,l in zip(G,L):
        s=W/even_break(g,l,Wcap);st+=list(s);hz.append(s.mean())
        for p in range(0,len(s),15): pg.append(np.std(s[p:p+15]))
    st=np.array(st);hz=np.array(hz);dev=np.abs(st-1)
    print(f"{pages}p: type {LW/W*100:.0f}% of Madina | median {np.median(st):.2f} p5 {np.percentile(st,5):.2f} p95 {np.percentile(st,95):.2f} max {st.max():.2f} | shrunk lines {(st<1).mean()*100:.0f}% | within 0.95-1.19 {( (st>=0.95)&(st<=1.19)).mean()*100:.0f}% | >1.30 {(st>1.3).mean()*100:.0f}% >1.50 {(st>1.5).mean()*100:.1f}% | hizb avg {hz.min():.2f}-{hz.max():.2f} | page sd {np.median(pg):.3f} | median |deviation| {np.median(dev):.2f}")
