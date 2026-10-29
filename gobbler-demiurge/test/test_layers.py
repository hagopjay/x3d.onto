"""python3 -I test/test_layers.py : the layers are deterministic, match the plan's counts, and compose in the right place (needs make v4-data first)."""
import os, re, sys, json, math, unittest, hashlib, pathlib
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
        self.assertEqual(len(re.findall(r"<Group DEF='TenderBody\d'>", x)), 3); self.assertEqual(len(re.findall(r"<Group USE='TenderBody\d'/>", x)), 7)   # three H-Anim copies, shared by USE among the ten shell tenders
        self.assertEqual(x.count('<HAnimHumanoid'), 3); self.assertEqual(len(re.findall(r'<HAnimJoint DEF="hanim_T\d_\w+"', x)), 54)   # 18 joints each; the villagers' bodies are in their own lazy file
        ids = {a['id'] for a in L['anchors']}; self.assertEqual(len(L['anchors']), 19)
        for t in ('fan_gltf', 'fan_usd', 'fan_video', 'fan_o3de', 'fan_paraview', 'fan_3dslicer', 'fan_unity', 'fan_defold', 'fan_ifc'): self.assertIn(t, ids)
        self.assertEqual(sum(1 for a in L['anchors'] if a['id'].startswith('fan_') and 'mock' in a['tag']), 6)   # six mocks, tagged
        self.assertEqual(sum(1 for a in L['anchors'] if a['id'].startswith('fan_') and a['tag'].startswith('Blender export')), 3)
    def test_world_layer(self):
        L = layers.build(EXP); x = L['sway']; W = L['world']
        self.assertNotIn("DEF='Villager0'", x)                                                                           # the villagers are not in the boot payload ...
        self.assertEqual(re.findall(r"<Inline DEF='(\w+)' load='false'", x), ['EarthPlanet', 'EarthClouds', 'EarthMoon', 'VillageInline', 'VillagersInline'])   # ... the big files wait for the camera
        self.assertEqual(sorted(W['stops']), ['earth', 'plaza', 'village', 'villager'])
        for k, st in W['stops'].items(): self.assertEqual((len(st['pos']), len(st['look']), len(st['up'])), (3, 3, 3), k)
        seen = set(re.findall(r"DEF='(\w+)'", x))                                                                       # every ROUTE names nodes that are defined (the world routes come after their nodes)
        for m in re.finditer(r"<ROUTE fromNode='(\w+)'[^>]*toNode='(\w+)'", x):
            for n in m.groups():
                if n.startswith(('Earth', 'Village', 'Villagers', 'Climb', 'Moon', 'Cloud')): self.assertIn(n, seen, n)
        self.assertLess(x.index("<Group DEF='EarthWorld'"), x.index("toNode='EarthWorld'"))
        tag = {a['id']: a for a in L['anchors']}; self.assertIn('1,700', tag['earth']['tag']); self.assertIn('25,000', tag['village']['tag'])   # the scale notes say what is not to scale
    def test_villagers_file(self):
        v = layers.build(EXP)['villagers']
        self.assertEqual(len(re.findall(r"<Group DEF='VillagerBody\d'>", v)), 3); self.assertEqual(len(re.findall(r"<Group USE='VillagerBody\d'/>", v)), 9)   # three outfits, each with its own gait, shared by USE among twelve walkers
        self.assertEqual(len(re.findall(r"<Transform DEF='Villager\d+'>", v)), 12); self.assertEqual(v.count('<HAnimHumanoid'), 3); self.assertEqual(len(re.findall(r'<HAnimJoint DEF="hanim_T[345]_\w+"', v)), 54)
        self.assertIn("<component name='HAnim' level='1'/>", v)
        for m in re.finditer(r"<ROUTE fromNode='(\w+)'[^>]*toNode='(\w+)'", v):                                           # a self-contained file: every ROUTE names nodes it defines, defined before it (the fork does not check the order)
            for n in m.groups():
                d = re.search(r"DEF=['\"]%s['\"]" % n, v); self.assertIsNotNone(d, n); self.assertLess(d.start(), m.start(), n)
        self.assertEqual(v, layers.build(EXP)['villagers'])                                                              # deterministic
    def test_world_files_are_written_unlit_and_small(self):
        import world, tempfile
        with tempfile.TemporaryDirectory() as d:
            sizes = world.build(d); self.assertEqual(sorted(sizes), ['earth-clouds.x3d', 'earth-moon.x3d', 'earth-planet.x3d', 'village.x3d'])
            for n in sizes:
                t = pathlib.Path(d, n).read_text(encoding='utf-8'); self.assertNotIn('PhysicalMaterial', t, n); self.assertNotIn('NavigationInfo', t, n); self.assertLess(sizes[n], 1.5e6, n)
            v = pathlib.Path(d, 'village.x3d').read_text(encoding='utf-8'); self.assertEqual(v.count('<Shape'), 4)               # four merged meshes (four draw calls), the light baked into one colour per face corner, not one object per house
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
    def test_gold_variant_is_an_additional_file_that_keeps_alpha(self):
        deep = open(DEEP, encoding='utf-8').read(); g = build_bird.goldgraph(deep)
        self.assertNotEqual(g, deep)
        a = [m for m in re.findall(r"<ColorRGBA color='([^']*)'", deep) if len(m.split()) >= 400]; b = [m for m in re.findall(r"<ColorRGBA color='([^']*)'", g) if len(m.split()) >= 400]
        self.assertEqual(len(a), len(b)); self.assertGreater(len(a), 3)
        for x, y in zip(a, b): self.assertEqual(x.split()[3::4], y.split()[3::4])                  # alpha (sprite kind and size) untouched
        self.assertEqual(deep.count('<ColorRGBA'), g.count('<ColorRGBA'))
    def test_every_use_follows_its_def(self):
        deep = open(DEEP, encoding='utf-8').read(); out = build_bird.compose(deep, layers.build(EXP)); seen = set()
        for m in re.finditer(r"(DEF|USE)='([^']+)'", out):
            if m.group(1) == 'DEF': seen.add(m.group(2))
            else: self.assertIn(m.group(2), seen, 'USE before DEF: ' + m.group(2))
    def test_armenian_knot_strands(self):
        import weave
        orns = weave.ornaments(4); self.assertEqual([o['L'] for o in orns], [2, 5, 3])                         # eight-armed arevakhach, the plaited border ring, twelve arms
        self.assertNotEqual(weave.ornaments(5)[0], orns[0])                                                     # the next seed changes the knot
        for o in orns:
            for k in range(4):
                for t in (0.0, 0.137, 0.5, 0.91):
                    a, b = weave.point(o, k, t), weave.point(o, k, t + 1.0); self.assertAlmostEqual(math.hypot(a[0] - b[0], a[1] - b[1]), 0, places=9)   # closed and periodic
            P = [weave.point(o, 0, weave.tparam(o, i / weave.N)) for i in range(weave.N + 1)]; self.assertLess(math.hypot(P[0][0] - P[-1][0], P[0][1] - P[-1][1]), 1e-9)   # the strip as the shader bends it closes on itself
            for a, b, c in zip(P, P[1:], P[2:]):                                                                 # and is smooth: short steps, gentle bends, also where it curls
                self.assertLess(math.hypot(c[0] - b[0], c[1] - b[1]), 0.15, o['name'])
                d = abs((math.atan2(c[1] - b[1], c[0] - b[0]) - math.atan2(b[1] - a[1], b[0] - a[0]) + math.pi) % (2 * math.pi) - math.pi); self.assertLess(math.degrees(d), 15, o['name'])
            cs = weave.crossings(o); lift, flips, base = weave.lift_profile(o, cs)
            self.assertGreater(len(base), 8)
            for k in range(4):                                                                                  # along every strand the crossings go over, under, over ...
                sk = weave.strand_crossings(cs, k); self.assertEqual(len(sk) % 2, 0)
                for (t0, s0), (t1, s1) in zip(sk, sk[1:] + sk[:1]): self.assertEqual(s0, -s1, (o['name'], k, t0))
            for t, s in base: self.assertAlmostEqual(lift(t), s, places=6, msg=(o['name'], t))                  # the lift the strip carries is fully up where the strand is over, down where under
            self.assertAlmostEqual(lift(0.0), lift(1.0), places=9)                                              # the lift closes too
    def test_armenian_knot_in_the_scene(self):
        L = layers.build(EXP); x = L['sway']
        self.assertEqual(x.count("<TriangleStripSet DEF='WeaveStrip'"), 1); self.assertEqual(x.count("<TriangleStripSet USE='WeaveStrip'/>"), 11); self.assertEqual(len(re.findall(r"<ComposedShader DEF='WeaveSh\d_\d'", x)), 12)
        self.assertEqual(len(re.findall(r"<Transform DEF='Shuttle\d' ", x)), 4); self.assertNotIn("DEF='ShuttleClock0'", x); self.assertNotIn('<Script', x)
        for m in re.finditer(r"<ROUTE fromNode='(\w+)'[^>]*toNode='(\w+)'", x):                                   # X_ITE drops a ROUTE that comes before its node
            for n in m.groups():
                if n.startswith(('Weave', 'Shuttle')): d = re.search(r"DEF='%s'" % n, x); self.assertIsNotNone(d, n); self.assertLess(d.start(), m.start(), n)
        self.assertEqual(len(L['knot']['ornaments']), 3); self.assertIn("startTime='1e12'", x)                  # the page starts the clock; elsewhere the first knot shows complete
        old = layers.build(EXP, weave=False)['sway']; self.assertNotIn("DEF='Weave'", old); self.assertIn("DEF='ShuttleClock3'", old)   # weave=False: the earlier wandering shuttles
    def test_sound_beds_and_heart_tape(self):
        man = json.loads(pathlib.Path(ROOT, 'assets', 'audio', 'manifest.json').read_text())
        self.assertEqual(sorted(man['beds']), ['cosmos', 'village'])
        for k, bed in man['beds'].items():
            raw = pathlib.Path(ROOT, 'assets', 'audio', bed['file']).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), bed['sha256'], k + ': the file is the one the manifest describes'); self.assertEqual(len(raw), bed['bytes'])
            self.assertAlmostEqual(bed['mastered']['lufs'], man['target_lufs'], delta=0.3)                                  # both beds sit at the same loudness
            self.assertEqual(sorted(bed), sorted(('file', 'plays', 'prompt', 'negative_prompt', 'seed', 'seconds', 'source', 'gain_db', 'mastered', 'bytes', 'sha256')), 'only these fields: no model or service field')
            self.assertNotIn('http', json.dumps(bed).lower())                                                              # and no link
        L = layers.build(EXP); H = L['heart']; beats = layers.heart_beats()
        self.assertEqual(len(H['beats']), len(beats)); self.assertEqual(sum(1 for _, r in H['beats'] if r), sum(1 for _, r in beats if r))
        self.assertAlmostEqual(H['cycle'], sum(d for d, _ in beats), delta=0.01 * len(beats))                                # the tape the sound reads is the tape the swell is keyed on
        self.assertIn("cycleInterval='%s'" % layers.f(H['cycle']), L['sway'])
        self.assertEqual((H['lub'], H['dub']), (layers.HEART_LUB, layers.HEART_DUB))
if __name__ == '__main__': unittest.main()
