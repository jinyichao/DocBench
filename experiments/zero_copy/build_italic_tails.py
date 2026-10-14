"""clean_1007 + running heads / page numbers that are PRINTED in italic (visually verified per book) written once as $\textit{}$."""
import json,re,collections
B='outputs/work_backup_20261006'
HEAD={'7da538b6':r'Industrial Solvents Handbook|Amines','3135ee8c':r'A-Z Birmingham','ad04f287':r'Index',
      '2ca460ec':r'Table of legislations?','ba58d30d':r'Education Act 1997','558c4212':r'Background, introduction and aims',
      '53a172d1':r"Who's There\?.*",'5ffbad37':r'Textual Introduction','adf56403':r'Quick & Easy|Barbecue'}
NUMIT={'7da538b6','3135ee8c','ad04f287','8e154f2f','9cdbf6bc'}
NUM=r'(\d{1,4}|[ivxlc]{1,7})'
def esc(s): return re.sub(r'\s+',' ',s.replace('&',r'\&')).strip()
log=collections.Counter(); ex=[]
rows=[]
for r in map(json.loads,open(f'{B}/clean_1007.jsonl')):
    d=r['document_id'][:8]; bl=r['markdown'].split('\n\n')
    if d in HEAD or d in NUMIT:
        n=len(bl)
        for i in range(max(0,n-3),n):
            raw=bl[i].strip(); s=re.sub(r'\*','',raw); s=re.sub(r'\s+',' ',s).strip()
            if not s or len(s)>90 or '<' in s or s.startswith('$'): continue
            head=None
            m=re.fullmatch(rf'(?:{NUM}\s+)?(.*?)(?:\s+{NUM})?',s)
            num=None; rest=s
            mm=re.match(rf'^{NUM}\s+(.*)$',s); mn=re.match(rf'^(.*?)\s+{NUM}$',s)
            if re.fullmatch(NUM,s): num,rest=s,''
            elif mm and (head or d in NUMIT) : num,rest=mm.group(1),mm.group(2)
            elif mn: num,rest=mn.group(2),mn.group(1)
            if d in HEAD: head=re.search(HEAD[d],rest)
            if not head and not num: continue
            if not head and d not in NUMIT: continue
            PLAINHEAD={'9cdbf6bc':r'feeling sorry for celia|jaclyn moriarty'}
            if num and not head and rest and not (d in PLAINHEAD and re.fullmatch(PLAINHEAD[d],rest)): continue
            out_text=[]; out_f=[]
            if head:
                h=head.group(0); other=esc(rest.replace(h,' '))
                out_f.append('$\\textit{'+esc(h)+'}$')
                if other: out_text.append(other)
            elif rest: out_text.append(rest)
            if num:
                (out_f if d in NUMIT else out_text).append('$\\textit{'+num+'}$' if d in NUMIT else num)
            new='\n\n'.join(([' '.join(out_text)] if out_text else [])+out_f)
            if new!=bl[i]: log[d]+=1; ex.append((d,r['page'],raw.replace('\n',' / ')[:40],new.replace('\n\n',' | ')[:70])); bl[i]=new
    rows.append(dict(r,markdown='\n\n'.join(bl)))
with open(f'{B}/clean_ittails_1007.jsonl','w') as f:
    for r in rows: f.write(json.dumps(r,ensure_ascii=False)+'\n')
print('tail blocks converted per book:',dict(log),'total',sum(log.values()))
seen=set()
for e in ex:
    if e[0] in seen: continue
    seen.add(e[0]); print('  ',e)
