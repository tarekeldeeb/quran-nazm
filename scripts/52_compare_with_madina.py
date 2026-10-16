"""Quran-Nazm research script. Paths come from paths.py (QMH, SCAN_PDF, NAZM_WORK)."""
import sys,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from paths import *
import json,numpy as np
exec(open(HERE+'/51_ayah_pages_dp.py').read().split("if __name__")[0])
def metrics(pages):
    s=np.concatenate([np.array(p) for p in pages]);ls=np.log(s)
    within=[np.std(p) for p in pages if len(p)>=10]
    jumps=np.concatenate([np.abs(np.diff(p)) for p in pages])
    return dict(med=np.median(s),p5=np.percentile(s,5),p95=np.percentile(s,95),sd=np.std(ls),
        b5=(np.abs(s-np.median(s))<=0.05*np.median(s)).mean(),b10=(np.abs(s-np.median(s))<=0.10*np.median(s)).mean(),
        within=np.median(within),jump=np.median(jumps),jump95=np.percentile(jumps,95))
m=[o for o in json.load(open(WORK+'/m_1441H.json')) if o['full']];by={}
for o in m: by.setdefault(o['p'],[]).append(o)
mad=[[1/o['ratio'] for o in sorted(v,key=lambda o:o['l'])] for v in by.values()]
rows=[('Madina 1441H',1.00,metrics(mad))]
P=10;lo,hi=8000,60000
for _ in range(22):
    mid=(lo+hi)/2
    if all(z.feasible(mid,P) for z in HZ): hi=mid
    else: lo=mid
Wc=hi
for sh in (0.10,0.15,0.20,0.25):
    W=Wc*(1-sh);pages=[]
    for z in HZ:
        b=z.best_partition(Wc,W,P)
        for j,i in zip(b[:-1],b[1:]):
            units=[u for a in z.A[j:i] for u in a['u']];L=15-sum(z.hdr[j:i]);ws=[w for _,w in units]
            br=even_break(ws,L,Wc);cum=np.concatenate([[0],np.cumsum(np.array(ws)+SP)])
            pages.append(list(W/np.array([cum[e]-cum[s_]-SP for s_,e in zip(br[:-1],br[1:])])))
    rows.append((f'Nazm 10p ≤{int(sh*100)}%',LW/W,metrics(pages)))
for n,t,r in rows: print(f"{n:16s} type {t*100:4.0f}% | median {r['med']:.2f} | 5-95% {r['p5']:.2f}-{r['p95']:.2f} | spread sd(log) {r['sd']:.3f} | within ±5% of median {r['b5']*100:.0f}% ±10% {r['b10']*100:.0f}% | page sd {r['within']:.3f} | neighbour jump median {r['jump']:.3f} p95 {r['jump95']:.3f}")
