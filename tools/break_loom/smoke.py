from loomlab.core import cards,require
from loomlab.generate import build_case,scene,source,EPOCH
from loomlab.witnesses import run_local
count=0
for c in cards():
 for v in ['mutant','control']:
  f=build_case(c,v);alt=scene(c['id'],v=='mutant',source(),EPOCH+259200) if c['id']=='08-clock' else None
  r=run_local(f,alt,include_grammar=False)
  if v=='control':require(all(x['status'] in ['pass','not_applicable'] for x in r.values()),'CONTROL_FALSE_POSITIVE',c['id'])
  elif c['owner'] not in ['Behaviour','Eyes','Host']:require(r[c['owner']]['diagnostic']==c['diagnostic'],'OWNER_MISS',c['id'])
  count+=1
print('PASS:',count,'paired local specimens; XSD and rendering require the full bundle')
