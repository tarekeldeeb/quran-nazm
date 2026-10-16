"""Quran-Nazm research script. Paths come from paths.py (QMH, SCAN_PDF, NAZM_WORK)."""
import sys,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from paths import *
import json,numpy as np
w=[o for o in json.load(open(WORK+'/w_1441H.json')) if o['full']]
sw=np.array([o['sw'] for o in w]);r=np.array([o['ratio'] for o in w]);ink=np.array([o['ink'] for o in w]);let=np.array([o['letters'] for o in w]);ipl=ink/let
print(len(w),len({o['p'] for o in w}),'sw pct',np.percentile(sw,[1,5,50,95,99]).round(2),'cv',(sw.std()/sw.mean()).round(3))
print('corr sw-ratio',np.corrcoef(sw,r)[0,1].round(3),'ipl pct',np.percentile(ipl,[1,5,50,95,99]).round(1),'corr ipl-r',np.corrcoef(ipl,r)[0,1].round(3))
by={}
for o in w: by.setdefault(o['p'],[]).append(o)
rng=sorted([(max(x['sw'] for x in v)/min(x['sw'] for x in v),p) for p,v in by.items()],reverse=True)
print('page sw max/min top',[(round(a,2),p) for a,p in rng[:6]],'median',round(float(np.median([a for a,_ in rng])),3))
J=[]
for p,v in by.items():
  d={x['l']:x for x in v}
  for l,x in d.items():
    y=d.get(l+1)
    if y: J.append((max(x['sw'],y['sw'])/min(x['sw'],y['sw']),p,l,x['sw'],y['sw'],x['ratio'],y['ratio']))
J.sort(reverse=True);print('adjacent',[(round(a,2),p,l,round(s1,2),round(s2,2),round(r1,2),round(r2,2)) for a,p,l,s1,s2,r1,r2 in J[:8]])
for lo,hi in [(0.6,0.8),(0.8,0.9),(0.9,1.0),(1.0,1.1),(1.1,1.2),(1.2,1.4)]:
  s=(r>=lo)&(r<hi);print(lo,hi,s.sum(),sw[s].mean().round(3),ipl[s].mean().round(1))
print('lightest',[(o['p'],o['l'],round(o['sw'],2),round(o['ratio'],2)) for o in sorted(w,key=lambda o:o['sw'])[:5]])
print('heaviest',[(o['p'],o['l'],round(o['sw'],2),round(o['ratio'],2)) for o in sorted(w,key=lambda o:-o['sw'])[:5]])
