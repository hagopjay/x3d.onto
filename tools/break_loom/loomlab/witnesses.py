"""Read the emitted representation; never infer a verdict from a case label."""
import base64,collections,io,json,math,struct,wave,xml.etree.ElementTree as ET
from functools import lru_cache
from pathlib import Path
from .core import ROOT,WITNESSES,GateError,require,canonical,sha,read,result,na

@lru_cache(maxsize=1)
def schema():
 from lxml import etree
 return etree.XMLSchema(etree.parse(str(ROOT/'vendor/schema/x3d-4.0.xsd')))
def grammar(xml):
 from lxml import etree
 s=schema();valid=s.validate(etree.fromstring(xml))
 return result('Grammar',None if valid else 'XSD_INVALID',str(s.error_log) if not valid else 'XSD 4.0 accepts this XML.',schema_sha256=sha((ROOT/'vendor/schema/x3d-4.0.xsd').read_bytes()))
def meaning(tree):
 seen={};issues=[]
 for node in tree.iter():
  if node.tag=='ROUTE':
   for attr in ['fromNode','toNode']:
    if node.get(attr) not in seen:issues.append({'node':node.get(attr),'position':'before DEF','field':attr})
  if node.get('DEF'):seen[node.get('DEF')]=node.tag
 return result('Meaning','ROUTE_ORDER' if issues else None,'Order-aware XML ROUTE lookup; not the unavailable x3d_mcp fork.',issues=issues,definitions=len(seen))
def traps(tree,contract):
 raw=[]
 for p in tree.findall('.//ShaderPart'):
  u=p.get('url','')
  if ('void main' in u or '#version' in u) and not any(k in u for k in ['data:','http:','https:']):raw.append(p.get('DEF','unnamed'))
 if raw:return result('Traps','SHADER_RAW_SOURCE','GLSL text used as an unprefixed URL entry.',nodes=raw)
 white=[]
 if contract.get('palette_required'):
  for shape in tree.findall('.//Shape'):
   mat=shape.find('./Appearance/Material')
   if shape.find('.//Color') is not None and mat is not None and all(float(v)>.98 for v in mat.get('emissiveColor','0 0 0').split()):white.append(True)
 return result('Traps','PALETTE_EMISSIVE_WHITE' if white else None,'Only explicit palette-preservation contracts activate the white-emission rule.',affected_shapes=len(white))
def receipts(files,clock_alternative=None):
 r=json.loads(files['receipt.json']);drift=[]
 if set(r.get('outputs',{}))!=set(files)-{'receipt.json'}:drift.append('output inventory incomplete or extraneous')
 for name,expected in r.get('outputs',{}).items():
  if name not in files or sha(files[name])!=expected:drift.append(name)
 if not r.get('outputs') or 'scene.x3d' not in r['outputs']:drift.append('required scene output absent')
 src=json.loads(files['source.json'])
 if r.get('source_sha256')!=sha(canonical(src)):drift.append('source identity')
 if drift:return result('Receipts','RECEIPT_SUBJECT','Receipt bytes differ from the delivered specimen.',drift=drift)
 if clock_alternative is not None and files['scene.x3d']!=clock_alternative:return result('Receipts','REBUILD_CLOCK_DRIFT','Declared inputs fixed; injected wall clock moved by three days.',before=sha(files['scene.x3d']),after=sha(clock_alternative),clock_delta_seconds=259200)
 return result('Receipts',detail='Output hashes match; declared clock perturbation passes where applicable.',outputs=len(r['outputs']),clock_test=clock_alternative is not None)
def truth(src,mapping,tree):
 records={r['id']:r['value'] for r in src['records']};derived={r['id']:r['value'] for r in mapping}
 if set(records)!=set(derived):return result('Truth','ROW_BIJECTION',source_ids=sorted(records),derived_ids=sorted(derived))
 geometry={};occurrences=[]
 for m in tree.findall('.//MetadataSet[@name="mapping"]'):
  fields={n.get('name'):json.loads(n.get('value')) for n in m.findall('MetadataString')};occurrences.append(fields['row_id']);geometry[fields['row_id']]={'value':json.loads(fields['value']),'kind':fields['kind']}
 if collections.Counter(occurrences)!=collections.Counter(records.keys()):return result('Truth','ROW_BIJECTION',detail='Source rows and actual geometry must correspond one-to-one.')
 for key,value in records.items():
  if value is None and (derived[key] is not None or geometry.get(key,{}).get('value','absent') is not None or geometry.get(key,{}).get('kind')!='fog'):
   return result('Truth','UNKNOWN_COERCION','Null source acquired an invented numeric value or a numeric marker.',id=key,source=value,model=derived[key],geometry=geometry.get(key))
  if value is not None and (derived[key]!=value or geometry.get(key,{}).get('value')!=value):return result('Truth','VALUE_CHANGED',id=key)
  if value==0 and geometry.get(key,{}).get('kind')!='zero':return result('Truth','ZERO_LOST',id=key)
 return result('Truth',detail='Independent source/model/XML comparison preserves null and measured zero.',rows=len(records))
def budget(ledger):
 require(ledger.get('synthetic') is True,'LEDGER_SCOPE','Only the supplied synthetic ledger is supported.')
 seen=set();total=0;duplicates=[]
 for c in ledger['calls']:
  key=sha(canonical(c['request']))
  if key!=c['request_key']:return result('Budget','REQUEST_KEY',detail='Declared identity does not match the complete request.')
  cost=c['paid_microcredits']
  if not isinstance(cost,int) or isinstance(cost,bool) or cost<0:return result('Budget','INVALID_COST')
  if c['cache_hit'] and cost!=0:return result('Budget','BILLED_CACHE_HIT')
  total+=cost
  if cost:
   if key in seen:duplicates.append(key)
   seen.add(key)
 if duplicates:return result('Budget','DUPLICATE_PAID_CALL','Identical model/prompt/parameters/inputs billed more than once.',duplicates=duplicates,total_microcredits=total,cap_microcredits=ledger['cap_microcredits'])
 return result('Budget','BUDGET_EXCEEDED' if total>ledger['cap_microcredits'] else None,total_microcredits=total,cap_microcredits=ledger['cap_microcredits'])
def ear(data):
 with wave.open(io.BytesIO(data),'rb') as w:
  require(w.getsampwidth()==2 and w.getnchannels()==1,'PCM_FORMAT','Expected mono PCM16.');rate=w.getframerate();n=w.getnframes();s=struct.unpack('<'+'h'*n,w.readframes(n))
 peak=max(abs(x) for x in s)/32768 if s else 0;rail=sum(abs(x)>=32767 for x in s)/max(1,len(s));db=20*math.log10(peak) if peak else None
 bad=rail>.001 or (db is not None and db>-1)
 envelope=[max(abs(x) for x in s[i:i+882])/32768 for i in range(0,n,882)]
 return result('Ear','PCM_CLIPPING' if bad else None,'Decoded PCM sample measurements, not LUFS or true-peak.',sample_peak_dbfs=db,rail_fraction=rail,duration_seconds=n/rate,rate=rate,samples=n,envelope=envelope)
def score(src,tree):
 expected=[(e['id'],e['onset']) for e in src['events']];actual=[]
 for m in tree.findall('.//MetadataSet[@name="score"]'):
  node=m.find('MetadataString[@name="event_id"]');on=m.find('MetadataDouble[@name="onset"]')
  if node is not None and on is not None:actual.append((json.loads(node.get('value')),float(on.get('value'))))
 missing=list((collections.Counter(expected)-collections.Counter(actual)).elements());extra=list((collections.Counter(actual)-collections.Counter(expected)).elements())
 return result('Score','EVENT_BIJECTION' if missing or extra else None,'Compared actual scene metadata with source event identities and onsets.',source_count=len(expected),scene_count=len(actual),missing=missing,extra=extra)
def run_local(files,clock_alternative=None,include_grammar=True):
 contract=json.loads(files['contract.json']);cid=contract['case_id'];tree=ET.fromstring(files['scene.x3d']);src=json.loads(files['source.json'])
 out={w:na(w) for w in WITNESSES}
 if include_grammar:
  try:out['Grammar']=grammar(files['scene.x3d'])
  except ImportError:out['Grammar']={'witness':'Grammar','status':'error','diagnostic':'INSTRUMENT_UNAVAILABLE','detail':'Install requirements-witness.txt for a fresh XSD run.','grade':None,'measurements':{}}
 out.update(Meaning=meaning(tree),Traps=traps(tree,contract),Receipts=receipts(files,clock_alternative),Budget=budget(json.loads(files['budget.json'])))
 if cid=='09-unknown':out['Truth']=truth(src,json.loads(files['mapping.json']),tree)
 if cid=='11-ear':out['Ear']=ear(files['audio.wav'])
 if cid=='12-score':out['Score']=score(src,tree)
 return out
def load_files(path):return {p.name:p.read_bytes() for p in Path(path).iterdir() if p.is_file()}
