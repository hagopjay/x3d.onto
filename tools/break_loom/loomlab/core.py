from pathlib import Path
import hashlib,json

ROOT=Path(__file__).resolve().parents[1]
WITNESSES=['Grammar','Meaning','Traps','Behaviour','Eyes','Host','Receipts','Truth','Budget','Ear','Score']
class GateError(RuntimeError):
 def __init__(self,code,detail=''): self.code=code;self.detail=detail;super().__init__(code+(': '+detail if detail else ''))
def require(ok,code,detail=''):
 if not ok:raise GateError(code,str(detail))
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf8')
def sha(x):return hashlib.sha256(x).hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf8'))
def write(path,obj):Path(path).parent.mkdir(parents=True,exist_ok=True);Path(path).write_bytes(canonical(obj)+b'\n')
def inventory(root=ROOT):
 return {p.relative_to(root).as_posix():sha(p.read_bytes()) for p in sorted(Path(root).rglob('*')) if p.is_file() and not any(x in ['evidence','node_modules','__pycache__','.git','.venv'] for x in p.relative_to(root).parts) and p.suffix not in ['.pyc','.zip']}
def subject(root=ROOT):return sha(canonical(inventory(root)))
def cards():return read(ROOT/'recipes/cases.json')['cases']
def case(cid):
 rows=[c for c in cards() if c['id']==cid];require(len(rows)==1,'UNKNOWN_CASE',cid);return rows[0]
def bundle(cid,variant):
 require(variant in ['mutant','control'],'UNKNOWN_VARIANT',variant);case(cid);return ROOT/'corpus'/cid/variant
def result(witness,code=None,detail=None,**measurements):
 return {'witness':witness,'status':'catch' if code else 'pass','diagnostic':code,'detail':detail,'measurements':measurements,'grade':'C'}
def na(witness,reason='Outside the declared scope of this family witness.'):
 return {'witness':witness,'status':'not_applicable','detail':reason,'grade':None,'measurements':{}}
