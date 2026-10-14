import json,re,glob,numpy as np
from PIL import Image
O=json.load(open('outputs/ocr_test/ocr_test.json'))
def slant(img,bx):
    x0,y0,x1,y1=[int(v) for v in bx[:4]] if len(bx)>=4 else bx
    g=np.asarray(img.convert('L').crop((max(0,x0-2),max(0,y0-2),x1+2,y1+2)),dtype=np.float32)
    if g.shape[0]<8 or g.shape[1]<20: return None
    ink=(g<(g.mean()-0.5*g.std())).astype(np.float32)   # dark pixels
    h,w=ink.shape; best=None
    for a in np.arange(-8,22,1.0):
        t=np.tan(np.radians(a)); W=w+int(abs(t)*h)+2; prof=np.zeros(W)
        ys,xs=np.nonzero(ink)
        xx=(xs - (h-1-ys)*t + abs(t)*h).astype(int)   # undo a rightward lean of angle a
        np.add.at(prof,np.clip(xx,0,W-1),1)
        s=(prof**2).sum()
        if best is None or s>best[1]: best=(a,s)
    return best[0]
def page(d,p):
    k=[k for k in O if f'/{d}' in k and k.endswith(f'/page_{p}.jpg')][0]; return k,O[k]
if __name__=='__main__':
    for d,p in [('3135ee8c',217),('9cdbf6bc',37),('ad04f287',169),('7da538b6',803)]:
        k,o=page(d,p); im=Image.open(k)
        print('==',d,p,'box format',o[0][1][:4] if o else '')
        for i,(t,bx) in enumerate(o):
            if any(w in t for w in ('Birmingham','Horatio','Holland Rd. Gt','jaclyn','Index','156','Amines','777','Hollyoake','celia')) or i<2:
                print(f'   slant {slant(im,bx)!s:>5}  {t[:50]!r}')
