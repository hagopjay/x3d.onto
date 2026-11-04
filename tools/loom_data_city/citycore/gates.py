"""Reusable source-to-scene truth gates. Explicit errors survive python -O."""
import csv,io,json,math,hashlib,re,xml.etree.ElementTree as ET
from decimal import Decimal,localcontext
from .core import HEADER,POLICY,CityError,require,canonical,sha

def verify(raw,m):
 checks=[]
 require(m['source_sha256']==sha(raw),'SOURCE_HASH','Source bytes differ')
 require(m['policy']==POLICY and m['policy_sha256']==sha(canonical(POLICY)),'POLICY_BINDING','Unknown parsing policy')
 checks.append('source_and_policy')
 # Separate reader and direct Decimal predicates: do not call the producer model.
 parser=csv.DictReader(io.StringIO(raw.decode('utf-8-sig'),newline=''),strict=True);_header=parser.fieldnames
 parsed=[];spans=[];last=parser.line_num;physical=raw.splitlines(keepends=True);offsets=[0]
 for line in physical:offsets.append(offsets[-1]+len(line))
 for p in parser:parsed.append(p);spans.append((offsets[last],offsets[parser.line_num],last+1,parser.line_num));last=parser.line_num
 require(len(parsed)==len(m['rows'])==len(m['glyphs']),'ROW_BIJECTION','Source, rows and glyphs must be one-to-one')
 require(len({r['id'] for r in m['rows']})==len(parsed),'ROW_BIJECTION','Duplicate emitted row')
 require({g['row_id'] for g in m['glyphs']}=={r['id'] for r in m['rows']},'ROW_BIJECTION','Glyph IDs disagree')
 require(len({g['pick_id'] for g in m['glyphs']})==len(parsed),'PICK_BIJECTION','Pick IDs duplicate')
 byid={g['row_id']:g for g in m['glyphs']}
 for metric in m['metrics']:
  expected_scale=max([abs(Decimal(r['value'])) for r in m['rows'] if r['metric']==metric and r['value'] is not None]+[Decimal(1)])
  require(Decimal(m['scales'][metric])==expected_scale,'SCALE_TRUTH',metric)
 for i,(p,r) in enumerate(zip(parsed,m['rows']),1):
  require(p==r['fields'] and r['id']==p['id'].strip(),'ROW_CONTENT',f'Record {i}')
  require(r['record']==i and 0<=r['byte_start']<r['byte_end']<=len(raw),'ROW_RANGE',r['id'])
  require((r['byte_start'],r['byte_end'],r['line_start'],r['line_end'])==spans[i-1],'ROW_RANGE',r['id'])
  piece=raw[r['byte_start']:r['byte_end']]
  require(sha(piece)==r['raw_sha256'] and sha(canonical(p))==r['canonical_sha256'],'ROW_HASH',r['id'])
  require(list(csv.reader(io.StringIO(piece.decode('utf-8'),newline=''),strict=True))==[[p[k] for k in HEADER]],'ROW_RANGE_CONTENT',r['id'])
  g=byid[r['id']]; token=p['value'].strip()
  if token.upper() in POLICY['missing_tokens']:
   require(r['state']==POLICY['missing_tokens'][token.upper()] and r['value'] is None,'UNKNOWN_COERCION',r['id'])
  else:
   numeric=bool(re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d{1,3})?',token))
   try:number=Decimal(token)
   except Exception:number=Decimal('NaN')
   with localcontext() as ctx:
    ctx.prec=128;places_ok=number.is_finite() and (not number or number.normalize().as_tuple().exponent>=-6)
   numeric=numeric and len(token)<=64 and number.is_finite() and number.copy_abs()<=Decimal(POLICY['max_abs_value']) and places_ok
   if numeric:require(r['state']=='measured' and r['value'] is not None and number==Decimal(r['value']),'VALUE_TRUTH',r['id'])
   else:require(r['state']=='invalid' and r['value'] is None,'INVALID_COERCION',r['id'])
  require(all(r[k]==p[k].strip() and g[k]==r[k] for k in ['district','period','metric','unit']),'DIMENSION_TRUTH',r['id'])
  require(g['pick_id']==i and g['node']==f'G{i}' and g['shape']==f'Body{i}','NODE_IDENTITY',r['id'])
  expected_x=(m['districts'].index(r['district'])-(len(m['districts'])-1)/2)*2.8
  expected_z=(m['periods'].index(r['period'])-(len(m['periods'])-1)/2)*3.25
  require(abs(g['position'][0]-expected_x)<1e-10 and abs(g['position'][2]-expected_z)<1e-10,'LAYOUT_TRUTH',r['id'])
  require(g['row_sha256']==r['raw_sha256'] and g['source_sha256']==m['source_sha256'],'GLYPH_LINEAGE',r['id'])
  require(sha(canonical({k:v for k,v in g.items() if k!='glyph_sha256'}))==g['glyph_sha256'],'GLYPH_HASH',r['id'])
  if r['value'] is None:
   require(g['kind']=='fog' and g['height'] is None and g['signed_value'] is None,'UNKNOWN_GEOMETRY',r['id'])
  else:
   n=Decimal(r['value']);expected=float(abs(n)/Decimal(m['scales'][r['metric']])*9)
   require(g['signed_value']==r['value'] and g['kind']==('zero' if n==0 else 'bar'),'VALUE_GEOMETRY',r['id'])
   require(isinstance(g['height'],(int,float)) and math.isfinite(g['height']) and abs(g['height']-expected)<1e-10,'HEIGHT_TRUTH',r['id'])
   if n: require(abs(g['position'][1]-(1 if n>0 else -1)*expected/2)<1e-10,'SIGN_TRUTH',r['id'])
 checks.extend(['row_bytes_and_content','row_glyph_bijection','unknown_is_not_zero','linear_height_and_sign'])
 expected_groups={(metric,district) for metric in m['metrics'] for district in m['districts']}
 require(len(m['groups'])==len(expected_groups) and {(a['metric'],a['district']) for a in m['groups']}==expected_groups,'GROUP_BIJECTION','District aggregate coverage')
 entries=[(metric,a,[r for r in m['rows'] if r['metric']==metric]) for metric,a in m['aggregates'].items()]
 entries.extend((a['metric']+'/'+a['district'],a,[r for r in m['rows'] if r['metric']==a['metric'] and r['district']==a['district']]) for a in m['groups'])
 for metric,agg,rows in entries:
  known=[Decimal(r['value']) for r in rows if r['value'] is not None]
  unknown=len(rows)-len(known)
  require(agg['rows']==len(rows) and agg['measured']==len(known) and agg['unknown']==unknown,'COVERAGE_TRUTH',metric)
  require((agg['observed_sum'] is None)==(not known),'EMPTY_SUM',metric)
  if known: require(Decimal(agg['observed_sum'])==sum(known),'AGGREGATE_TRUTH',metric)
  require(agg['complete_sum'] is None if unknown or not rows else agg['complete_sum']==agg['observed_sum'],'PARTIAL_TOTAL',metric)
  require(set(agg['contributor_ids'])=={r['id'] for r in rows if r['value'] is not None},'AGGREGATE_LINEAGE',metric)
  require(set(agg['unknown_ids'])=={r['id'] for r in rows if r['value'] is None},'AGGREGATE_LINEAGE',metric)
 checks.extend(['aggregate_truth','partial_total_is_unknown','aggregate_lineage'])
 return {'status':'pass','grade':'C','checks':checks,'rows':len(parsed)}

def verify_scene(xml,m):
 root=ET.fromstring(xml); defs={n.attrib['DEF']:n for n in root.iter() if 'DEF' in n.attrib};checks=[]
 require(not list(root.iter('Script')),'SCENE_SCRIPT','No executable Script nodes')
 for g in m['glyphs']:
  node=defs.get(g['node']);require(node is not None,'SCENE_NODE',g['node'])
  meta={n.get('name'):n.get('value') for n in node.iter('MetadataString')}
  require(meta.get('row_sha256')=='"'+g['row_sha256']+'"','SCENE_LINEAGE',g['node'])
  require(meta.get('row_id')=='"'+g['row_id']+'"','SCENE_LINEAGE',g['node'])
  require(meta.get('source_sha256')=='"'+g['source_sha256']+'"' and meta.get('glyph_sha256')=='"'+g['glyph_sha256']+'"','SCENE_LINEAGE',g['node'])
  require(meta.get('kind')=='"'+g['kind']+'"','SCENE_KIND',g['node'])
  require(all(abs(float(a)-b)<1e-8 for a,b in zip(node.get('translation').split(),g['position'])),'SCENE_POSITION',g['node'])
  body=defs.get(g['shape']);require(body is not None,'SCENE_BODY',g['node'])
  if g['kind']=='bar':
   geom=body.find('Box');require(geom is not None,'SCENE_GEOMETRY',g['node'])
   h=float(geom.get('size').split()[1]);require(abs(h-g['height'])<1e-8,'SCENE_HEIGHT',g['node'])
  else:
   require(body.find('Box') is None,'UNKNOWN_BOX','Fog and zero are semantic markers, not boxes')
   points=[float(v) for v in body.find('IndexedFaceSet/Coordinate').get('point').split()]
   require(len(points)==12,'MARKER_TOPOLOGY',g['node'])
   require(all(v==0 for v in points[1::3]) if g['kind']=='zero' else all(v==0 for v in points[2::3]),'MARKER_TOPOLOGY',g['node'])
  shader=defs.get('Shader'+str(g['pick_id']));require(shader is not None,'SCENE_SHADER',g['node'])
  require(float(shader.find('field[@name="u_fog"]').get('value'))==(1 if g['kind']=='fog' else 0),'FOG_SHADER_BINDING',g['node'])
 checks=['scene_metadata_lineage','scene_geometry_matches_manifest','unknown_has_no_box','no_script_nodes']
 return {'status':'pass','grade':'C','checks':checks}
