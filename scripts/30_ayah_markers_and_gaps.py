"""Quran-Nazm research script. Paths come from paths.py (QMH, SCAN_PDF, NAZM_WORK)."""
import sys,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from paths import *
import sys,json,re,numpy as np,cv2
from lib_scan import load,frame
from concurrent.futures import ProcessPoolExecutor
db=json.load(open(QMH+'/assets/db/v2/Madina-1441H.json'))
M={}
for o in json.load(open(WORK+'/m_1441H.json')): M[(o['p'],o['l'])]=o
def find_marks(im,a,b,x0,x1):
    hsv=cv2.cvtColor(im[a:b,x0:x1],cv2.COLOR_BGR2HSV);mk=(hsv[...,1]>30).astype(np.uint8)
    mk=cv2.morphologyEx(mk,cv2.MORPH_CLOSE,np.ones((3,3),np.uint8))
    n,lab,st,_=cv2.connectedComponentsWithStats(mk)
    bx=sorted([list(st[k][:4]) for k in range(1,n) if st[k][4]>60 and 12<st[k][2]<40]);Mk=[]
    for x,y,w,h in bx:
        if Mk and x<Mk[-1][0]+Mk[-1][2]-4: Mk[-1][2]=max(Mk[-1][0]+Mk[-1][2],x+w)-Mk[-1][0]
        else: Mk.append([x,y,w,h])
    return [m for m in Mk if m[2]>=15]
def page(p):
    if any(r['k']!='text' for r in db['lines'][p-1]): return []
    im,g,c=load(p);rr,cc=frame(c)
    try: x0,x1=cc[cc<360].max()+4,cc[cc>360].min()-4;y0,y1=rr[rr<560].max()+4,rr[rr>560].min()-4
    except ValueError: return []
    hsv=cv2.cvtColor(im,cv2.COLOR_BGR2HSV);pitch=(y1-y0)/15;out=[]
    for l in range(1,16):
        o=M.get((p,l))
        if not o: continue
        a,b=int(y0+(l-1)*pitch),int(y0+l*pitch)
        mk=find_marks(im,a,b,x0,x1)
        ink=(g[a:b,x0:x1]<140)&(hsv[a:b,x0:x1,1]<30)
        cols=np.where(ink.sum(0)>0)[0];
        if len(cols)==0: continue
        L,R=cols[0],cols[-1]
        starts_mark=bool(mk) and max(m[0]+m[2] for m in mk)>=R-12
        ends_mark=bool(mk) and min(m[0] for m in mk)<=L+3
        # gaps
        proj=ink.sum(0).copy()
        for m_ in mk: proj[max(0,m_[0]-2):m_[0]+m_[2]+2]=99
        gaps=[];run=0;st=None
        for x in range(L,R+1):
            if proj[x]==0:
                if run==0: st=x
                run+=1
            else:
                if run>=2: gaps.append((st,run))
                run=0
        nw=o['words'];sel=sorted(gaps,key=lambda t:-t[1])[:max(0,nw-1-len(mk))]
        out.append(dict(p=p,l=l,db_start=o['text'].startswith('۝'),scan_start=starts_mark,nmk=len(mk),nmk_db=o['text'].count('۝'),
            gaps=[int(t[1]) for t in sel],gx=[int(t[0]+x0) for t in sel],y0=a,y1=b,x0=int(x0),x1=int(x1),full=o['full'],words=nw,ratio=o['ratio']))
    return out
if __name__=='__main__':
    with ProcessPoolExecutor() as ex: res=[r for rs in ex.map(page,range(3,605)) for r in rs]
    json.dump(res,open(WORK+'/mg.json','w'),default=lambda v: v.item() if hasattr(v,'item') else str(v))
    ok=[o for o in res if o['nmk']==o['nmk_db']]
    print(len(res),'marker count agrees',len(ok))
    a=sum(o['db_start'] and o['scan_start'] for o in ok);b=sum(o['db_start'] for o in ok);c=sum(o['scan_start'] and not o['db_start'] for o in ok)
    print('db says starts',b,'scan confirms',a,'scan-only',c)
