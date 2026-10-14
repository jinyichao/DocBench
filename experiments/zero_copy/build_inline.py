"""Zero-copy, structure-preserving: inside each fused furniture block, wrap ONE piece in inline $\\textit{..}$ (block keeps other text, so it stays a text block)."""
import json,re,zipfile
DOCS={'7da538b6','3135ee8c','ad04f287','9cdbf6bc','2ca460ec','bc7b5e32'}
NUM=r'(?<![\w.,/])(\d{1,4}|[ivxlc]{1,7})(?![\w.,/])'
def furn(d,s,last):
    s0=s.strip()
    if d=='3135ee8c': return bool(re.fullmatch(r'(\d{1,4} )?A-Z Birmingham( \d{1,4})?',s0))
    if d=='7da538b6': return bool(re.fullmatch(r'\*?(Amines|Industrial Solvents Handbook)\*?',re.sub(NUM,'',s0).strip())) and re.search(r'\d',s0)
    if d=='ad04f287': return bool(re.fullmatch(r'\*?Index\*?',re.sub(NUM,'',s0).strip())) and re.search(r'\d',s0)
    if d=='9cdbf6bc': return bool(re.fullmatch(r'(jaclyn moriarty|feeling sorry for celia)',re.sub(NUM,'',s0).strip())) and re.search(r'\d',s0)
    if d=='2ca460ec': return bool(re.fullmatch(r'\*?Table of (cases|legislation)\*?',re.sub(NUM,'',s0).strip())) and re.search(r'\b[ivxlc]+\b',s0)
    if d=='bc7b5e32': return last and 'Macmillan' in s0 and bool(re.search(r'(^|\n)[ivx]{1,5}(\n|$)',s0))
def wrap(d,s,mode):
    if mode=='num' or d in ('9cdbf6bc','2ca460ec','bc7b5e32'):
        return re.sub(NUM,lambda m:'$\\textit{'+m.group(1)+'}$',s,count=1)
    # head mode (TECH/TRAVEL/HOUSE): wrap the words, keep number plain
    m=re.search(NUM,s); n=m.group(1); head=re.sub(r'\*','',re.sub(NUM,'',s,count=1)).strip()
    return ('$\\textit{'+head+'}$ '+n) if s.strip().endswith(n) else (n+' $\\textit{'+head+'}$')
def build(mode,name):
    out=[];cnt={}
    for r in map(json.loads,open('clean_1007.jsonl')):
        d=r['document_id'][:8]; bl=r['markdown'].split('\n\n')
        if d in DOCS:
            for i,b in enumerate(bl):
                if b and furn(d,b,i>=len(bl)-2):
                    nb=wrap(d,b,mode)
                    if nb!=b: bl[i]=nb; cnt[d]=cnt.get(d,0)+1
        out.append(dict(r,markdown='\n\n'.join(bl)))
    with open(f'{name}.jsonl','w') as fo:
        for r in out: fo.write(json.dumps(r,ensure_ascii=False)+'\n')
    with zipfile.ZipFile(f'../../submissions/tabswap/{name}.zip','w',zipfile.ZIP_DEFLATED) as zf: zf.write(f'{name}.jsonl','predictions.jsonl')
    print(name,cnt,sum(cnt.values()))
build('num','inline_num_1007'); build('head','inline_head_1007')
