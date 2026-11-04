from pathlib import Path
import sys,tempfile,unittest,hashlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from scene_contracts import *
class Contracts(unittest.TestCase):
 def test_asset_base_is_scene_not_document(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'scenes').mkdir();(p/'tex').mkdir();(p/'tex/a.png').write_bytes(b'fixture')
   s=p/'scenes/a.x3d';s.write_text('<X3D><Scene><ImageTexture url="&quot;../tex/a.png&quot;"/></Scene></X3D>')
   self.assertTrue(all(r['pass'] for r in scene_assets(s,p)))
   wrong=p/'a.x3d';wrong.write_bytes(s.read_bytes());self.assertFalse(all(r['pass'] for r in scene_assets(wrong,p)))
 def test_missing_asset_is_not_ready(self):
  with tempfile.TemporaryDirectory() as d:
   s=Path(d)/'a.x3d';s.write_text('<X3D><Scene><ImageTexture url="&quot;missing.png&quot;"/></Scene></X3D>');self.assertFalse(scene_assets(s,d)[0]['pass'])
 def test_external_asset_requires_an_explicit_other_policy(self):
  with tempfile.TemporaryDirectory() as d:
   s=Path(d)/'a.x3d';s.write_text('<X3D><Scene><ImageTexture url="&quot;https://example.invalid/map.png&quot;"/></Scene></X3D>');self.assertEqual(scene_assets(s,d)[0]['status'],'external')
 def test_semantic_geometry_ignores_formatting_but_not_mutation(self):
  a=b'<X3D><Coordinate point="1 2 3"/></X3D>';b=b'<X3D>\n<Coordinate point="1  2   3"/></X3D>';c=b'<X3D><Coordinate point="1 2 4"/></X3D>'
  self.assertEqual(semantic_arrays(a),semantic_arrays(b));self.assertNotEqual(semantic_arrays(a),semantic_arrays(c))
 def test_old_identity_cannot_attest_new_bytes(self):
  h=hashlib.sha256(b'old').hexdigest();self.assertTrue(identity_matches(b'old',h));self.assertFalse(identity_matches(b'new',h));self.assertFalse(identity_matches(b'old',None))
 def test_join_is_not_first_similar_label(self):
  a={'id':'shape','label':'Shape','cls':'NodeType'};b={'id':'shape component','label':'Shape','cls':'NodeType'}
  self.assertEqual(unique_canonical_join('Shape',[b,a]),a);self.assertIsNone(unique_canonical_join('Shape',[a,dict(a)]));self.assertIsNone(unique_canonical_join('Shape',[b]))
if __name__=='__main__':unittest.main()
