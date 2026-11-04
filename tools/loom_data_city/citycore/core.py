"""Strict CSV ingestion, exact decimal semantics, and a deterministic visual model.

Only the standard library is used. Unknown values remain None throughout.
Raw record hashes cover the original UTF-8 bytes, including record terminators.
"""
import csv, hashlib, io, json, re
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path

HEADER = ['id','district','period','metric','value','unit','note']
POLICY = {
 'schema':'data-city.policy/1', 'encoding':'UTF-8; optional BOM',
 'header':HEADER, 'max_bytes':131072, 'max_rows':128,
 'missing_tokens':{'':'missing','NA':'not_available','NULL':'missing','SUPPRESSED':'suppressed','?':'unreported','--':'missing'},
 'max_abs_value':'1000000', 'max_decimal_places':6,'max_numeric_chars':64,
 'unknown_rule':'Unknown is null and has no magnitude; fog is a fixed semantic marker, not an interval.',
 'zero_rule':'Measured zero is an outlined ground marker with height exactly zero.',
 'negative_rule':'Negative measured values extend below the zero plane.',
 'aggregate_rule':'Observed sum excludes unknowns; complete sum is null unless every input is measured.',
 'mean_rule':'Observed means use Decimal division at 28 significant digits, ROUND_HALF_EVEN; sums remain exact within the declared domain.',
 'scaling_rule':'Linear, zero-anchored, per metric across all periods. No clipping; max absolute value maps to 9 world units.',
 'units_rule':'Exactly one unit per metric. Aggregation never crosses metrics.',
}

class CityError(ValueError):
 def __init__(self, code, detail):
  self.code=code; self.detail=detail; super().__init__(f'{code}: {detail}')

def require(ok, code, detail):
 if not ok: raise CityError(code,detail)

def canonical(value):
 return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')

def sha(data): return hashlib.sha256(data).hexdigest()
def decimal_text(n):
 if not n: return '0'
 return format(n.normalize(),'f')

def classify(token):
 t=token.strip()
 if t.upper() in POLICY['missing_tokens']:
  return {'state':POLICY['missing_tokens'][t.upper()], 'value':None,'reason':'Declared missing token'}
 if len(t)>POLICY['max_numeric_chars']:return {'state':'invalid','value':None,'reason':'Numeric token exceeds 64 characters'}
 if not re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d{1,3})?',t):
  return {'state':'invalid','value':None,'reason':'Not a finite decimal literal'}
 try: n=Decimal(t)
 except InvalidOperation: return {'state':'invalid','value':None,'reason':'Decimal conversion failed'}
 if not n.is_finite() or n.copy_abs()>Decimal(POLICY['max_abs_value']):
  return {'state':'invalid','value':None,'reason':'Outside declared finite numeric domain'}
 with localcontext() as ctx:
  ctx.prec=128;exponent=n.normalize().as_tuple().exponent
 if n and exponent < -POLICY['max_decimal_places']:
  return {'state':'invalid','value':None,'reason':'More than six decimal places'}
 return {'state':'measured','value':decimal_text(n),'reason':'Finite decimal parsed without imputation'}

def ingest(raw):
 require(isinstance(raw,bytes),'SOURCE_TYPE','Expected original bytes')
 require(0<len(raw)<=POLICY['max_bytes'],'SOURCE_SIZE','CSV must be 1–131072 bytes')
 try: text=raw.decode('utf-8-sig')
 except UnicodeError as e: raise CityError('UTF8_REQUIRED',str(e))
 require(not any(ord(c)<32 and c not in '\r\n\t' for c in text),'CONTROL_CHARACTER','Control character in source')
 # Physical lines retain terminators. csv.reader.line_num gives each logical
 # record's physical span, including embedded quoted newlines.
 lines=raw.splitlines(keepends=True); offsets=[0]
 for line in lines: offsets.append(offsets[-1]+len(line))
 reader=csv.reader(io.StringIO(text,newline=''),strict=True)
 try: header=next(reader)
 except (StopIteration,csv.Error) as e: raise CityError('CSV_HEADER',str(e))
 require(header==HEADER,'CSV_HEADER','Expected '+','.join(HEADER))
 previous=reader.line_num; rows=[]; ids=set(); keys=set(); units={}
 try:
  for ordinal,values in enumerate(reader,1):
   end=reader.line_num; start=previous; previous=end
   require(len(values)==len(HEADER),'CSV_WIDTH',f'Record {ordinal}: expected seven fields')
   require(ordinal<=POLICY['max_rows'],'ROW_LIMIT','At most 128 records')
   require(all(len(v)<=512 for v in values),'FIELD_SIZE',f'Record {ordinal}: field exceeds 512 characters')
   fields=dict(zip(HEADER,values)); entity=fields['id'].strip()
   require(bool(re.fullmatch(r'[A-Za-z0-9_.:-]{1,80}',entity)),'ROW_ID','ID must be 1–80 ASCII identifier characters')
   require(entity not in ids,'DUPLICATE_ID',entity);ids.add(entity)
   for key in ['district','metric','unit']:
    require(bool(fields[key].strip()),'EMPTY_DIMENSION',f'{entity}: {key}')
   require(bool(re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])',fields['period'].strip())),'PERIOD_FORMAT',entity)
   dims={k:fields[k].strip() for k in ['district','period','metric','unit']}
   key=tuple(dims[k] for k in ['district','period','metric'])
   require(key not in keys,'DUPLICATE_CELL',str(key));keys.add(key)
   require(dims['metric'] not in units or units[dims['metric']]==dims['unit'],'MIXED_UNITS',dims['metric'])
   units[dims['metric']]=dims['unit']
   chunk=raw[offsets[start]:offsets[end]]
   rows.append({'id':entity,**dims,'raw_value':fields['value'],'note':fields['note'],
    **classify(fields['value']), 'record':ordinal,'line_start':start+1,'line_end':end,
    'byte_start':offsets[start],'byte_end':offsets[end], 'raw_sha256':sha(chunk),
    'canonical_sha256':sha(canonical(fields)), 'fields':fields})
 except csv.Error as e: raise CityError('CSV_SYNTAX',str(e))
 require(bool(rows),'EMPTY_SOURCE','At least one data record is required')
 return {'source_sha256':sha(raw),'source_bytes':len(raw),'rows':rows,'units':units}

def summarize(rows):
 known=[Decimal(r['value']) for r in rows if r['state']=='measured']
 total=sum(known,Decimal(0)); unknown=len(rows)-len(known)
 states={}
 for r in rows: states[r['state']]=states.get(r['state'],0)+1
 with localcontext() as ctx:
  ctx.prec=28;ctx.rounding='ROUND_HALF_EVEN';mean=decimal_text(total/len(known)) if known else None
 return {'rows':len(rows),'measured':len(known),'unknown':unknown,'states':states,
  'zero_count':sum(v==0 for v in known),'negative_count':sum(v<0 for v in known),
  'observed_sum':decimal_text(total) if known else None,
  'complete_sum':decimal_text(total) if rows and not unknown else None,
  'observed_mean':mean,'mean_precision_digits':28,
  'coverage':{'numerator':len(known),'denominator':len(rows)},
  'contributor_ids':[r['id'] for r in rows if r['state']=='measured'],
  'unknown_ids':[r['id'] for r in rows if r['state']!='measured']}

def model(raw):
 source=ingest(raw);rows=source['rows']; districts=sorted({r['district'] for r in rows});periods=sorted({r['period'] for r in rows});metrics=sorted(source['units'])
 require(len(districts)<=16 and len(periods)<=12 and len(metrics)<=8,'DIMENSION_LIMIT','Maximum 16 districts, 12 periods, 8 metrics')
 scales={m:max([abs(Decimal(r['value'])) for r in rows if r['metric']==m and r['value'] is not None]+[Decimal(1)]) for m in metrics}
 glyphs=[]
 for i,row in enumerate(rows,1):
  value=Decimal(row['value']) if row['value'] is not None else None
  kind='fog' if value is None else 'zero' if value==0 else 'bar'
  h=float(abs(value)/scales[row['metric']]*9) if value is not None else None
  sign=-1 if value is not None and value<0 else 1
  x=(districts.index(row['district'])-(len(districts)-1)/2)*2.8
  z=(periods.index(row['period'])-(len(periods)-1)/2)*3.25
  glyph={'row_id':row['id'],'pick_id':i,'node':f'G{i}','shape':f'Body{i}','kind':kind,
   'position':[x,sign*h/2 if kind=='bar' else 0,z], 'height':h,'signed_value':row['value'],
   'source_sha256':source['source_sha256'],'row_sha256':row['raw_sha256'],
   'metric':row['metric'],'district':row['district'],'period':row['period'],'unit':row['unit']}
  glyph['glyph_sha256']=sha(canonical(glyph));glyphs.append(glyph)
 aggregates={m:summarize([r for r in rows if r['metric']==m]) for m in metrics}
 groups=[{'metric':m,'district':d,'unit':source['units'][m],**summarize([r for r in rows if r['metric']==m and r['district']==d])} for m in metrics for d in districts]
 return {'schema':'data-city.manifest/1',**source,'policy':POLICY,'policy_sha256':sha(canonical(POLICY)),
  'districts':districts,'periods':periods,'metrics':metrics,'scales':{m:decimal_text(v) for m,v in scales.items()},
  'glyphs':glyphs,'aggregates':aggregates,'groups':groups,'data_label':'User-provided data; not independently verified'}

def compare(a,b):
 aa={r['id']:r for r in a['rows']};bb={r['id']:r for r in b['rows']};changes=[]
 for key in sorted(aa.keys()|bb.keys()):
  x,y=aa.get(key),bb.get(key)
  state='added' if x is None else 'removed' if y is None else 'unchanged' if x['canonical_sha256']==y['canonical_sha256'] else 'changed'
  changes.append({'id':key,'change':state,'before':None if x is None else {k:x[k] for k in ['state','value','raw_sha256']},'after':None if y is None else {k:y[k] for k in ['state','value','raw_sha256']}})
 return {'schema':'data-city.diff/1','from':a['source_sha256'],'to':b['source_sha256'],'rows':changes,'counts':{s:sum(x['change']==s for x in changes) for s in ['added','removed','changed','unchanged']}}
