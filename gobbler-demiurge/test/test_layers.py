"""python3 -I test/test_layers.py : the layers are deterministic, match the plan's counts, and compose in the right place (needs make v4-data first)."""
import os, re, sys, unittest, hashlib
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); REPO = os.path.dirname(ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import layers, build_bird
EXP = os.path.join(REPO, 'data', 'explorer.json'); DEEP = os.path.join(REPO, 'gobbler-v4', 'data', 'deep', 'gobbler3.x3d')

class T(unittest.TestCase):
    def test_deterministic(self):
        a = layers.build(EXP); b = layers.build(EXP)
        self.assertEqual(hashlib.sha256(a['sway'].encode()).hexdigest(), hashlib.sha256(b['sway'].encode()).hexdigest())
        self.assertNotEqual(a['sway'], layers.build(EXP, seed=5)['sway'])
    def test_counts_match_the_plan(self):
        L = layers.build(EXP); x = L['sway']
        self.assertEqual(L['counts']['beads'], 364)                                   # one gem per ontology class
        self.assertEqual(len(re.findall(r"<LOD DEF='Fan\d+'", x)), 18)                 # tail fan: 18 plumes
        self.assertEqual(len(re.findall(r"<LOD DEF='Wing\d+'", x)), 10)                # 10 primaries
        self.assertEqual(len(re.findall(r"<Transform DEF='TenderOrbit\d+'", x)), 10)
        self.assertEqual(len(re.findall(r"<Group DEF='TenderBody\d'>", x)), 3); self.assertEqual(len(re.findall(r"<Group USE='TenderBody\d'/>", x)), 7)   # three H-Anim copies, shared by USE
        self.assertEqual(x.count('<HAnimHumanoid'), 3); self.assertEqual(len(re.findall(r'<HAnimJoint DEF="hanim_T\d_\w+"', x)), 54)   # 18 joints each
        ids = {a['id'] for a in L['anchors']}; self.assertEqual(len(L['anchors']), 15)
        for t in ('fan_gltf', 'fan_usd', 'fan_video', 'fan_o3de', 'fan_paraview', 'fan_3dslicer', 'fan_unity', 'fan_defold', 'fan_ifc'): self.assertIn(t, ids)
        self.assertEqual(sum(1 for a in L['anchors'] if a['id'].startswith('fan_') and 'mock' in a['tag']), 6)   # six mocks, tagged
        self.assertEqual(sum(1 for a in L['anchors'] if a['id'].startswith('fan_') and a['tag'].startswith('Blender export')), 3)
    def test_glow_shader_defined_once_per_build(self):
        x = layers.build(EXP)['sway']; self.assertEqual(x.count("<ComposedShader DEF='GlowShader'"), 1); self.assertGreater(x.count("<ComposedShader USE='GlowShader'/>"), 1)
    def test_point_sprite_alpha_encoding(self):
        for kind in range(4):
            for size in (0.9, 2.1, 3.9):
                a = layers.alpha(kind, size); self.assertEqual(int(a * 4 + 0.001), kind); self.assertAlmostEqual((a - kind * .25) * 16, size, places=6)
        with self.assertRaises(AssertionError): layers.alpha(1, 4.0)
    def test_compose_adds_never_edits(self):
        deep = open(DEEP, encoding='utf-8').read(); L = layers.build(EXP); out = build_bird.compose(deep, L)
        self.assertLess(out.index("<Viewpoint DEF='Face'"), out.index("<Viewpoint DEF='Wide'"))           # Face binds at load
        out2 = out.replace(L['viewpoints'] + '\n    ', '', 1).replace('    ' + L['component'] + '\n', '', 1); m = out2.index('\n    <!-- Gobbler demiurge layers'); k = out2.rindex('</Scene>')
        rest = out2[:m] + out2[k:]                                                                         # drop the three insertions (viewpoints, the HAnim component statement, the layers block)
        self.assertEqual(rest, deep)                                                                       # everything else is the Deep scene, byte for byte
        for nm in ('PointShader', 'SwayTurn', 'Twinkle', 'Intro', 'Probe'): self.assertIn("DEF='%s'" % nm, deep)
    def test_every_use_follows_its_def(self):
        deep = open(DEEP, encoding='utf-8').read(); out = build_bird.compose(deep, layers.build(EXP)); seen = set()
        for m in re.finditer(r"(DEF|USE)='([^']+)'", out):
            if m.group(1) == 'DEF': seen.add(m.group(2))
            else: self.assertIn(m.group(2), seen, 'USE before DEF: ' + m.group(2))
if __name__ == '__main__': unittest.main()
