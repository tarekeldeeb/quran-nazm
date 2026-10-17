"""Letter counts of the Quran under different counting conventions, against the report
of al-Hajjaj's count (Ibn Abi Dawud, Kitab al-Masahif; Ibn Kathir, Tafsir, vol. 1 p. 141):
340,740 letters, the half at Al-Kahf 19, thirds at Al-Tawba 100 and Al-Shu'ara 100, and
sevenths at An-Nisa 55, Al-A'raf 147, Ar-Ra'd 35, Al-Hajj 34, Al-Ahzab 36 and Al-Fath 6.

    python scripts/71_letter_count.py        # writes data/letter_count.json

The Madina Uthmani text marks what each convention needs: letters written but never
pronounced (small rounded zero), added small letters (superscript alef, small waw and
ya), doubled letters (shadda), madd, alef wasla and the separate hamza. Errors are the
position of each reported point minus its nominal fraction, in percentage points.
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import DATA

import render_mushaf as R
txt=R.Text(); flat=txt.flat
BASE=set(chr(c) for c in list(range(0x0621,0x063B))+list(range(0x0641,0x064B))+[0x0671])
SMALL={'ٰ','ۥ','ۦ','ۧ'}
def feats(word):
    """per ayah counts of components"""
    chars=list(word)
    f=dict(base=0,hamza=0,wasla=0,silent=0,silent_cont=0,shadda=0,small=0,madd=0)
    for i,ch in enumerate(chars):
        nxt=chars[i+1:i+4]
        if ch in BASE:
            f['base']+=1
            if ch=='ء': f['hamza']+=1
            if ch=='ٱ': f['wasla']+=1
            # a letter is silent if its following marks include U+06DF before the next base letter
            j=i+1
            while j<len(chars) and chars[j] not in BASE and chars[j] not in SMALL:
                if chars[j]=='۟': f['silent']+=1
                if chars[j]=='۠': f['silent_cont']+=1
                j+=1
        elif ch in SMALL: f['small']+=1
        elif ch=='ّ': f['shadda']+=1
        elif ch=='ٓ': f['madd']+=1
    return f
A=[]
for s,a in flat:
    t=txt.suras[s-1]['ayas'][a-1]
    tot=dict(base=0,hamza=0,wasla=0,silent=0,silent_cont=0,shadda=0,small=0,madd=0)
    for w in t.split():
        if w.startswith(R.MARK): continue
        for k,v in feats(w).items(): tot[k]+=v
    A.append(tot)
K=list(A[0]); M=np.array([[x[k] for k in K] for x in A],float)
idx={k:i for i,k in enumerate(K)}
rep={'1/2':((18,19),1/2),'1/3':((9,100),1/3),'2/3':((26,100),2/3),'1/7':((4,55),1/7),'2/7':((7,147),2/7),'3/7':((13,35),3/7),'4/7':((22,34),4/7),'5/7':((33,36),5/7),'6/7':((48,6),6/7)}
def evaluate(w):
    per=M@w; c=np.cumsum(per); T=c[-1]
    errs={}
    for k,(ay,f) in rep.items():
        i=flat.index(ay); errs[k]=(c[i-1]/T-f)*100
    return T, errs
variants={
 'written letters (all)':                dict(base=1),
 'written, no separate hamza':           dict(base=1,hamza=-1),
 'written, no silent letters':           dict(base=1,silent=-1),
 'written, no silent, no wasla':         dict(base=1,silent=-1,wasla=-1),
 'written + small letters':              dict(base=1,small=1),
 'written + small, no silent':           dict(base=1,small=1,silent=-1),
 'written + shadda doubled':             dict(base=1,shadda=1),
 'written + small + shadda':             dict(base=1,small=1,shadda=1),
 'pronounced: +small +shadda -silent':   dict(base=1,small=1,shadda=1,silent=-1),
 'pronounced, -silent -wasla':           dict(base=1,small=1,shadda=1,silent=-1,wasla=-1),
 'written + madd':                       dict(base=1,madd=1),
 'written + small + madd':               dict(base=1,small=1,madd=1),
 'written + small + madd, no silent':    dict(base=1,small=1,madd=1,silent=-1),
 'pronounced + madd':                    dict(base=1,small=1,shadda=1,silent=-1,madd=1),
}
rows=[]
for name,v in variants.items():
    w=np.zeros(len(K)); 
    for k,x in v.items(): w[idx[k]]=x
    T,e=evaluate(w)
    rows.append((name,T,e))
print(f"{'convention':40s}{'total':>9s}{'vs 340,740':>11s}  mean |err| pts   errors at 1/2 1/3 2/3 1/7..6/7 (percentage points)")
for name,T,e in rows:
    print(f"{name:40s}{int(T):9d}{(T/340740-1)*100:+10.1f}%  {np.mean(np.abs(list(e.values()))):6.2f}   "+" ".join(f"{x:+.1f}" for x in e.values()))
OUT = {n: dict(total=int(T), errors=e) for n, T, e in rows}

print()
jz=R.juz_ranges()
for name in ('written letters (all)','written + small letters','written + shadda doubled','pronounced, -silent -wasla','written + small + madd'):
    w=np.zeros(len(K))
    for k,x in variants[name].items(): w[idx[k]]=x
    per=M@w; c=np.cumsum(per)
    jl=np.array([per[a0-1:a1-1].sum() for a0,a1 in jz])
    p16=c[jz[15][0]-2]/c[-1]; p11=c[jz[10][0]-2]/c[-1]; p21=c[jz[20][0]-2]/c[-1]
    print(f"{name:32s} juz16 at {p16*100:.1f}%  juz11 {p11*100:.1f}%  juz21 {p21*100:.1f}%  juz CV {jl.std()/jl.mean():.3f}  max/min {jl.max()/jl.min():.2f}")
    OUT[name].update(juz16_start=p16, juz11_start=p11, juz21_start=p21, juz_cv=float(jl.std() / jl.mean()),
                     juz_max_over_min=float(jl.max() / jl.min()))
json.dump(OUT, open(os.path.join(DATA, "letter_count.json"), "w"), indent=1)
