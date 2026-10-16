"""Quran-Nazm research script. Paths come from paths.py (QMH, SCAN_PDF, NAZM_WORK)."""
import sys,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from paths import *
import sys,json,numpy as np,cv2
from lib_scan import load,frame
from concurrent.futures import ProcessPoolExecutor
db=json.load(open(QMH+'/assets/db/v2/Madina-1441H.json'))
def page(p):
    if any(r['k']!='text' for r in db['lines'][p-1]): return []
    im,g,c=load(p);rr,cc=frame(c)
    try: x0,x1=cc[cc<360].max()+4,cc[cc>360].min()-4;y0,y1=rr[rr<560].max()+4,rr[rr>560].min()-4
    except ValueError: return []
    ink=(g<128)&~(cv2.dilate(c.astype(np.uint8),np.ones((3,3),np.uint8))>0)
    pitch=(y1-y0)/15;out=[]
    for l in range(15):
        a,b=int(y0+l*pitch),int(y0+(l+1)*pitch);band=ink[a:b,x0:x1]
        cols=np.where(band.sum(0)>0)[0]
        if len(cols)==0: continue
        prof=band.sum(1).astype(float);prof=np.convolve(prof,[1,2,1],'same')
        base=a+np.argmax(prof)
        W=band.shape[1];hl=band[:,:W//2].sum(1);hr=band[:,W//2:].sum(1)
        tilt=float(np.argmax(np.convolve(hr,[1,2,1],'same'))-np.argmax(np.convolve(hl,[1,2,1],'same')))
        # gaps: vertical projection of the core (baseline zone) columns empty
        core=band[max(0,base-a-12):base-a+4]
        e=(core.sum(0)==0).astype(int)
        gaps=[];run=0
        for v in e[cols[0]:cols[-1]+1]:
            if v: run+=1
            else:
                if run>=4: gaps.append(run)
                run=0
        out.append(dict(p=p,l=l+1,left=int(cols[0]),right=int(W-1-cols[-1]),base=int(base),tilt=tilt,gaps=gaps,W=W))
    return out
if __name__=='__main__':
    with ProcessPoolExecutor() as ex: res=[r for rs in ex.map(page,range(3,605)) for r in rs]
    json.dump(res,open(WORK+'/more.json','w'));print(len(res))
