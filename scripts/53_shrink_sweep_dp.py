"""Quran-Nazm research script. Paths come from paths.py (QMH, SCAN_PDF, NAZM_WORK)."""
import sys,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from paths import *
import numpy as np,math
exec(open(HERE+'/51_ayah_pages_dp.py').read().split("if __name__")[0])
P=10
lo,hi=8000,60000
for _ in range(22):
    mid=(lo+hi)/2
    if all(z.feasible(mid,P) for z in HZ): hi=mid
    else: lo=mid
Wc=hi
for sh in (0.10,0.125,0.15,0.175,0.20,0.25):
    W=Wc*(1-sh);st=[];pa=[]
    for z in HZ:
        b=z.best_partition(Wc,W,P)
        for j,i in zip(b[:-1],b[1:]):
            units=[u for a in z.A[j:i] for u in a['u']];L=15-sum(z.hdr[j:i]);ws=[w for _,w in units]
            br=even_break(ws,L,Wc);cum=np.concatenate([[0],np.cumsum(np.array(ws)+SP)])
            s=W/np.array([cum[e]-cum[s_]-SP for s_,e in zip(br[:-1],br[1:])]);st+=list(s);pa.append(s.mean())
    st=np.array(st);pa=np.array(pa);c=1-st
    print(f"shrink {sh*100:4.1f}%: type {LW/W*100:.0f}% | median {np.median(st):.2f} p95 {np.percentile(st,95):.2f} | 0.95-1.19 {((st>=.95)&(st<=1.19)).mean()*100:.0f}% | >1.3 {(st>1.3).mean()*100:.0f}% >1.5 {(st>1.5).mean()*100:.1f}% | shrunk {(st<1).mean()*100:.0f}% >5% {(c>.05).mean()*100:.0f}% >10% {(c>.10).mean()*100:.1f}% >15% {(c>.15).mean()*100:.1f}% | sparsest page {pa.max():.2f}")
