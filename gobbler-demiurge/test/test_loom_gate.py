"""python3 -I test/test_loom_gate.py : every gate rule on a tiny inline scene (one that should trip it, one that should not), the receipt tool, and the gate over the committed assets."""
import os, sys, json, glob, shutil, tempfile, unittest, contextlib, io
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import loom_gate, loom_receipt


def X(body, head='', gen=False):
    meta = "<meta name='generator' content='X3D Blender I/O v2.6.1'/>" if gen else ''
    return "<?xml version='1.0' encoding='UTF-8'?>\n<X3D profile='Immersive' version='4.0'>\n<head>%s%s</head>\n<Scene>\n%s\n</Scene>\n</X3D>\n" % (head, meta, body)

def put(p, s):
    with open(p, 'w', encoding='utf-8') as fh: fh.write(s)
def get(p):
    with open(p, encoding='utf-8') as fh: return fh.read()
def rules(text, **k): return [d['rule'] for d in loom_gate.gate(text, **k)]
def only(text, rule, **k): return [d for d in loom_gate.gate(text, **k) if d['rule'] == rule]

SHADER = """<Shape><Appearance><ComposedShader DEF='S' language='GLSL'>%s
<ShaderPart type='FRAGMENT'><![CDATA[data:x-shader/x-fragment,#version 300 es
precision highp float;
uniform float t;
in vec3 v;
out vec4 x3d_FragColor;
void main() {
  float h[4];
  for (int i = 0; i < 4; i++) { h[i] = float(i) * 0.5; }
  vec3 w = vec3(1);
  %s
}
]]></ShaderPart></ComposedShader></Appearance><Sphere/></Shape>"""


class Gate(unittest.TestCase):
    def test_route_forward(self):
        bad = X("<ROUTE fromNode='C' fromField='fraction_changed' toNode='P' toField='set_fraction'/>\n<TimeSensor DEF='C'/>\n<PositionInterpolator DEF='P'/>")
        f = only(bad, 'route-forward'); self.assertEqual(len(f), 2); self.assertEqual(f[0]['line'], 5); self.assertEqual(f[0]['ref'], 'C'); self.assertEqual(f[0]['def_line'], 6)
        good = X("<TimeSensor DEF='C'/>\n<PositionInterpolator DEF='P'/>\n<ROUTE fromNode='C' fromField='fraction_changed' toNode='P' toField='set_fraction'/>")
        self.assertEqual(rules(good), [])
    def test_route_undefined(self):
        f = only(X("<TimeSensor DEF='C'/><ROUTE fromNode='C' fromField='isActive' toNode='Nope' toField='set_bind'/>"), 'route-undefined')
        self.assertEqual([d['ref'] for d in f], ['Nope']); self.assertEqual(f[0]['severity'], 'error')
        imp = X("<Inline DEF='I' url='\"a.x3d\"'/><IMPORT inlineDEF='I' importedDEF='T' AS='T2'/><TimeSensor DEF='C'/><ROUTE fromNode='C' fromField='isActive' toNode='T2' toField='enabled'/>")
        self.assertEqual(rules(imp), [])                                                                                  # an IMPORTed name counts as a definition
    def test_colour_range(self):
        cols = ' '.join(['0.5 0.5 0.5'] * 100 + ['1.0059 1.0511 0.9'] + ['0.2 0.2 0.2', '1.2 0 0'])                        # the Earth case: the 101st colour
        f = only(X("<Shape><IndexedFaceSet DEF='ME_Earth' coordIndex='0 1 2 -1'><Coordinate point='0 0 0 1 0 0 0 1 0'/><Color color='%s'/></IndexedFaceSet></Shape>" % cols), 'colour-range')
        self.assertEqual(len(f), 1); d = f[0]
        self.assertEqual((d['first_index'], d['first_value'], d['count']), (100, [1.0059, 1.0511, 0.9], 2)); self.assertIn('DEF=ME_Earth', d['node']); self.assertEqual(d['line'], 5)
        self.assertEqual(len(only(X("<Shape><Appearance><Material diffuseColor='0.2 -0.1 0.4'/></Appearance><Box/></Shape>"), 'colour-range')), 1)
        self.assertEqual(only(X("<ColorRGBA color='0.1 0.2 0.3 0.5 1 1 1 0'/>"), 'colour-range'), [])
        self.assertEqual(len(only(X("<ColorRGBA color='0.1 0.2 0.3 1.5'/>"), 'colour-range')), 1)                         # alpha is a channel too
    def test_rgba_opaque(self):
        self.assertEqual(rules(X("<ColorRGBA color='0.1 0.2 0.3 1 0.4 0.5 0.6 1.0'/>")), ['rgba-opaque'])
        self.assertEqual(rules(X("<ColorRGBA color='0.1 0.2 0.3 1 0.4 0.5 0.6 0.5'/>")), [])
        self.assertEqual(rules(X("<Color color='0.1 0.2 0.3'/>")), [])
    def test_asset_scene_nodes(self):
        body = "<NavigationInfo/><Background skyColor='0.05 0.05 0.05'/><Shape><Appearance><PhysicalMaterial/></Appearance><Box/></Shape>"
        self.assertEqual(sorted(rules(X(body, gen=True))), ['asset-scene-node'] * 3)                                     # detected from the generator meta
        self.assertEqual(rules(X(body)), []); self.assertEqual(len(only(X(body), 'asset-scene-node', asset=True)), 3); self.assertEqual(rules(X(body, gen=True), asset=False), [])
    def test_precision(self):
        f = only(X("<Coordinate point='0.123456 1.5 -2.000001'/><Color color='0.12345 0.5 0.25'/>"), 'precision')
        self.assertEqual(len(f), 2); self.assertTrue(all(d['severity'] == 'info' for d in f))
        by = {d['node']: d['bytes_saved'] for d in f}; self.assertEqual(by['Coordinate'], 8 - 6 + 9 - 2); self.assertEqual(by['Color'], 7 - 5)  # 0.1235, -2
        self.assertEqual(rules(X("<Coordinate point='0.1235 1.5 -2'/><Color color='0.123 0.5 0.25'/>")), [])
    def test_xite_component(self):
        body = "<Shape><Appearance><DepthMode depthMask='false'/><BlendMode/></Appearance><Sphere/></Shape>"
        f = only(X(body), 'xite-component'); self.assertEqual([d['node'] for d in f], ['DepthMode', 'BlendMode']); self.assertEqual(f[0]['severity'], 'error')
        self.assertEqual(rules(X(body, head="<component name='X_ITE' level='1'/>")), [])
    def test_glsl_int_literals(self):
        bad = SHADER % ('', 'float a = 1; vec3 b = v * 2; float c = pow(t, 2); float d = max(t, 0); float e = v.x - 3;\n  x3d_FragColor = vec4(b * a, 1.0);')
        f = only(X(bad), 'glsl-int-literal')
        self.assertEqual(sorted(d['message'].split()[2] for d in f), ['0', '1', '2', '2', '3']); self.assertTrue(all(d['line'] == 15 for d in f), [d['line'] for d in f])
        good = SHADER % ('', 'float a = 1.0; vec3 b = v * 2.0; float c = pow(t, 2.0); float d = max(t, 0.0); int k = 3 * 2; x3d_FragColor = vec4(b * a + h[2], 1.0);')
        self.assertEqual(only(X(good), 'glsl-int-literal'), [])                                                        # indices, loops, int maths and vec3(1) are fine
    def test_glsl_url_data(self):
        part = "<ComposedShader language='GLSL'><ShaderPart type='FRAGMENT' url='\"data:x-shader/x-fragment,%23version%20300%20es%0Aprecision highp float;%0Auniform float t;%0Avoid main() { float a = t * 2; }\"'/></ComposedShader>"
        f = only(X("<Shape><Appearance>%s</Appearance><Box/></Shape>" % part), 'glsl-int-literal'); self.assertEqual(len(f), 1); self.assertEqual(f[0]['glsl_line'], 4)
    def test_glsl_logdepth(self):
        writes = 'gl_FragDepth = gl_FragCoord.z; x3d_FragColor = vec4(1.0);'
        self.assertEqual(rules(X(SHADER % ('', writes))), ['glsl-logdepth'])
        self.assertEqual(rules(X(SHADER % ("<field name='logDepth' type='SFFloat' accessType='inputOutput' value='0'/>", writes))), [])
        self.assertEqual(rules(X(SHADER % ('', 'x3d_FragColor = vec4(1.0);'))), [])
    def test_shader_raw_source(self):
        raw = SHADER.replace('data:x-shader/x-fragment,', '') % ('', 'x3d_FragColor = vec4(1.0);')                # the pocket-universe pages' form: white spheres in X_ITE 16.5.1
        f = only(X(raw), 'shader-raw-source'); self.assertEqual(len(f), 1)
        self.assertEqual((f[0]['severity'], f[0]['line'], f[0]['prefix']), ('error', 6, 'data:x-shader/x-fragment,'))
        self.assertEqual(only(X(SHADER % ('', 'x3d_FragColor = vec4(1.0);')), 'shader-raw-source'), [])           # the prefixed form is silent
        lead = "<ComposedShader language='GLSL'><ShaderPart type='VERTEX'><![CDATA[\n  precision highp float;\n  void main() { gl_Position = vec4(0.0); }\n]]></ShaderPart></ComposedShader>"
        self.assertEqual([d['prefix'] for d in only(X("<Shape><Appearance>%s</Appearance><Box/></Shape>" % lead), 'shader-raw-source')], ['data:x-shader/x-vertex,'])
        for body in ('shaders/glow.fs', '"glow.fs" "https://example.org/glow.fs"', 'https://example.org/glow.fs'):    # a body that is a url stays a url
            part = "<ComposedShader language='GLSL'><ShaderPart type='FRAGMENT'><![CDATA[%s]]></ShaderPart></ComposedShader>" % body
            self.assertEqual(only(X("<Shape><Appearance>%s</Appearance><Box/></Shape>" % part), 'shader-raw-source'), [], body)
    def test_the_page_shaders_are_clean(self):
        import re
        src = get(os.path.join(ROOT, 'tools', 'layers.py')) + get(os.path.join(ROOT, 'tools', 'world_layer.py'))
        parts = re.findall(r'CDATA\[data:[^,]*,(.*?)\]\]>', src, re.S); self.assertGreaterEqual(len(parts), 6)
        for p in parts: self.assertEqual(loom_gate.glsl_int_literals(p), [])
    def test_parse_error_and_exit_codes(self):
        self.assertEqual(rules("<X3D><Scene><Shape></Scene></X3D>"), ['parse-error'])
        with tempfile.TemporaryDirectory() as d:
            ok, bad = os.path.join(d, 'ok.x3d'), os.path.join(d, 'bad.x3d')
            put(ok, X("<ColorRGBA color='0 0 0 1'/>")); put(bad, X("<Color color='2 0 0'/>"))
            with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(loom_gate.main([ok]), 0)
            with contextlib.redirect_stdout(io.StringIO()) as o: self.assertEqual(loom_gate.main([bad, '--json']), 1)
            self.assertEqual(json.loads(o.getvalue())[0]['rule'], 'colour-range')
            with contextlib.redirect_stdout(io.StringIO()) as o: loom_gate.main([ok, '--fork'])
            self.assertTrue('fork-skipped' in o.getvalue() or 'fork-' in o.getvalue())
    def test_committed_assets_have_no_errors(self):
        files = sorted(glob.glob(os.path.join(ROOT, 'assets', '*', '*.x3d'))); self.assertGreaterEqual(len(files), 9)
        for f in files:
            errs = [d for d in loom_gate.gate_file(f) if d['severity'] == 'error']; self.assertEqual(errs, [], f)


class Receipt(unittest.TestCase):
    def test_luminance_per_shape(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, 'a.x3d')
            put(p, X("<Shape><IndexedFaceSet DEF='ME_Wall'><Color color='%s'/></IndexedFaceSet></Shape><Shape><IndexedFaceSet DEF='ME_Sky'><ColorRGBA color='1 1 1 1'/></IndexedFaceSet></Shape>" % ' '.join(['0 0 0'] * 10 + ['1 1 1'] * 10)))
            s = loom_receipt.shape_luminance(p)
            self.assertEqual(sorted(s), ['Sky', 'Wall']); self.assertEqual((s['Wall']['corners'], s['Wall']['lum_p05'], s['Wall']['lum_p95']), (20, 0.0, 1.0)); self.assertEqual(s['Sky']['lum_p50'], 1.0)
    def test_write_then_check_then_drift(self):
        with tempfile.TemporaryDirectory() as d:
            a, sc = os.path.join(d, 'a.x3d'), os.path.join(d, 'gen.py')
            put(a, X("<Shape><IndexedFaceSet DEF='ME_W'><Color color='0.5 0.5 0.5'/></IndexedFaceSet></Shape>")); put(sc, '# generator\n')
            bake = os.path.join(d, 'bake.json'); put(bake, json.dumps({'samples': 384}))
            q = io.StringIO()
            with contextlib.redirect_stdout(q): self.assertEqual(loom_receipt.main(['write', a, '--script', sc, '--bake', bake, '--blender', '5.2.2 LTS']), 0)
            r = json.loads(get(os.path.join(d, 'receipt.json')))
            self.assertEqual((r['blender'], r['bake'], r['file'], r['colour_stats']['W']['lum_p50']), ('5.2.2 LTS', {'samples': 384}, 'a.x3d', 0.5))
            with contextlib.redirect_stdout(q), contextlib.redirect_stderr(q): self.assertEqual(loom_receipt.main(['write', a, '--script', sc]), 1)   # never overwrites
            self.assertTrue(all(s == 'ok' for s, _ in loom_receipt.check_one(os.path.join(d, 'receipt.json'))))
            put(sc, get(sc) + '# a comment\n')                                                                       # even a comment is a drift
            st = loom_receipt.check_one(os.path.join(d, 'receipt.json')); self.assertIn('drift', [s for s, _ in st])
            self.assertEqual(json.loads(get(os.path.join(d, 'receipt.json'))), r)                                     # and the receipt is left as it was
    def test_committed_receipts(self):
        ps = sorted(glob.glob(os.path.join(ROOT, 'assets', '*', 'receipt*.json'))); self.assertEqual(len(ps), 8)
        before = {p: get(p) for p in ps}
        res = {p: loom_receipt.check_one(p) for p in ps}
        for p, r in res.items():
            self.assertTrue(r, p); self.assertNotIn('missing', [s for s, _ in r], (p, r))                              # every receipt's file and script is found (drift is reported, not a failure here)
        self.assertEqual(sum(1 for _, m in res[os.path.join(ROOT, 'assets', 'feathers', 'receipt.json')] if 'variant' in m), 3)
        self.assertEqual(before, {p: get(p) for p in ps})


if __name__ == '__main__':
    unittest.main(verbosity=1)
