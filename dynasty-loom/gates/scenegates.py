"""Static SCENE gates for an X3D (XML) file: the checks the fork validator does not make, or makes with a misleading message.
They run before the fork validator (XSD, semantic, profile) and X_ITE's console, and never replace them.

  python3 -I scenegates.py FILE.x3d [...] [--budget-gz BYTES]

S1 DEF names unique per scope (a ProtoBody is its own scope)
S2 every USE follows its DEF in document order
S3 every ROUTE comes after the nodes it names (the fork passes a ROUTE written first; X_ITE 16.5.1 drops it)
S4 every colour channel in [0, 1], with the element, field and index of the first bad value (the fork's XSD message once
   blamed a start-tag size limit for a colour of 1.0059: no bisecting needed when the array is read directly)
S5 bytes raw and gzipped against a budget
S6 advisory (ok*): a ColorRGBA whose alpha is 1 everywhere (should be a Color in the page's file: the bake stage's step 6; expected on raw exports)"""
import gzip
import json
import os
import sys
import xml.etree.ElementTree as ET

COLOUR_FIELDS = {'color', 'diffuseColor', 'emissiveColor', 'specularColor', 'baseColor', 'skyColor', 'groundColor', 'backColor', 'emissiveColor'}
NOT_COLOUR = {'FontStyle'}            # elements whose `color`-like attributes are not SFColor/MFColor


def check(path, budget_gz=None, budget_raw=None):
    raw = open(path, 'rb').read(); out = []
    def bad(gate, msg, **d): out.append(dict(gate=gate, file=os.path.basename(path), message=msg, **d))
    try:
        it = ET.iterparse(path, events=('start', 'end'))
        scopes = [set()]; seen_routes = 0
        for ev, el in it:
            tag = el.tag.split('}')[-1]
            if ev == 'end':
                if tag == 'ProtoBody': scopes.pop()
                continue
            if tag == 'ProtoBody': scopes.append(set())
            d, u = el.get('DEF'), el.get('USE')
            if d:
                if d in scopes[-1]: bad('S1-def-unique', 'DEF %r defined twice in one scope' % d, name=d)
                scopes[-1].add(d)
            if u and not any(u in s for s in scopes): bad('S2-use-after-def', 'USE %r before (or without) its DEF' % u, name=u)
            if tag == 'IMPORT' and el.get('AS'): scopes[-1].add(el.get('AS'))
            if tag == 'ROUTE':
                seen_routes += 1
                for f in ('fromNode', 'toNode'):
                    n = el.get(f)
                    if n and not any(n in s for s in scopes): bad('S3-route-order', 'ROUTE %s=%r comes before the node it names (X_ITE drops it, the fork passes it)' % (f, n), name=n)
            if tag in NOT_COLOUR: continue
            for f in COLOUR_FIELDS & set(el.attrib):
                try: vals = [float(x) for x in el.get(f).replace(',', ' ').split()]
                except ValueError: bad('S4-colour-range', '%s.%s is not numeric' % (tag, f)); continue
                for i, v in enumerate(vals):
                    if not 0.0 <= v <= 1.0:
                        bad('S4-colour-range', '%s%s.%s value %d is %r (outside [0, 1]); %d of %d values out of range' % (tag, "[DEF=%s]" % el.get('DEF') if el.get('DEF') else '', f, i, v, sum(not 0 <= x <= 1 for x in vals), len(vals)), element=tag, field=f, index=i, value=v)
                        break
                if tag == 'ColorRGBA' and f == 'color' and len(vals) >= 4 and len(vals) % 4 == 0 and all(a == 1.0 for a in vals[3::4]):
                    bad('S6-rgba-opaque', 'ColorRGBA with alpha 1 on all %d entries: a Color is smaller' % (len(vals) // 4))
    except ET.ParseError as e:
        bad('S0-xml', 'not well-formed XML: %s' % e)
    gz = len(gzip.compress(raw, 9, mtime=0))
    if budget_gz and gz > budget_gz: bad('S5-size', '%d B gzipped, over the %d B budget' % (gz, budget_gz))
    if budget_raw and len(raw) > budget_raw: bad('S5-size', '%d B raw, over the %d B budget' % (len(raw), budget_raw))
    return dict(file=path, bytes=len(raw), gz_bytes=gz, findings=out)


if __name__ == '__main__':
    args = sys.argv[1:]; bg = None
    if '--budget-gz' in args: i = args.index('--budget-gz'); bg = int(args[i + 1]); del args[i:i + 2]
    worst = 0
    for p in args:
        r = check(p, budget_gz=bg); worst = max(worst, len([f for f in r['findings'] if f['gate'] != 'S6-rgba-opaque']))
        hard = [f for f in r['findings'] if f['gate'] != 'S6-rgba-opaque']
        print('%-4s %9d B raw %8d B gz  %s' % ('FAIL' if hard else ('ok*' if r['findings'] else 'ok'), r['bytes'], r['gz_bytes'], p))
        for f in r['findings'][:8]: print('      %s  %s' % (f['gate'], f['message']))
    sys.exit(1 if worst else 0)
