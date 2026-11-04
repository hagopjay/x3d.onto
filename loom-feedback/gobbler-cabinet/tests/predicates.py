import unittest,hashlib,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from gates import inspect,accumulated_opacity,observed_arrival
GOOD=b'<X3D><Scene><Shape><Appearance><ComposedShader DEF="Ribbon"/></Appearance><IndexedFaceSet coordIndex="0 0 1 1 -1"><Tangent vector="1 0 0 1"/></IndexedFaceSet></Shape><Inline DEF="World" load="false"/></Scene></X3D>'
def check(xml,allowed=('Ribbon',)):return inspect(xml,hashlib.sha256(xml).hexdigest(),allowed)
class Predicates(unittest.TestCase):
 def test_allowed_counterexample(self):self.assertEqual(check(GOOD),[])
 def test_unknown_interpretation(self):self.assertTrue(any('unexplained' in x for x in check(GOOD,())))
 def test_missing_basis(self):self.assertTrue(any('explicit basis' in x for x in check(GOOD.replace(b'<Tangent vector="1 0 0 1"/>',b''))))
 def test_stale(self):self.assertTrue(any('L-ID' in x for x in inspect(GOOD,'stale',('Ribbon',))))
 def test_duplicate(self):self.assertTrue(any('L-DEF' in x for x in check(GOOD.replace(b'</Scene>',b'<Group DEF="World"/></Scene>'))))
 def test_owner(self):self.assertTrue(any('L-OWNER' in x for x in check(GOOD.replace(b'</Scene>',b'<ROUTE toNode="World" toField="load"/></Scene>'))))
 def test_shader(self):self.assertTrue(any('L-GLSL' in x for x in check(GOOD.replace(b'</Scene>',b'<ShaderPart>smoothstep(1.0,0.0,x)</ShaderPart></Scene>'))))
 def test_layer_composite(self):self.assertGreater(accumulated_opacity(.72,12),.98);self.assertLess(accumulated_opacity(.965,12),.35)
 def test_observed_camera(self):
  self.assertTrue(observed_arrival([1,2,3],[1,2,3.000001],.00001));self.assertFalse(observed_arrival([1,2,3],[1,2,4],.00001));self.assertFalse(observed_arrival([1,2,3],[1,2,float('nan')],.00001))
 def test_zero_layers(self):self.assertEqual(accumulated_opacity(.5,0),0)
 def test_invalid_alpha(self):
  with self.assertRaises(ValueError):accumulated_opacity(1.1,2)
if __name__=='__main__':unittest.main()
