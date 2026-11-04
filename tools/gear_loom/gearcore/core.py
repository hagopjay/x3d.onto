from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
class GateError(RuntimeError):
 def __init__(self,code,detail=''):self.code=code;super().__init__(code+(': '+str(detail) if detail else ''))
def require(ok,code,detail=''):
 if not ok:raise GateError(code,detail)
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def sha(x):return hashlib.sha256(x).hexdigest()
def read(path):return json.loads(Path(path).read_text())
def write(path,obj):Path(path).parent.mkdir(parents=True,exist_ok=True);Path(path).write_bytes(canonical(obj)+b'\n')
def inventory():return {p.relative_to(ROOT).as_posix():sha(p.read_bytes()) for p in sorted(ROOT.rglob('*')) if p.is_file() and p!=ROOT/'SHA256SUMS.txt' and not any(k in ['evidence','node_modules','__pycache__','.git','.venv'] for k in p.relative_to(ROOT).parts) and p.suffix not in ['.pyc','.zip']}
def subject():return sha(canonical(inventory()))
def cards():return read(ROOT/'cards/trains.json')
