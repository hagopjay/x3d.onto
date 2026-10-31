"""python3 -I test_scene_look.py : the static scene gates and the pixel look gates, on injected faults and on clean inputs."""
import os, sys, tempfile, unittest
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import scenegates as S, lookgates as L

HEAD = "<?xml version='1.0' encoding='UTF-8'?>\n<X3D profile='Interchange' version='4.0'><head/><Scene>"
OK = HEAD + """<Transform DEF='P1'><Shape><Appearance><Material diffuseColor='1 0.84 0'/></Appearance><Sphere/></Shape></Transform>
<TimeSensor DEF='T' loop='true'/><PositionInterpolator DEF='I' key='0 1' keyValue='0 0 0 0 1 0'/>
<ROUTE fromNode='T' fromField='fraction_changed' toNode='I' toField='set_fraction'/>
<ROUTE fromNode='I' fromField='value_changed' toNode='P1' toField='set_translation'/>
<Transform USE='P1'/></Scene></X3D>"""


def gates_of(xml, **kw):
    with tempfile.NamedTemporaryFile('w', suffix='.x3d', delete=False) as f: f.write(xml); p = f.name
    try: return [x['gate'] for x in S.check(p, **kw)['findings']], S.check(p, **kw)
    finally: os.unlink(p)


class Scene(unittest.TestCase):
    def test_clean(self): self.assertEqual(gates_of(OK)[0], [])
    def test_colour_out_of_range_names_the_value(self):
        g, r = gates_of(OK.replace("diffuseColor='1 0.84 0'", "diffuseColor='1.0059 0.84 0'"))
        self.assertEqual(g, ['S4-colour-range']); self.assertEqual(r['findings'][0]['value'], 1.0059)
        g, r = gates_of(OK.replace("<Sphere/>", "<IndexedFaceSet coordIndex='0 1 2 -1'><Coordinate point='0 0 0 1 0 0 0 1 0'/><Color color='0.2 0.2 0.2 0.5 0.5 1.0511 0 0 0'/></IndexedFaceSet>"))
        self.assertEqual(r['findings'][0]['index'], 5)
    def test_route_before_node(self):
        bad = OK.replace("<Transform DEF='P1'>", "<ROUTE fromNode='I' fromField='value_changed' toNode='P1' toField='set_translation'/><Transform DEF='P1'>", 1)
        self.assertIn('S3-route-order', gates_of(bad)[0])
    def test_def_twice_and_use_first(self):
        self.assertIn('S1-def-unique', gates_of(OK.replace("DEF='T'", "DEF='P1'"))[0])
        self.assertIn('S2-use-after-def', gates_of(OK.replace("<Scene>", "<Scene><Group USE='P1'/>", 1))[0])
    def test_proto_scope_may_reuse_a_name(self):
        proto = OK.replace("<Scene>", "<Scene><ProtoDeclare name='Star'><ProtoBody><Transform DEF='P1'/></ProtoBody></ProtoDeclare>", 1)
        self.assertEqual(gates_of(proto)[0], [])
    def test_size_budget(self): self.assertIn('S5-size', gates_of(OK, budget_gz=100)[0])


def canvas(w=320, h=200, bg=(15, 13, 12)): return np.tile(np.array(bg, np.uint8), (h, w, 1))


class Look(unittest.TestCase):
    def test_black_and_background_only_fail(self):
        self.assertFalse(L.nonblack(canvas(bg=(0, 0, 0)))['ok']); self.assertFalse(L.nonblack(canvas())['ok'])
    def test_sparse_starfield_needs_its_golden_frame(self):
        img = canvas(); rng = np.random.default_rng(1)
        for x, y in zip(rng.integers(0, 320, 120), rng.integers(0, 200, 120)): img[y:y + 2, x:x + 2] = (255, 215, 90)
        self.assertFalse(L.nonblack(img)['ok'])                                  # 1.5% lit: the absolute floor would retake it ...
        gold = L.frame_stats(img); self.assertTrue(L.nonblack(img, golden=gold)['ok'])   # ... the stop's golden frame says it is right
        self.assertFalse(L.nonblack(canvas(), golden=gold)['ok'])                 # and a stalled frame still fails against the golden frame
    def test_node_recall(self):
        img = canvas(); pts = [('p%d' % i, 20 + 30 * i, 100) for i in range(10)]
        for pid, x, y in pts[:8]: img[y - 1:y + 2, x - 1:x + 2] = (255, 215, 90)
        r = L.node_recall(img, pts + [('off', -5, 10)]); self.assertEqual((r['onscreen'], r['seen'], r['missed']), (10, 8, ['p8', 'p9']))
    def test_labels(self):
        m = L.label_metrics([('a', 10, 10, 100, 14), ('b', 60, 15, 100, 14), ('c', 300, 180, 40, 9)], 320, 200)
        self.assertEqual(m['overlapping'], ['a', 'b']); self.assertEqual(m['too_small'], ['c']); self.assertEqual(m['offscreen'], ['c']); self.assertGreater(m['overlap_share'], 0.1)
        self.assertAlmostEqual(L.contrast(canvas(bg=(0, 0, 0)), ('x', 0, 0, 10, 10), (255, 255, 255)), 21.0, places=3)

if __name__ == '__main__': unittest.main(verbosity=1)
