"""The Loom gate: lints for the traps the fork validator passes (SKILL step 7 and its Traps list). Stdlib only; --fork also runs tools/validate_fork.py (needs lxml and X3D_MCP).
  python3 -I tools/loom_gate.py FILE.x3d [...] [--json] [--fork] [--asset|--scene]
Each finding has a stable rule id, a severity (error, warning, info), the file, the line, the node (tag and DEF, or the nearest DEF above it) and a message.
Exit code 1 when any finding is an error, 2 when a file does not parse, else 0.

Rules:
  route-forward     error    a ROUTE names a node whose DEF comes later in the document (X_ITE 16.5.1 drops it, the fork passes it)
  route-undefined   error    a ROUTE names a node that is never defined (nor IMPORTed)
  colour-range      error    a colour channel outside [0, 1] (Color, ColorRGBA, materials, lights, Background, Fog, ColorInterpolator): the first offending colour, its values, the count
  rgba-opaque       warning  a ColorRGBA whose alpha is 1 everywhere (write a Color: a quarter fewer numbers)
  asset-scene-node  warning  PhysicalMaterial, Background or NavigationInfo left in an asset export (default: files whose generator meta names Blender; --asset forces, --scene turns it off)
  precision         info     positions with more than 4 decimals, colours with more than 3, and the bytes shortening would save
  xite-component    error    an X_ITE-only node (DepthMode, BlendMode, InstancedShape) in a scene without <component name='X_ITE'>
  glsl-int-literal  warning  an integer literal where GLSL ES wants a float (heuristic: next to a float operand, assigned to a float, or in a float-only builtin)
  glsl-logdepth     warning  a shader writes gl_FragDepth or uses X_ITE's log depth uniform, and its ComposedShader has no logDepth field
  shader-raw-source error    a ShaderPart or ShaderProgram whose CDATA is GLSL with no data:x-shader/... prefix: X_ITE 16.5.1 reads the body as its url, resolves
                             '#version 300 es ...' against the world URL, the shader is invalid and the shape draws unlit (white); XSD and the fork pass it
  fork-*            error    --fork: XSD invalid, semantic errors or profile not OK; fork-skipped (info) when X3D_MCP has no checkout
"""
import os, re, sys, json, subprocess, urllib.parse, base64
import xml.parsers.expat

HERE = os.path.dirname(os.path.abspath(__file__))
SEV = {'error': 0, 'warning': 1, 'info': 2}

COLOUR_FIELDS = {
    'Color': ('color',), 'ColorRGBA': ('color',), 'ColorInterpolator': ('keyValue',),
    'Material': ('diffuseColor', 'emissiveColor', 'specularColor'),
    'TwoSidedMaterial': ('diffuseColor', 'emissiveColor', 'specularColor', 'backDiffuseColor', 'backEmissiveColor', 'backSpecularColor'),
    'PhysicalMaterial': ('baseColor', 'emissiveColor'), 'UnlitMaterial': ('emissiveColor',),
    'DirectionalLight': ('color',), 'PointLight': ('color',), 'SpotLight': ('color',), 'EnvironmentLight': ('color',),
    'Background': ('skyColor', 'groundColor'), 'TextureBackground': ('skyColor', 'groundColor'), 'Fog': ('color',), 'LocalFog': ('color',),
}
POSITION_FIELDS = {'Coordinate': ('point',), 'CoordinateDouble': ('point',)}
XITE_ONLY = ('DepthMode', 'BlendMode', 'InstancedShape')
ASSET_ONLY_NOT = ('PhysicalMaterial', 'Background', 'NavigationInfo')
POS_PLACES, COL_PLACES = 4, 3


class Node:
    __slots__ = ('tag', 'a', 'line', 'kids', 'parent', 'text', 'text_line', 'order')
    def __init__(self, tag, a, line, parent, order):
        self.tag, self.a, self.line, self.parent, self.order = tag, a, line, parent, order
        self.kids, self.text, self.text_line = [], [], None
    def iter(self):
        yield self
        for k in self.kids: yield from k.iter()
    def where(self):
        n = self
        while n is not None:
            if n.a.get('DEF'): return '%s DEF=%s' % (self.tag, n.a['DEF']) if n is self else '%s in DEF=%s' % (self.tag, n.a['DEF'])
            n = n.parent
        return self.tag


def parse(text):
    """-> root Node. Expat (stdlib) so every element keeps its line; CDATA and text are kept with the line they start on."""
    p = xml.parsers.expat.ParserCreate(); stack = [Node('#doc', {}, 0, None, -1)]; count = [0]
    def start(tag, a):
        n = Node(tag, a, p.CurrentLineNumber, stack[-1], count[0]); count[0] += 1; stack[-1].kids.append(n); stack.append(n)
    def end(tag): stack.pop()
    def chars(s):
        n = stack[-1]
        if n.text_line is None and s.strip(): n.text_line = p.CurrentLineNumber
        n.text.append(s)
    p.StartElementHandler, p.EndElementHandler, p.CharacterDataHandler = start, end, chars
    p.Parse(text.encode('utf-8') if isinstance(text, str) else text, True)
    return stack[0]


def F(rule, sev, node, msg, line=None, **extra):
    d = {'rule': rule, 'severity': sev, 'line': line if line is not None else (node.line if node else 0), 'node': node.where() if node else '', 'message': msg}
    d.update(extra); return d


# ---- ROUTE order --------------------------------------------------------------------------------
def check_routes(root):
    out = []; first = {}
    for n in root.iter():
        name = n.a.get('DEF') or (n.a.get('AS') or n.a.get('importedDEF') if n.tag == 'IMPORT' else None)
        if name and name not in first: first[name] = n
    for n in root.iter():
        if n.tag != 'ROUTE': continue
        for k in ('fromNode', 'toNode'):
            v = n.a.get(k)
            if not v: continue
            d = first.get(v)
            if d is None: out.append(F('route-undefined', 'error', n, "ROUTE %s='%s' names a node that is never defined" % (k, v), ref=v))
            elif d.order > n.order: out.append(F('route-forward', 'error', n, "ROUTE %s='%s' comes before its DEF (line %d); X_ITE drops it, write ROUTEs after their nodes" % (k, v, d.line), ref=v, def_line=d.line))
    return out


# ---- colours, precision ---------------------------------------------------------------------------
def _floats(s):
    return [float(t) for t in s.replace(',', ' ').split()]

def _short(t, places):
    s = ('%.*f' % (places, float(t))).rstrip('0').rstrip('.')
    return '0' if s in ('', '-0') else s

def _decimals(t):
    m = re.match(r'^[-+]?\d*\.(\d+)$', t); return len(m.group(1)) if m else 0

def check_colours(root):
    out = []
    for n in root.iter():
        for f in COLOUR_FIELDS.get(n.tag, ()):
            v = n.a.get(f)
            if v is None: continue
            try: xs = _floats(v)
            except ValueError: out.append(F('colour-range', 'error', n, '%s is not a list of numbers' % f, field=f)); continue
            w = 4 if n.tag == 'ColorRGBA' else 3
            bad = [i for i in range(len(xs) // w) if any(c < 0.0 or c > 1.0 for c in xs[i * w:(i + 1) * w])]
            if bad:
                i = bad[0]; tup = xs[i * w:(i + 1) * w]
                out.append(F('colour-range', 'error', n, '%s: %d of %d colours outside [0, 1]; the first is index %d = (%s); min %g, max %g' % (
                    f, len(bad), len(xs) // w, i, ', '.join('%g' % c for c in tup), min(xs), max(xs)), field=f, first_index=i, first_value=tup, count=len(bad)))
            if n.tag == 'ColorRGBA' and xs and all(a == 1.0 for a in xs[3::4]):
                out.append(F('rgba-opaque', 'warning', n, 'ColorRGBA with alpha 1 in all %d colours: write a Color (saves %d numbers)' % (len(xs) // 4, len(xs) // 4)))
    return out

def check_precision(root):
    out = []
    for n in root.iter():
        for fields, places, kind in ((POSITION_FIELDS.get(n.tag, ()), POS_PLACES, 'position'), (COLOUR_FIELDS.get(n.tag, ()), COL_PLACES, 'colour')):
            for f in fields:
                v = n.a.get(f)
                if not v: continue
                toks = v.replace(',', ' ').split(); long_ = [t for t in toks if _decimals(t) > places]
                if not long_: continue
                try: saved = sum(len(t) - len(_short(t, places)) for t in long_)
                except ValueError: continue
                if saved > 0:
                    out.append(F('precision', 'info', n, '%s %s: %d of %d numbers have more than %d decimals (up to %d); shortening saves %d bytes' % (
                        kind, f, len(long_), len(toks), places, max(map(_decimals, long_)), saved), field=f, bytes_saved=saved))
    return out


# ---- scene-level ----------------------------------------------------------------------------------
def is_asset_export(root):
    return any(n.tag == 'meta' and n.a.get('name') == 'generator' and 'blender' in n.a.get('content', '').lower() for n in root.iter())

def check_asset_nodes(root):
    return [F('asset-scene-node', 'warning', n, '%s left in an asset export (strip it: the faces draw unlit and an Inline ignores bindables)' % n.tag) for n in root.iter() if n.tag in ASSET_ONLY_NOT]

def check_xite(root):
    comps = {n.a.get('name') for n in root.iter() if n.tag == 'component'}
    if 'X_ITE' in comps: return []
    return [F('xite-component', 'error', n, "%s is an X_ITE-only node, not X3D 4.0; X_ITE refuses it without <component name='X_ITE' level='1'/> (and the XSD refuses it anyway)" % n.tag)
            for n in root.iter() if n.tag in XITE_ONLY]


# ---- GLSL -----------------------------------------------------------------------------------------
_TOK = re.compile(r'(?P<ws>\s+)|(?P<com>//[^\n]*|/\*.*?\*/)|(?P<num>(?:\d+\.\d*|\.\d+)(?:[eE][-+]?\d+)?[fF]?|\d+[eE][-+]?\d+|0[xX][0-9a-fA-F]+[uU]?|\d+[uU]?)|(?P<id>[A-Za-z_]\w*)|(?P<op><<=|>>=|[-+*/%<>=!&|^]=|&&|\|\||\+\+|--|<<|>>|[-+*/%<>=!&|^~?:;,.(){}\[\]])', re.S)
FLOAT_TYPES = {'float', 'vec2', 'vec3', 'vec4', 'mat2', 'mat3', 'mat4', 'mat2x3', 'mat2x4', 'mat3x2', 'mat3x4', 'mat4x2', 'mat4x3'}
FLOAT_ONLY = {'pow', 'mix', 'smoothstep', 'step', 'exp', 'exp2', 'log', 'log2', 'sqrt', 'inversesqrt', 'sin', 'cos', 'tan', 'asin', 'acos', 'atan', 'mod', 'fract', 'floor', 'ceil',
              'radians', 'degrees', 'length', 'distance', 'dot', 'cross', 'normalize', 'reflect', 'refract', 'faceforward'}
MIXED = {'max', 'min', 'clamp', 'abs', 'sign'}
BINOPS = {'+', '-', '*', '/', '<', '>', '<=', '>=', '==', '!='}
ASSIGN = {'=', '+=', '-=', '*=', '/='}
FLOAT_BUILTINS = {'gl_FragCoord', 'gl_Position', 'gl_FragDepth', 'gl_PointSize', 'gl_PointCoord'}


def glsl_tokens(src):
    toks = []; line = 1; pre = False
    for m in _TOK.finditer(src):
        k, s = m.lastgroup, m.group()
        if k == 'ws' or k == 'com':
            line += s.count('\n'); continue
        toks.append((k, s, line))
    # drop preprocessor lines (#version, #define ...): they are not code the literal rule applies to
    lines_pp = {i + 1 for i, l in enumerate(src.split('\n')) if l.lstrip().startswith('#')}
    return [t for t in toks if t[2] not in lines_pp]


def glsl_int_literals(src):
    """-> [(glsl line, literal, why)]. A heuristic: it flags only an integer literal that is next to a float operand, assigned to a float, or an argument of a float-only builtin
    (or of max/min/clamp with a float beside it). Array indices, for-loop headers, int declarations, constructors (vec3(1) is legal) and #lines are left alone."""
    t = glsl_tokens(src); n = len(t); floats = set(FLOAT_BUILTINS); out = []
    for i in range(n - 1):                                                               # declared float-typed names (uniforms, ins, locals, parameters, comma lists)
        if t[i][0] == 'id' and t[i][1] in FLOAT_TYPES:
            j = i + 1
            while j < n and t[j][0] == 'id':
                floats.add(t[j][1]); j += 1
                depth = 0                                                                  # skip an initialiser to the next comma at depth 0
                while j < n and not (depth == 0 and t[j][1] in (',', ';', ')')):
                    depth += t[j][1] in '([{'; depth -= t[j][1] in ')]}'; j += 1
                if j < n and t[j][1] == ',' and j + 1 < n and t[j + 1][0] == 'id' and t[j + 1][1] not in FLOAT_TYPES and (j + 2 < n and t[j + 2][1] in ('=', ',', ';', '[')): j += 1
                else: break
    match = {}; st = []                                                                   # matching parens, and for each '(' the name before it
    for i, (k, s, _) in enumerate(t):
        if s in '([': st.append(i)
        elif s in ')]' and st: match[st.pop()] = i

    back = {v: k for k, v in match.items()}

    def fl(j, ahead=False):                                                                # is the operand at token j a float? (ahead: j starts it, else j ends it)
        if not 0 <= j < n: return False
        k, s, _ = t[j]
        if k == 'num': return bool(re.search(r'[.eE]', s)) and not s.lower().startswith('0x')
        if ahead:
            if k == 'id' and j + 1 < n and t[j + 1][1] == '(': return s in FLOAT_ONLY or s in FLOAT_TYPES or s in floats
            return k == 'id' and s in floats
        if k == 'id':
            if j >= 2 and t[j - 1][1] == '.': return fl(j - 2)                              # p.x, m[0].xyz, f(a).y
            return s in floats
        if s == ']' and j in back: return fl(back[j] - 1)                                 # m[0] where m is a float vector or matrix
        if s == ')' and j in back:
            o = back[j]; name = t[o - 1][1] if o and t[o - 1][0] == 'id' else ''
            return name in FLOAT_ONLY or name in FLOAT_TYPES or name in floats
        return False

    stack = []                                                                             # (open index, name before it, kind)
    for i, (k, s, ln) in enumerate(t):
        if s in '([':
            name = t[i - 1][1] if i and t[i - 1][0] == 'id' else ''
            stack.append((i, name, s)); continue
        if s in ')]':
            if stack: stack.pop()
            continue
        if k != 'num' or re.search(r'[.eE]', s) or s.lower().startswith('0x') or s.endswith(('u', 'U')): continue
        if any(o[2] == '[' or o[1] in ('for', 'layout') for o in stack): continue
        why = None
        p = i - 1
        if p >= 0 and t[p][1] == '-' and (p == 0 or t[p - 1][0] == 'op' and t[p - 1][1] not in (')', ']')): p -= 1   # unary minus
        if p >= 0 and t[p][1] in BINOPS and fl(p - 1): why = 'next to float %s' % (t[p - 1][1] if t[p - 1][0] != 'op' else 'expression')
        if not why and i + 2 < n and t[i + 1][1] in BINOPS and fl(i + 2, True): why = 'next to float %s' % t[i + 2][1]
        if not why and p >= 0 and t[p][1] in ASSIGN:
            q = p - 1
            if q >= 0 and t[q][1] == ']':                                                     # a[i] = 1: look before the bracket
                d = 0
                while q >= 0:
                    d += t[q][1] == ']'; d -= t[q][1] == '['
                    if d == 0: break
                    q -= 1
                q -= 1
            if q >= 0 and t[q][0] == 'id' and t[q][1] in floats: why = 'assigned to float %s' % t[q][1]
        if not why and stack and stack[-1][2] == '(':
            o, name, _ = stack[-1]
            if name in FLOAT_ONLY: why = 'argument of %s()' % name
            elif name in MIXED and any(fl(j) for j in range(o + 1, match.get(o, n))): why = 'argument of %s() beside a float' % name
        if why: out.append((ln, s, why))
    return out


def _mfstrings(v):
    return re.findall(r'"((?:[^"\\]|\\.)*)"', v) or ([v] if v.strip() else [])

def shader_sources(root):
    """-> [(ComposedShader node or None, ShaderPart node, glsl text, file line of glsl line 1 or None)]"""
    out = []
    for n in root.iter():
        if n.tag not in ('ShaderPart', 'ShaderProgram'): continue
        sh = n.parent if n.parent is not None and n.parent.tag in ('ComposedShader', 'ProgramShader') else None
        body = ''.join(n.text); srcs = []
        if body.strip():
            b = body.lstrip(); lead = body[:len(body) - len(b)]; first = (n.text_line or n.line)
            if b.startswith('data:'):
                head, _, b = b.partition(',')
            srcs.append((b, first + lead.count('\n')))
        for u in _mfstrings(n.a.get('url', '')):
            if u.startswith('data:'):
                head, _, b = u.partition(',')
                b = base64.b64decode(b).decode('utf-8', 'replace') if ';base64' in head else urllib.parse.unquote(b)
                srcs.append((b, None))
        for b, l0 in srcs: out.append((sh, n, b, l0))
    return out

def check_glsl(root):
    out = []
    for sh, part, src, l0 in shader_sources(root):
        for ln, lit, why in glsl_int_literals(src):
            line = l0 + ln - 1 if l0 else part.line
            out.append(F('glsl-int-literal', 'warning', part, "integer literal %s where a float is wanted (%s; glsl line %d): write %s.0" % (lit, why, ln, lit), line=line, glsl_line=ln))
        writes = re.search(r'\bgl_FragDepth\s*=', src); logd = re.search(r'x3d_LogarithmicFarFactor|\blogDepth\b', src)
        if (writes or logd):
            holder = sh if sh is not None else part
            fields = {k.a.get('name') for k in holder.kids if k.tag == 'field'}
            if 'logDepth' not in fields:
                out.append(F('glsl-logdepth', 'warning', holder, "shader %s but its %s has no logDepth field: with X_ITE's logarithmic depth on, its depth will not match the scene" % (
                    'writes gl_FragDepth' if writes else 'uses log depth', holder.tag), line=holder.line))
    return out


_SCHEME = re.compile(r'^[A-Za-z][A-Za-z0-9+.-]*:')
_GLSL_HINT = re.compile(r'^\s*#\s*(version|define|extension)\b|\b(void|uniform|precision|attribute|varying|gl_\w+|x3d_\w+)\b|;')

def check_shader_body(root):
    """An inline body is the node's url (as X_ITE reads it), so GLSL there needs a data: scheme; a quoted list or a bare relative path (no ';', no GLSL words) is a url and is left alone."""
    out = []
    for n in root.iter():
        if n.tag not in ('ShaderPart', 'ShaderProgram'): continue
        body = ''.join(n.text).strip()
        if not body or body.startswith('"') or _SCHEME.match(body) or not _GLSL_HINT.search(body): continue
        kind = 'fragment' if n.a.get('type', 'VERTEX').upper() == 'FRAGMENT' else 'vertex'
        out.append(F('shader-raw-source', 'error', n, "CDATA is raw GLSL: X_ITE reads it as the url field, resolves '%s' against the world URL and the shader fails (isValid false, "
                     "the shape draws unlit); start the CDATA with data:x-shader/x-%s," % (re.sub(r'\s+', ' ', body)[:24], kind), line=n.text_line or n.line, prefix='data:x-shader/x-%s,' % kind))
    return out


# ---- the fork --------------------------------------------------------------------------------------
def run_fork(path):
    mcp = os.environ.get('X3D_MCP', '/home/user/x3d_mcp')
    if not os.path.isdir(os.path.join(mcp, 'src', 'validation')):
        return [F('fork-skipped', 'info', None, 'X3D_MCP=%s has no fork checkout (src/validation); the XSD, semantic and profile checks did not run' % mcp)]
    r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'validate_fork.py'), path], capture_output=True, text=True, env=dict(os.environ, X3D_MCP=mcp))
    if r.returncode != 0:
        return [F('fork-failed', 'error', None, 'validate_fork.py exited %d: %s' % (r.returncode, (r.stderr.strip().splitlines() or [''])[-1]))]
    out = []; dec = json.JSONDecoder(); s = r.stdout.strip(); i = 0
    while i < len(s):
        o, j = dec.raw_decode(s, i); i = j
        while i < len(s) and s[i].isspace(): i += 1
        if not o.get('xsd_valid'): out.append(F('fork-xsd', 'error', None, 'XSD invalid: %s' % '; '.join(o.get('xsd_errors') or ['(no message)'])))
        sem = o.get('semantic'); errs = None
        if isinstance(sem, dict):
            e = sem.get('errors', sem.get('error_count'))
            errs = len(e) if isinstance(e, list) else e
        elif isinstance(sem, str):
            m = re.search(r'(\d+)\s+errors?', sem); errs = int(m.group(1)) if m else None
        if errs: out.append(F('fork-semantic', 'error', None, '%s semantic errors' % errs))
        if o.get('profile_ok') is False: out.append(F('fork-profile', 'error', None, 'profile not OK: %s' % o.get('profile')))
        if not out: out.append(F('fork-ok', 'info', None, 'fork: XSD valid, %s semantic errors, profile OK' % (errs or 0)))
    return out


# ---- driver ----------------------------------------------------------------------------------------
def gate(text, asset=None):
    """X3D text -> list of findings (no file key). asset: True/False forces the asset-export rule, None detects it from the generator meta."""
    try: root = parse(text)
    except xml.parsers.expat.ExpatError as e:
        return [{'rule': 'parse-error', 'severity': 'error', 'line': e.lineno, 'node': '', 'message': str(e)}]
    out = check_routes(root) + check_colours(root) + check_xite(root) + check_glsl(root) + check_shader_body(root)
    strip = asset if asset is not None else is_asset_export(root)
    if strip: out += check_asset_nodes(root)
    out += [d for d in check_precision(root) if not (strip and d['node'].split()[0] in ASSET_ONLY_NOT)]   # no byte count for a node that is to be stripped anyway
    return sorted(out, key=lambda d: (SEV[d['severity']], d['line']))

def gate_file(path, asset=None, fork=False):
    with open(path, encoding='utf-8') as fh: out = gate(fh.read(), asset)
    if fork: out += run_fork(path)
    for d in out: d['file'] = path
    return out


def main(argv):
    args = [a for a in argv if not a.startswith('--')]; opts = {a for a in argv if a.startswith('--')}
    unknown = opts - {'--json', '--fork', '--asset', '--scene'}
    if unknown or not args:
        print(__doc__.strip() if not unknown else 'unknown option: %s' % ' '.join(sorted(unknown)), file=sys.stderr); return 2
    asset = True if '--asset' in opts else False if '--scene' in opts else None
    allf = []
    for p in args: allf += gate_file(p, asset, '--fork' in opts)
    if '--json' in opts: print(json.dumps(allf, indent=1))
    else:
        for d in allf: print('%s:%d: %s %s [%s] %s' % (d['file'], d['line'], d['severity'], d['rule'], d['node'], d['message']))
        c = {s: sum(d['severity'] == s for d in allf) for s in SEV}
        print('%d files: %d errors, %d warnings, %d info' % (len(args), c['error'], c['warning'], c['info']))
    if any(d['rule'] == 'parse-error' for d in allf): return 2
    return 1 if any(d['severity'] == 'error' for d in allf) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
