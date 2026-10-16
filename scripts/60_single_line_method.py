"""Quran-Nazm research script. Paths come from paths.py (QMH, SCAN_PDF, NAZM_WORK)."""
import sys,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from paths import *
import json,numpy as np
H=json.load(open(WORK+'/hizb_ayas.json'))[:58];SP=100;LW=15437.6;P=10;LPP=15
def layout(A):
    # 1) whole hizb as one natural line: units in order, ayah-end positions, header lines as virtual width
    units=[];ends=[];hdr_at=[]
    for a in A:
        if a['hdr']: hdr_at.append((len(units),a['hdr']))
        units+=a['u'];ends.append(len(units))
    w=np.array([x[1] for x in units])+SP;cum=np.concatenate([[0],np.cumsum(w)])
    nh=sum(h for _,h in hdr_at);q=cum[-1]/(P*LPP-nh)            # one text line's worth of width
    vcum=cum.copy()
    for pos,h in hdr_at: vcum[pos:]+=h*q                          # header lines occupy virtual width
    # 2) page breaks at nearest ayah end to k/10 of the virtual total
    Vt=vcum[-1];pb=[0]
    for k in range(1,P):
        t=k*Vt/P;cand=[e for e in ends if e>pb[-1] and e<len(units)]
        pb.append(min(cand,key=lambda e:abs(vcum[e]-t)))
    pb.append(len(units))
    pages=[]
    for s,e in zip(pb[:-1],pb[1:]):
        h=sum(hh for pos,hh in hdr_at if s<=pos<e);L=LPP-h
        # 3) equal split into L lines at nearest word boundary (markers are glued to the previous word)
        tot=cum[e]-cum[s];lb=[s]
        for j in range(1,L):
            t=cum[s]+j*tot/L;cands=range(lb[-1]+1,e-(L-j)+1)
            lb.append(min(cands,key=lambda b:abs(cum[b]-t)))
        lb.append(e)
        lines=[(cum[b]-cum[a]-SP,[u[0] for u in units[a:b]]) for a,b in zip(lb[:-1],lb[1:])]
        pages.append(dict(L=L,hdr=h,lines=lines))
    return pages
ALL=[layout(A) for A in H]
maxline=max(l[0] for pg in ALL for p in pg for l in p['lines'])
def metrics(pages):
    s=np.concatenate([np.array(p) for p in pages]);ls=np.log(s);med=np.median(s)
    return dict(med=med,p5=np.percentile(s,5),p95=np.percentile(s,95),sd=np.std(ls),b10=(np.abs(s-med)<=0.1*med).mean(),
        within=np.median([np.std(p) for p in pages if len(p)>=10]),jump=np.median(np.concatenate([np.abs(np.diff(p)) for p in pages])),
        jump95=np.percentile(np.concatenate([np.abs(np.diff(p)) for p in pages]),95),mx=s.max(),mn=s.min())
m=[o for o in json.load(open(WORK+'/m_1441H.json')) if o['full']];by={}
for o in m: by.setdefault(o['p'],[]).append(o)
rows=[('Madina 1441H',1.0,metrics([[1/o['ratio'] for o in sorted(v,key=lambda o:o['l'])] for v in by.values()]))]
for sh in (0.0,0.10,0.15,0.20):
    W=maxline*(1-sh)
    pages=[[W/l[0] for l in p['lines']] for pg in ALL for p in pg]
    rows.append((f'Nazm ≤{int(sh*100)}%',LW/W,metrics(pages)))
for n,t,r in rows: print(f"{n:14s} type {t*100:4.0f}% | median {r['med']:.2f} | 5-95% {r['p5']:.2f}-{r['p95']:.2f} | min {r['mn']:.2f} max {r['mx']:.2f} | spread {r['sd']:.3f} | ±10% {r['b10']*100:.0f}% | page sd {r['within']:.3f} | jump med {r['jump']:.3f} p95 {r['jump95']:.3f}")
# where does the longest line come from, and page fill spread
L=[(l[0],h+1,pi+1) for h,pg in enumerate(ALL) for pi,p in enumerate(pg) for l in p['lines']];L.sort(reverse=True)
print('longest lines (x Madina):',[(round(a/LW,2),h,p) for a,h,p in L[:6]])
pf=[np.mean([l[0] for l in p['lines']]) for pg in ALL for p in pg];print('page mean line / longest line: min %.2f median %.2f'%(min(pf)/maxline,np.median(pf)/maxline))
json.dump(dict(maxline=maxline,ALL=[[dict(L=p['L'],hdr=p['hdr'],lines=[[float(a),b] for a,b in p['lines']]) for p in pg] for pg in ALL]),open(WORK+'/tarek.json','w'),ensure_ascii=False)
