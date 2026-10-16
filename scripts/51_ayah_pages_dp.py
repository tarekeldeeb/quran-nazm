"""Quran-Nazm research script. Paths come from paths.py (QMH, SCAN_PDF, NAZM_WORK)."""
import sys,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from paths import *
import json,math,numpy as np
H=json.load(open(WORK+'/hizb_ayas.json'))[:58];SP=100;LW=15437.6
def lines_needed(ws,Wm):
    n=1;cur=-SP
    for w in ws:
        if w>Wm: return 999
        if cur+SP+w<=Wm: cur+=SP+w
        else: n+=1;cur=w
    return n
class Hz:
    def __init__(s,A):
        s.A=A;s.n=len(A);s.ws=[[w for _,w in a['u']] for a in A];s.hdr=[a['hdr'] for a in A]
        s.T=np.concatenate([[0],np.cumsum([sum(w)+SP*len(w) for w in s.ws])])
    def maxi(s,Wc):
        M=[]
        for j in range(s.n):
            ws=[];h=0;best=j-1
            for i in range(j,s.n):
                ws+=s.ws[i];h+=s.hdr[i]
                if lines_needed(ws,Wc)<=15-h: best=i
                else: break
            M.append(best)
        return M
    def feasible(s,Wc,P):
        M=s.maxi(Wc);lo,hi=0,0   # reachable start positions (next page starts at index in [lo,hi])
        for k in range(P):
            if lo>hi or lo>=s.n: return False
            nhi=max(M[j] for j in range(lo,min(hi,s.n-1)+1))+1;nlo=lo+1;lo,hi=nlo,nhi
        return lo<=s.n<=hi
    def best_partition(s,Wc,W,P):
        M=s.maxi(Wc);INF=1e18
        cost=[[INF]*(s.n+1) for _ in range(P+1)];back=[[None]*(s.n+1) for _ in range(P+1)];cost[0][0]=0
        for k in range(P):
            for j in range(s.n):
                if cost[k][j]>=INF: continue
                h=0
                for i in range(j,M[j]+1):
                    h+=s.hdr[i];L=15-h;T=s.T[i+1]-s.T[j]
                    c=cost[k][j]+(math.log(L*W/T))**2
                    if c<cost[k+1][i+1]: cost[k+1][i+1]=c;back[k+1][i+1]=j
        if cost[P][s.n]>=INF: return None
        b=[s.n];k=P
        while k: b.append(back[k][b[-1]]);k-=1
        return b[::-1]
def even_break(ws,L,Wm):
    n=len(ws);cum=np.cumsum(np.array(ws)+SP);T=cum[-1];idx=[0];start=0
    for k in range(1,L):
        target=k*T/L;best=None
        for e in range(start+1,n-(L-k)+1):
            w=cum[e-1]-(cum[start-1] if start else 0)-SP
            if w>Wm: break
            if best is None or abs(cum[e-1]-target)<abs(cum[best-1]-target): best=e
        if best is None: best=start+1
        idx.append(best);start=best
    idx.append(n);return idx
HZ=[Hz(A) for A in H]
def solve(P,shrink):
    lo,hi=8000,60000
    for _ in range(22):
        mid=(lo+hi)/2
        if all(z.feasible(mid,P) for z in HZ): hi=mid
        else: lo=mid
    Wc=hi;W=Wc*(1-shrink);lines=[];pages=[]
    for hi_,z in enumerate(HZ):
        b=z.best_partition(Wc,W,P)
        for j,i in zip(b[:-1],b[1:]):
            units=[u for a in z.A[j:i] for u in a['u']];h=sum(z.hdr[j:i]);L=15-h
            ws=[w for _,w in units];br=even_break(ws,L,Wc);cum=np.concatenate([[0],np.cumsum(np.array(ws)+SP)])
            lw=[cum[e]-cum[s]-SP for s,e in zip(br[:-1],br[1:])];st=W/np.array(lw)
            lines+=list(st);pages.append(dict(h=hi_+1,j=j,i=i,L=L,hdr=h,st=st.tolist(),units=[[t for t,_ in units[s:e]] for s,e in zip(br[:-1],br[1:])],avg=float(np.mean(st))))
    return Wc,W,np.array(lines),pages
if __name__=='__main__':
    out={}
    for P in (8,10):
        for sh in (0.0,0.1):
            Wc,W,st,pages=solve(P,sh);pa=np.array([p['avg'] for p in pages]);sd=np.median([np.std(p['st']) for p in pages])
            print(f"{P}p shrink {int(sh*100)}%: type {LW/W*100:.0f}% | line stretch median {np.median(st):.2f} p5 {np.percentile(st,5):.2f} p95 {np.percentile(st,95):.2f} max {st.max():.2f} | 0.95-1.19 {((st>=.95)&(st<=1.19)).mean()*100:.0f}% >1.30 {(st>1.3).mean()*100:.0f}% >1.50 {(st>1.5).mean()*100:.1f}% shrunk {(st<1).mean()*100:.0f}% | page avg {pa.min():.2f}-{pa.max():.2f} (p95 {np.percentile(pa,95):.2f}) | page sd {sd:.3f}")
            out[f'{P}_{int(sh*100)}']=dict(Wc=Wc,W=W,pages=pages)
    json.dump(out,open(WORK+'/aya_pages.json','w'),ensure_ascii=False)
