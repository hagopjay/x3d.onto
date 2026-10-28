#!/usr/bin/env python3
"""Compose the bird-first scene: the Gobbler 3 Deep scene (untouched bytes) plus the layers from layers.py, spliced in.
  python3 -I tools/build_bird.py [--validate]   ->  data/bird/gobbler4-bird.x3d, .x3d.gz, graph-v3.json.gz, anchors.json, receipt.json
Needs gobbler-v4/data/deep (make v4-data) and data/explorer.json. Outputs are fetched/built, not committed (see .gitignore)."""
import gzip, hashlib, json, os, sys, subprocess, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); REPO = os.path.dirname(ROOT)
sys.path.insert(0, HERE)
import layers

DEEP = os.path.join(REPO, 'gobbler-v4', 'data', 'deep'); OUT = os.path.join(ROOT, 'data', 'bird')
def sha(b): return hashlib.sha256(b).hexdigest()
def gz(b): return gzip.compress(b, 9, mtime=0)

def compose(deep_text, L):
    first_vp = deep_text.index("<Viewpoint DEF='Wide'")
    assert deep_text.count('</Scene>') == 1 and "DEF='PointShader'" in deep_text and "DEF='SwayTurn'" in deep_text
    t = deep_text[:first_vp] + L['viewpoints'] + '\n    ' + deep_text[first_vp:]
    end = t.rindex('</Scene>')
    block = '\n    <!-- Gobbler demiurge layers (tools/layers.py, seed 4): Sun in the chest, Dyson ribcage, flywheel, tenders, wing, tail fan with the Blender root. Added; nothing above is edited. -->\n    ' + L['sway'] + L['routes'] + '\n  '
    t = t[:end] + block + t[end:]
    return t

def main():
    t0 = time.time(); os.makedirs(OUT, exist_ok=True)
    deep_b = open(os.path.join(DEEP, 'gobbler3.x3d'), 'rb').read(); deep = deep_b.decode('utf-8')
    L = layers.build(os.path.join(REPO, 'data', 'explorer.json'))
    scene = compose(deep, L); sb = scene.encode('utf-8')
    open(os.path.join(OUT, 'gobbler4-bird.x3d'), 'wb').write(sb)
    open(os.path.join(OUT, 'gobbler4-bird.x3d.gz'), 'wb').write(gz(sb))
    gj = open(os.path.join(DEEP, 'graph-v3.json'), 'rb').read(); open(os.path.join(OUT, 'graph-v3.json.gz'), 'wb').write(gz(gj))
    json.dump(L['anchors'], open(os.path.join(OUT, 'anchors.json'), 'w'), indent=1)
    rec = dict(scene_bytes=len(sb), scene_gz_bytes=len(gz(sb)), deep_bytes=len(deep_b), layers_bytes=len(sb) - len(deep_b), graph_bytes=len(gj), graph_gz_bytes=len(gz(gj)),
               boot_gz_bytes=len(gz(sb)) + len(gz(gj)), counts=L['counts'], scene_sha256=sha(sb), deep_sha256=sha(deep_b), built_in_s=round(time.time() - t0, 2))
    if '--validate' in sys.argv:
        v = os.environ.get('X3D_VALIDATE', os.path.join(HERE, 'validate_fork.py'))
        r = subprocess.run([sys.executable, v, os.path.join(OUT, 'gobbler4-bird.x3d')], capture_output=True, text=True)
        try: rec['validator'] = json.loads(r.stdout)
        except Exception: rec['validator'] = dict(error=(r.stdout + r.stderr)[-600:])
        mcp = os.environ.get('X3D_MCP', '/home/user/x3d_mcp')          # name the validator behind the number: the fork checkout the report came from
        try: head = subprocess.run(['git', '-C', mcp, 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip(); rec['validator'].update(commit=head, label='x3d_mcp fork ' + head)
        except Exception: pass
    json.dump(rec, open(os.path.join(OUT, 'receipt.json'), 'w'), indent=1)
    print(json.dumps({k: v for k, v in rec.items() if k != 'validator'}, indent=1))
    if 'validator' in rec: print('validator:', json.dumps({k: rec['validator'].get(k) for k in ('xsd_valid', 'xsd_errors', 'profile_ok', 'error')}))
if __name__ == '__main__': main()
