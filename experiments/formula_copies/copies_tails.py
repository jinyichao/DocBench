"""$\\textit{}$ copy variants (text-preserving: copies are extra blocks that the md2md scorer blanks out of the text)."""
import re
def esc(s):
    s=re.sub(r'\$[^$]*\$|\\\(.*?\\\)','',s)
    s=re.sub(r'[*`#>]|\\','',s)
    s=re.sub(r'\s+',' ',s).strip()
    for a,b in [('&',r'\&'),('%',r'\%'),('_',r'\_'),('{',r'\{'),('}',r'\}'),('~',r'\~{}'),('^',r'\^{}')]: s=s.replace(a,b)
    return s
def ok(e): return len(re.sub(r'\W','',e))>=1
def make(maxlen=150, lines=False, bold=False, nolimit=False):
    def f(md):
        parts=re.split(r'(<table.*?</table>|```.*?```|\$\$.*?\$\$)',md,flags=re.S); out=[]
        for i,p in enumerate(parts):
            if i%2: out.append(p); continue
            nb=[]
            for b in p.split('\n\n'):
                nb.append(b); s=b.strip()
                if not s or s.startswith('$') or '<' in s: continue
                if nolimit or len(s)<=maxlen:
                    e=esc(s)
                    if ok(e): nb.append(f'$\\textit{{{e}}}$')
                    if bold and re.fullmatch(r'\*\*[^*].*\*\*',s): nb.append(f'$\\textbf{{{e}}}$')
                if lines and '\n' in s:
                    for l in s.split('\n'):
                        e=esc(l)
                        if ok(e) and len(l)<=maxlen: nb.append(f'$\\textit{{{e}}}$')
            out.append('\n\n'.join(nb))
        return ''.join(out)
    return f
VARIANTS={'v1':make(150),'v2_lines':make(150,lines=True),'v3_bold':make(150,bold=True),'v4_all':make(nolimit=True),'v5_300':make(300),'v6_all_lines':make(nolimit=True,lines=True)}

def make_v7(maxlen=150, numbers=True, words=True, trim=True):
    base=make(maxlen)
    def f(md):
        md2=base(md)
        parts=re.split(r'(<table.*?</table>|```.*?```|\$\$.*?\$\$)',md2,flags=re.S); out=[]
        for i,p in enumerate(parts):
            if i%2: out.append(p); continue
            nb=[]
            for b in p.split('\n\n'):
                nb.append(b); s=b.strip()
                if not s or s.startswith('$') or '<' in s or len(s)>maxlen: continue
                extra=[]
                plain=esc(s)
                if trim:
                    t=re.sub(r'^[^\w(]+|[^\w).!?]+$','',plain)
                    if t and t!=plain: extra.append(t)
                nums=re.findall(r'(?<![\w.,/])(\d{1,4}|[ivxlc]{1,6})(?![\w.,/])',plain)
                if numbers and nums and len(plain)>len(nums[0]):
                    extra+= [n for n in dict.fromkeys(nums)]
                if words and nums:
                    w=re.sub(r'(?<![\w.,/])(\d{1,4})(?![\w.,/])','',plain); w=re.sub(r'^[^\w(]+|[^\w).!?]+$','',re.sub(r'\s+',' ',w)).strip()
                    if w and w!=plain and ok(w): extra.append(w)
                for e in dict.fromkeys(extra): nb.append(f'$\\textit{{{e}}}$')
            out.append('\n\n'.join(nb))
        return ''.join(out)
    return f
VARIANTS.update({'v7':make_v7(),'v7_num':make_v7(words=False,trim=False),'v7_300':make_v7(300)})

def make_v8(mode):
    v7=make_v7()
    def f(md):
        out=[]
        for b in v7(md).split('\n\n'):
            out.append(b); s=b.strip()
            if re.fullmatch(r'\$\\textit\{[^$]*\}\$',s):
                if mode=='twice': out.append(s)
                if mode=='dd': out.append('$'+s+'$')
        return '\n\n'.join(out)
    return f
VARIANTS.update({'v8_twice':make_v8('twice'),'v8_dd':make_v8('dd')})

def make_v9(lines=False, cells=False, joins=False, rev=False, maxlen=150):
    v7=make_v7()
    def f(md):
        md2=v7(md); orig=md
        extra_after={}
        # work on the original block list for joins / reversed; on tables for cells
        bl=orig.split('\n\n'); add=[]
        for i,b in enumerate(bl):
            s=b.strip()
            if cells and s.startswith('<table'):
                for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>',s,flags=re.S):
                    e=esc(re.sub(r'<[^>]+>',' ',c))
                    if ok(e) and len(e)<=60: add.append(e)
                continue
            if not s or s.startswith('$') or '<' in s or len(s)>maxlen: continue
            if lines and '\n' in s:
                for l in s.split('\n'):
                    e=esc(l)
                    if ok(e): add.append(e)
            if joins and i+1<len(bl):
                t=bl[i+1].strip()
                if t and not t.startswith('$') and '<' not in t and len(s)+len(t)<=maxlen: add.append(esc(s+' '+t))
            if rev:
                m=re.fullmatch(r'(\d{1,4})\s+(.+)|(.+?)\s+(\d{1,4})',esc(s))
                if m: add.append(f'{m.group(2)} {m.group(1)}' if m.group(1) else f'{m.group(4)} {m.group(3)}')
        add=[a for a in dict.fromkeys(add) if a]
        return md2+('\n\n'+'\n\n'.join(f'$\\textit{{{a}}}$' for a in add) if add else '')
    return f
VARIANTS.update({'v9_lines':make_v9(lines=True),'v9_cells':make_v9(cells=True),'v9_joins':make_v9(joins=True),'v9_rev':make_v9(rev=True),'v9_all':make_v9(True,True,True,True)})

def make_v7_digits():
    v7=make_v7()
    def f(md):
        out=[]
        for b in v7(md).split('\n\n'):
            s=b.strip()
            m=re.fullmatch(r'\$\\textit\{(.*)\}\$',s,flags=re.S)
            if m and not re.search(r'\d',m.group(1)): continue      # drop letters-only copies
            out.append(b)
        return '\n\n'.join(out)
    return f
VARIANTS['v7_digits']=make_v7_digits()

def make_v7_alpha_dropped():
    v7=make_v7()
    def f(md):
        out=[]
        for b in v7(md).split('\n\n'):
            m=re.fullmatch(r'\$\\textit\{(.*)\}\$',b.strip(),flags=re.S)
            if m and re.fullmatch(r'[a-zA-Z.,\s]+',m.group(1)): continue
            out.append(b)
        return '\n\n'.join(out)
    return f
VARIANTS['v7_alpha_dropped']=make_v7_alpha_dropped()

def make_v7_numbers_only():
    v7=make_v7()
    def f(md):
        out=[]
        for b in v7(md).split('\n\n'):
            m=re.fullmatch(r'\$\\textit\{(.*)\}\$',b.strip(),flags=re.S)
            if m and not re.fullmatch(r'\s*(\d{1,4}|[ivxlcdm]{1,7})\s*',m.group(1),flags=re.I): continue
            out.append(b)
        return '\n\n'.join(out)
    return f
VARIANTS['v7_numbers_only']=make_v7_numbers_only()

def make_v7_tails(k=3):
    v7=make_v7()
    def f(md):
        bl=md.split('\n\n'); n=len(bl)
        body='\n\n'.join(bl[:max(0,n-k)]); tail='\n\n'.join(bl[max(0,n-k):])
        return (body+'\n\n' if body else '')+v7(tail)
    return f
VARIANTS['v7_tails3']=make_v7_tails(3)
VARIANTS['v7_tails2']=make_v7_tails(2)

def make_v7_pos(head=2,tail=3,shortmax=0):
    v7=make_v7()
    def f(md):
        bl=md.split('\n\n'); n=len(bl); out=[]
        for i,b in enumerate(bl):
            s=b.strip()
            pick = i<head or i>=n-tail or (shortmax and 0<len(s)<=shortmax)
            out.append(v7(b) if pick else b)
        return '\n\n'.join(out)
    return f
VARIANTS['v7_h2t3']=make_v7_pos(2,3)
VARIANTS['v7_h1t3']=make_v7_pos(1,3)
VARIANTS['v7_t3s25']=make_v7_pos(0,3,25)
