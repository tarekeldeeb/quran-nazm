"""Quran-Nazm research script. Paths come from paths.py (QMH, SCAN_PDF, NAZM_WORK)."""
import sys,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from paths import *
import json,numpy as np
exec(open(HERE+'/60_single_line_method.py').read().split('ALL=[layout')[0])
def opt_lines(ws,L):
    # split words into exactly L lines minimizing sum of squared deviation from the mean line width
    n=len(ws);cum=np.concatenate([[0],np.cumsum(np.array(ws)+SP)]);tgt=cum[-1]/L;INF=1e30
    best=np.full((L+1,n+1),INF);bk=np.zeros((L+1,n+1),int);best[0][0]=0
    for k in range(1,L+1):
        for e in range(k,n-(L-k)+1):
            lo=max(k-1,e-30)
            for s in range(lo,e):
                if best[k-1][s]>=INF: continue
                c=best[k-1][s]+(cum[e]-cum[s]-tgt)**2
                if c<best[k][e]: best[k][e]=c;bk[k][e]=s
    b=[n];k=L
    while k: b.append(bk[k][b[-1]]);k-=1
    b=b[::-1];return [cum[e]-cum[s]-SP for s,e in zip(b[:-1],b[1:])]
def pages_of(A,joint):
    units=[];ends=[];hdr_at=[]
    for a in A:
        if a['hdr']: hdr_at.append((len(units),a['hdr']))
        units+=a['u'];ends.append(len(units))
    w=np.array([x[1] for x in units])+SP;cum=np.concatenate([[0],np.cumsum(w)])
    nh=sum(h for _,h in hdr_at);q=cum[-1]/(P*LPP-nh);vcum=cum.copy()
    for pos,h in hdr_at: vcum[pos:]+=h*q
    Vt=vcum[-1];E=[0]+ends
    if not joint:
        pb=[0]
        for k in range(1,P):
            t=k*Vt/P;cand=[e for e in ends if e>pb[-1] and e<len(units)];pb.append(min(cand,key=lambda e:abs(vcum[e]-t)))
        pb.append(len(units))
    else:  # choose all 9 page breaks together: minimize squared deviation of each page's virtual width from Vt/10
        idx={e:i for i,e in enumerate(E)};n=len(E);INF=1e30;best=np.full((P+1,n),INF);bk=np.zeros((P+1,n),int);best[0][0]=0
        for k in range(1,P+1):
            for i in range(1,n):
                for j in range(max(0,i-60),i):
                    if best[k-1][j]>=INF: continue
                    c=best[k-1][j]+(vcum[E[i]]-vcum[E[j]]-Vt/P)**2
                    if c<best[k][i]: best[k][i]=c;bk[k][i]=j
        b=[n-1];k=P
        while k: b.append(bk[k][b[-1]]);k-=1
        pb=[E[i] for i in b[::-1]]
    out=[]
    for s,e in zip(pb[:-1],pb[1:]):
        h=sum(hh for pos,hh in hdr_at if s<=pos<e);L=LPP-h;ws=[u[1] for u in units[s:e]]
        out.append(opt_lines(ws,L))
    return out
def metrics(pages):
    s=np.concatenate([np.array(p) for p in pages]);ls=np.log(s);med=np.median(s)
    return dict(med=med,p5=np.percentile(s,5),p95=np.percentile(s,95),sd=np.std(ls),b10=(np.abs(s-med)<=0.1*med).mean(),
        within=np.median([np.std(p) for p in pages if len(p)>=10]),jump=np.median(np.concatenate([np.abs(np.diff(p)) for p in pages])),
        jump95=np.percentile(np.concatenate([np.abs(np.diff(p)) for p in pages]),95),mx=s.max(),mn=s.min())
m=[o for o in json.load(open(WORK+'/m_1441H.json')) if o['full']];by={}
for o in m: by.setdefault(o['p'],[]).append(o)
def run(joint):
    ALL=[pages_of(A,joint) for A in H];ml=max(max(p) for pg in ALL for p in pg)
    return ALL,ml
def decomp(pages):
    s=[np.log(np.array(p)) for p in pages];pm=np.array([x.mean() for x in s])
    return np.std(pm),np.sqrt(np.mean([x.var() for x in s]))
for name,joint in [('your method + optimal line split',False),('+ page breaks chosen together',True)]:
    ALL,ml=run(joint)
    for sh in (0.0,0.20):
        W=ml*(1-sh);pages=[[W/w for w in p] for pg in ALL for p in pg];r=metrics(pages);bp,wp=decomp(pages)
        print(f"{name:34s} ≤{int(sh*100)}% | type {LW/W*100:.0f}% | median {r['med']:.2f} | 5-95% {r['p5']:.2f}-{r['p95']:.2f} max {r['mx']:.2f} | spread {r['sd']:.3f} (between pages {bp:.3f}, within {wp:.3f}) | page sd {r['within']:.3f} | jump med {r['jump']:.3f}")
# decomposition for the plain method and Madina
ALL0=json.load(open(WORK+'/tarek.json'));W=ALL0['maxline'];pg0=[[W/l[0] for l in p['lines']] for pg in ALL0['ALL'] for p in pg]
print('your method as specified: between pages %.3f, within %.3f'%decomp(pg0))
print('Madina 1441H:             between pages %.3f, within %.3f'%decomp([[1/o['ratio'] for o in sorted(v,key=lambda o:o['l'])] for v in by.values()]))
ALL,ml=run(True)
def adj(pg_lists):
    d=[abs(np.log(np.mean(a))-np.log(np.mean(b))) for a,b in zip(pg_lists[:-1],pg_lists[1:])];return np.median(d),np.percentile(d,95)
nz=[];
for pg in ALL: 
    pp=[[1/w for w in p] for p in pg];d=[abs(np.log(np.mean(a))-np.log(np.mean(b))) for a,b in zip(pp[:-1],pp[1:])];nz+=d
mp=[[1/o['ratio'] for o in sorted(by[p],key=lambda o:o['l'])] for p in sorted(by) if len(by[p])==15]
md=[abs(np.log(np.mean(a))-np.log(np.mean(b))) for a,b in zip(mp[:-1],mp[1:])]
print('neighbouring pages, difference in average stretch: Nazm median %.3f p95 %.3f | Madina median %.3f p95 %.3f'%(np.median(nz),np.percentile(nz,95),np.median(md),np.percentile(md,95)))
hz=[np.mean(np.log([1/w for p in pg for w in p])) for pg in ALL];print('between-hizb sd %.3f'%np.std(hz))
