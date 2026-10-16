"""Quran-Nazm research script. Paths come from paths.py (QMH, SCAN_PDF, NAZM_WORK)."""
import sys,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from paths import *
import sys,json,numpy as np,cv2
from lib_scan import load,frame
from skimage.morphology import skeletonize
from concurrent.futures import ProcessPoolExecutor
U=4
db=json.load(open(QMH+'/assets/db/v2/Madina-1441H.json'))
m={(o['p'],o['l']):o for o in json.load(open(WORK+'/m_1441H.json'))}
def page(p):
    im,g,c=load(p);rr,cc=frame(c)
    try:
        x0,x1=cc[cc<360].max()+4,cc[cc>360].min()-4;y0,y1=rr[rr<560].max()+4,rr[rr>560].min()-4
    except ValueError: return []
    cm=cv2.dilate(c.astype(np.uint8),np.ones((5,5),np.uint8))>0
    if any(r['k']!='text' for r in db['lines'][p-1]): return []
    pitch=(y1-y0)/15;out=[]
    for l in range(15):
        row=db['lines'][p-1][l]
        if row['k']!='text': continue
        a,b=int(y0+l*pitch),int(y0+(l+1)*pitch)
        gb=g[a:b,x0:x1].astype(np.float32);mask=cm[a:b,x0:x1]
        # remove colored marker areas (ring + digits): fill bbox of colored components
        n,lab,st,_=cv2.connectedComponentsWithStats(mask.astype(np.uint8))
        for k in range(1,n):
            x,y,w,h,ar=st[k]
            if ar>40: gb[y:y+h,x:x+w]=255
        gu=cv2.resize(gb,None,fx=U,fy=U,interpolation=cv2.INTER_CUBIC)
        bw=gu<128
        bw=cv2.morphologyEx(bw.astype(np.uint8),cv2.MORPH_OPEN,np.ones((2,2),np.uint8))>0
        area=bw.sum()
        if area<500: continue
        sk=skeletonize(bw);L=sk.sum()
        dt=cv2.distanceTransform(bw.astype(np.uint8),cv2.DIST_L2,5)
        sw_area=area/L/U
        sw_dt=2*np.median(dt[sk])/U
        prof=bw.sum(1);pk=prof.max()
        body=(prof>=0.5*pk).sum()/U; pkrel=float(np.argmax(prof)/len(prof))
        o=m.get((p,l+1),{})
        out.append(dict(p=p,l=l+1,sw=float(sw_area),swd=float(sw_dt),body=float(body),ink=float(area/U/U),pk=pkrel,
            ratio=o.get('ratio'),words=o.get('words'),letters=o.get('letters'),full=o.get('full'),box=[int(x0),a,int(x1),b]))
    return out
if __name__=='__main__':
    with ProcessPoolExecutor() as ex: res=[r for rs in ex.map(page,range(3,605)) for r in rs]
    json.dump(res,open(WORK+'/w_1441H.json','w'))
    print(len(res))
