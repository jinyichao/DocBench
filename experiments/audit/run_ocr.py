"""PaddleOCR line boxes for all test pages -> outputs/ocr_test/ocr_test.json  {img_path: [[text,[x0,y0,x1,y1]],...]} (resumable)."""
import json,glob,os,sys
from paddleocr import PaddleOCR
out='outputs/ocr_test/ocr_test.json'
res=json.load(open(out)) if os.path.exists(out) else {}
ocr=PaddleOCR(lang='en', use_doc_orientation_classify=False, use_doc_unwarping=False, use_textline_orientation=False)
imgs=sorted(glob.glob('data/DrDocBench/test/*/*/images/*.jpg'))
for i,p in enumerate(imgs):
    k=p.replace('','')
    if k in res: continue
    try:
        r=ocr.predict(p)[0]
        res[k]=[[t,[float(v) for v in b]] for t,b in zip(r['rec_texts'],r['rec_boxes'])]
    except Exception as e:
        res[k]=[]; print('ERR',k,e,flush=True)
    if i%20==0:
        json.dump(res,open(out,'w')); print(i,len(imgs),flush=True)
json.dump(res,open(out,'w')); print('done',len(res))
