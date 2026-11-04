"""Small fail-closed contracts, shared with the portable Loom gate kit."""
import hashlib,json,math,re
class Rejected(ValueError):
 def __init__(self,code,detail=''):self.code=code;self.detail=detail;super().__init__(code+(': '+detail if detail else ''))
def need(ok,code,detail=''):
 if not ok:raise Rejected(code,detail)
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def digest(x):return hashlib.sha256(x).hexdigest()
def finite_vector(v,n,limit):
 need(type(v) is list and len(v)==n and all(type(x) in (int,float) and math.isfinite(x) and abs(x)<=limit for x in v),'FINITE_VECTOR')
 return [float(x) for x in v]
def envelope(c):
 need(type(c) is dict and set(c)=={'client_id','command_id','base_revision','guid','op','value'},'COMMAND_FIELDS')
 for k in ['client_id','command_id']:need(type(c[k]) is str and re.fullmatch(r'[A-Za-z0-9_-]{8,80}',c[k]),'COMMAND_ID')
 need(type(c['base_revision']) is int and c['base_revision']>=0,'REVISION_TYPE')
 need(type(c['guid']) is str and re.fullmatch(r'[0-3][0-9A-Za-z_$]{21}',c['guid']),'GUID_FORMAT')
 need(c['op'] in ['translate','rename','status'],'UNSUPPORTED_OPERATION')
 if c['op']=='translate':finite_vector(c['value'],3,2.)
 else:need(type(c['value']) is str and 0<len(c['value'])<=120 and all(ord(x)>=32 for x in c['value']),'TEXT_VALUE')
 if c['op']=='status':need(c['value'] in ['Reviewed','Needs review','Approved'],'STATUS_VALUE')
 return c
def revision_transition(current,base,next_):need(base==current and next_==current+1,'REVISION_GAP')
def binding(source_sha,projection,shadow_sha):
 need(projection['source_sha256']==source_sha,'PROJECTION_SOURCE_DRIFT');need(projection['shadow_sha256']==shadow_sha,'STALE_LIGHTING')
def resource_path(root,value):
 from pathlib import Path
 need(type(value) is str and not re.match(r'[a-zA-Z][a-zA-Z0-9+.-]*:',value),'EXTERNAL_RESOURCE')
 p=(Path(root)/value).resolve();need(p.is_relative_to(Path(root).resolve()),'PATH_ESCAPE');return p
