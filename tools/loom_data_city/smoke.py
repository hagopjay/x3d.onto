from pathlib import Path
import copy,json
from citycore.core import CityError,require
from citycore.gates import verify,verify_scene
root=Path(__file__).parent
raw=(root/'fixture.csv').read_bytes();m=json.loads((root/'manifest.json').read_text())
verify(raw,m);verify_scene((root/'world.x3d').read_bytes(),m)
bad=copy.deepcopy(m);bad['rows'][2]['value']='0';bad['rows'][2]['state']='measured'
try:verify(raw,bad)
except CityError as e:require(e.code=='UNKNOWN_COERCION','WRONG_DIAGNOSTIC',e.code)
else:raise RuntimeError('Unknown-to-zero mutation escaped')
print('PASS: valid source/scene accepted; missing-to-zero rejected')
