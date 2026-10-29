"""python3 -I test/test_layers.py : the layers are deterministic, match the plan's counts, and compose in the right place (needs make v4-data first)."""
import os, re, sys, json, unittest, hashlib, pathlib
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
        ids = {a['id'] for a in L['anchors']}; self.assertEqual(len(L['anchors']), 20)            # 19, and the Mashtots ring
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
    def test_mashtots_ring(self):
        import mashtots as MS
        L = layers.build(EXP); x = L['sway']
        self.assertEqual(len(re.findall(r"<Transform DEF='Mashtots\d\d'", x)), 36)                                      # the 36 letters of Mashtots, Օ and Ֆ left out
        self.assertEqual(x.count("<Color DEF='MashtotsShades'"), 1); self.assertEqual(x.count("<Color USE='MashtotsShades'/>"), 35)  # one shade palette, shared
        self.assertEqual([c for c, _, _ in MS.LETTERS], list(range(0x531, 0x555)))
        self.assertEqual([v for _, _, v in MS.LETTERS][::9], [1, 10, 100, 1000]); self.assertEqual(MS.LETTERS[-1][2], 9000)
        letters = json.loads(pathlib.Path(ROOT, 'assets', 'mashtots', 'letters.json').read_text(encoding='utf-8'))['letters']
        self.assertEqual([(l['glyph'], l['name'], l['value']) for l in letters], [(chr(c), n, v) for c, n, v in MS.LETTERS])
        man = json.loads(pathlib.Path(ROOT, 'assets', 'mashtots', 'manifest.json').read_text())
        self.assertEqual(hashlib.sha256(pathlib.Path(ROOT, 'assets', 'mashtots', man['file']).read_bytes()).hexdigest(), man['sha256'])      # the font is the one the manifest names
        self.assertEqual(hashlib.sha256(pathlib.Path(ROOT, 'assets', 'mashtots', 'glyphs.json').read_bytes()).hexdigest(), man['glyphs_json_sha256'])
        for nm in ('MashtotsClock', 'MashtotsSpin', 'MashtotsReadClock', 'MashtotsRead', 'MashtotsReader', 'MashtotsRing'):                   # every ROUTE of the ring after its nodes (X_ITE drops one that is not)
            for m in re.finditer(r"<ROUTE [^>]*Node='%s'" % nm, x): self.assertLess(x.index("DEF='%s'" % nm), m.start(), nm)
        G = MS.load_glyphs()
        for cp, name, _ in MS.LETTERS:                                                                                   # the face of every letter covers its outline: triangles add up to the area
            polys = MS.flatten(G['glyphs']['%04X' % cp]['ops']); tot = 0.0
            for o, hs in MS.nest(polys):
                P = {}; rings = []
                for poly in [o] + hs: b = len(P); P.update({b + k: p for k, p in enumerate(poly)}); rings.append(list(range(b, b + len(poly))))
                tris = MS.earclip(P, MS.bridge(P, rings[0], rings[1:])); self.assertTrue(all(MS._cross(P[a], P[b], P[c]) > 0 for a, b, c in tris), name)
                tot += sum(MS._cross(P[a], P[b], P[c]) / 2 for a, b, c in tris) - MS.area(o) - sum(MS.area(h) for h in hs)
            self.assertAlmostEqual(tot, 0.0, delta=1.0, msg=name)
        layers.MASHTOTS = False
        try: off = layers.build(EXP)
        finally: layers.MASHTOTS = True
        self.assertNotIn('Mashtots', off['sway']); self.assertEqual(len(off['anchors']), 19)                              # the flag leaves the build as it was before the ring
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
