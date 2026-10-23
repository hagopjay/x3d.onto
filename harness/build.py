#!/usr/bin/env python3
"""Ontology explorer data harness.

Reads an X3D Ontology Turtle file (read-only), derives a compact JSON model for the
explorer and the X3D constellation, and writes a manifest with hashes.
Every number the UI shows is computed here or carried with an explicit source tag.

usage: build.py <X3dOntology.ttl> [out_dir]
Run with a python that has rdflib (x3d_mcp's .venv works).
"""
import hashlib, json, math, sys, time, collections
from pathlib import Path
import rdflib
from rdflib import RDF, RDFS, OWL

TTL = Path(sys.argv[1]).expanduser()
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else Path(__file__).resolve().parent.parent / "data")
OUT.mkdir(parents=True, exist_ok=True)
STEM = sys.argv[3] if len(sys.argv) > 3 else "ontology"

g = rdflib.Graph()
g.parse(str(TTL), format="turtle")
# namespace comes from the file's owl:Ontology-adjacent class IRIs
sample = next(s for s in g.subjects(RDF.type, OWL.Class) if isinstance(s, rdflib.URIRef))
NS = str(sample).rsplit("#", 1)[0] + "#"
U = lambda t: rdflib.URIRef(NS + t)
nm = lambda x: str(x)[len(NS):] if str(x).startswith(NS) else str(x)
iri_in_ns = lambda x: isinstance(x, rdflib.URIRef) and str(x).startswith(NS)

UOM = {}
_uom = Path(__file__).resolve().parent.parent / "data" / "uom_concrete.json"
if _uom.exists():
    UOM = json.loads(_uom.read_text())["nodes"]

UNIVERSAL = {"DEF", "USE", "hasIS", "hasMetadata", "class", "id", "style"}
ACCESS = {"accessTypeInputOutput": "inputOutput", "accessTypeInitializeOnly": "initializeOnly",
          "accessTypeInputOnly": "inputOnly", "accessTypeOutputOnly": "outputOnly"}

classes = sorted(nm(c) for c in g.subjects(RDF.type, OWL.Class) if iri_in_ns(c))
cset = set(classes)
parents = {c: sorted(nm(o) for o in g.objects(U(c), RDFS.subClassOf) if iri_in_ns(o) and nm(o) in cset) for c in classes}
children = collections.defaultdict(list)
for c, ps in parents.items():
    for p in ps:
        children[p].append(c)

# depth = shortest path to a root; primary parent = shallowest, ties alphabetical
depth, primary = {}, {}
def dep(c, stack=()):
    if c in depth: return depth[c]
    if c in stack: return 0
    ps = parents[c]
    if not ps:
        depth[c] = 0; primary[c] = None; return 0
    best = min(ps, key=lambda p: (dep(p, stack + (c,)), p))
    depth[c] = dep(best, stack + (c,)) + 1; primary[c] = best
    return depth[c]
for c in classes: dep(c)

def ancestors(c):
    seen, todo = set(), [c]
    while todo:
        x = todo.pop()
        for p in parents[x]:
            if p not in seen: seen.add(p); todo.append(p)
    return seen
anc = {c: ancestors(c) for c in classes}
desc_n = {c: sum(1 for d in classes if c in anc[d]) for c in classes}

# properties
def prop_info(p):
    name = nm(p)
    kind = "obj" if (p, RDF.type, OWL.ObjectProperty) in g else "dt"
    sup = {nm(o) for o in g.objects(p, RDFS.subPropertyOf)}
    acc = sorted(ACCESS[a] for a in sup if a in ACCESS)
    rng = sorted(nm(o) for o in g.objects(p, RDFS.range) if iri_in_ns(o))
    dom = sorted(nm(o) for o in g.objects(p, RDFS.domain) if iri_in_ns(o) and nm(o) in cset)
    dfl = sorted({str(o) for o in g.objects(p, U(name + "Default"))})
    defn = sorted({str(o) for o in g.objects(p, RDFS.label)})
    return name, dict(kind=kind, access=acc, range=rng, dom=dom, dflt=dfl[:6], ndflt=len(dfl), defs=[d[:240] for d in defn[:3]], ndefs=len(defn))

hc = U("hasChild")
child_family = {p for p in g.transitive_subjects(RDFS.subPropertyOf, hc)}
props = {}
for p in set(g.subjects(RDF.type, OWL.ObjectProperty)) | set(g.subjects(RDF.type, OWL.DatatypeProperty)):
    if not iri_in_ns(p) or nm(p).startswith("accessType"): continue
    name, info = prop_info(p)
    info["child"] = p in child_family
    props[name] = info

fields = collections.defaultdict(list)
for name, info in props.items():
    for d in info["dom"]:
        fields[d].append(name)

# containment as the x3d_mcp tool computes it: hasChild family, named IRI ranges, not X3DNode
cont = []
for p in child_family:
    name = nm(p)
    if name == "hasChild" or name not in props: continue
    info = props[name]
    cont.append(dict(p=name, dom=info["dom"], rng=info["range"]))
def node_parents(c):
    reach = anc[c] | {c}
    out = set()
    for e in cont:
        for r in e["rng"]:
            if r != "X3DNode" and r in reach:
                for d in e["dom"]:
                    out.add((d, e["p"]))
    return sorted(out)
legal_parents = {c: node_parents(c) for c in classes}

# which classes can a node contain (inverse, concrete or abstract ranges expanded)
contains = collections.defaultdict(set)
for c in classes:
    for d, p in legal_parents[c]:
        contains[d].add((c, p))

# families: ancestor at depth 2 below X3DNode (else depth 1, else self)
def family(c):
    chain = [c]
    while primary[chain[-1]]: chain.append(primary[chain[-1]])
    chain.reverse()  # root..c
    if chain[0] != "X3DNode": return chain[0]
    return chain[min(2, len(chain) - 1)] if len(chain) > 2 else chain[-1]
fam = {c: family(c) for c in classes}

# radial tree layout by primary parent, virtual root; angle share ~ leaf weight
kids = collections.defaultdict(list)
roots = [c for c in classes if primary[c] is None]
for c in classes:
    if primary[c]: kids[primary[c]].append(c)
leafw = {}
def lw(c):
    if c in leafw: return leafw[c]
    k = kids[c]
    leafw[c] = 1 if not k else sum(lw(x) for x in k)
    return leafw[c]
for r in roots: lw(r)
RSTEP = 150
pos = {}
def place(c, a0, a1):
    d = depth[c] + 1
    a = (a0 + a1) / 2
    pos[c] = (round(math.cos(a) * d * RSTEP, 1), round(math.sin(a) * d * RSTEP, 1), round(a, 4))
    k = sorted(kids[c], key=lambda x: (-leafw[x], x))
    tot = sum(leafw[x] for x in k)
    cur = a0
    for x in k:
        span = (a1 - a0) * leafw[x] / tot
        place(x, cur, cur + span); cur += span
roots_sorted = sorted(roots, key=lambda x: (-leafw[x], x))
tot = sum(leafw[r] + 3 for r in roots_sorted)
cur = 0.0
for r in roots_sorted:
    span = 2 * math.pi * (leafw[r] + 3) / tot
    place(r, cur + 0.01, cur + span - 0.01); cur += span

nodes = []
for c in classes:
    lab = sorted({str(o) for o in g.objects(U(c), RDFS.label)})
    fl = sorted(f for f in fields[c])
    own = [f for f in fl if f not in UNIVERSAL]
    nodes.append(dict(
        id=c, par=parents[c], pp=primary[c], d=depth[c], fam=fam[c],
        x=pos[c][0], y=pos[c][1], a=pos[c][2],
        kids=len(children[c]), desc=desc_n[c],
        kind=("concrete" if c in UOM else ("abstract" if c.startswith("X3D") else "other")) if UOM else ("abstract" if c.startswith("X3D") else "concrete"),
        comp=UOM.get(c, {}).get("component", ""), lvl=UOM.get(c, {}).get("level", 0), cf=UOM.get(c, {}).get("containerField", ""),
        nf=len(own), fields=own, lp=legal_parents[c], nc=len(contains.get(c, ())),
        defn=lab[0][:600] if lab else "", ancs=sorted(anc[c], key=lambda a: depth[a])))

# honest cross-check overlay: values carried from DOC.md section 2 (Confirmed, fork eb4b4b4, 4.1 ontology)
XCHECK_4_1 = {  # child: (predicted, xsd_accepts, xsd_rejects, inconclusive)
    "Sphere": (10, 5, 3, 2), "Box": (10, 5, 3, 2), "Material": (3, 2, 0, 1), "Appearance": (2, 2, 0, 0),
    "Coordinate": (15, 14, 1, 0), "PointLight": (57, 24, 27, 6), "TimeSensor": (57, 24, 27, 6),
    "Transform": (57, 21, 30, 6), "Shape": (59, 22, 30, 7), "ImageTexture": (78, 31, 42, 5)}
mine_pred = {c: len(legal_parents[c]) for c in XCHECK_4_1 if c in legal_parents}
mine_conc = {c: sum(1 for d, _ in legal_parents[c] if d in UOM) for c in XCHECK_4_1 if c in legal_parents}

# SPARQL gallery: run for real with rdflib at build time
PFX = f"PREFIX x3d: <{NS}>\nPREFIX owl: <http://www.w3.org/2002/07/owl#>\nPREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\nPREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n"
QUERIES = [
 ("q1", "Direct subclasses of X3DChildNode", "SELECT ?c WHERE { ?c rdfs:subClassOf x3d:X3DChildNode } ORDER BY ?c"),
 ("q2", "Classes with more than one parent class", "SELECT ?c (COUNT(?p) AS ?n) WHERE { ?c rdfs:subClassOf ?p . FILTER(isIRI(?p)) } GROUP BY ?c HAVING (COUNT(?p) > 1) ORDER BY DESC(?n) ?c"),
 ("q3", "Fields declared on Sphere", "SELECT ?f WHERE { ?f rdfs:domain x3d:Sphere } ORDER BY ?f"),
 ("q4", "hasChild-family properties whose range is X3DGeometryNode", "SELECT ?p WHERE { ?p rdfs:subPropertyOf+ x3d:hasChild ; rdfs:range x3d:X3DGeometryNode } ORDER BY ?p"),
 ("q5", "Which nodes may directly carry a geometry field", "SELECT DISTINCT ?d WHERE { x3d:geometry rdfs:domain ?d } ORDER BY ?d"),
 ("q6", "Domains of inputOnly fields (first 25)", "SELECT ?f WHERE { ?f rdfs:subPropertyOf x3d:accessTypeInputOnly } ORDER BY ?f LIMIT 25"),
]
gallery = []
for qid, title, q in QUERIES:
    t0 = time.perf_counter()
    rows = [[nm(v) if v is not None else "" for v in row] for row in g.query(PFX + q)]
    gallery.append(dict(id=qid, title=title, sparql=q, rows=rows[:60], n=len(rows), ms=round((time.perf_counter() - t0) * 1000, 1)))

fam_counts = collections.Counter(fam[c] for c in classes)
dt_classes = sorted(nm(s) for s in g.subjects(RDF.type, RDFS.Datatype) if iri_in_ns(s))
stats = dict(triples=len(g), classes=len(classes), object_props=len(set(g.subjects(RDF.type, OWL.ObjectProperty))),
             datatype_props=len(set(g.subjects(RDF.type, OWL.DatatypeProperty))), props_in_model=len(props),
             uom_concrete=len(UOM), datatypes=len(dt_classes),
             child_family=len(cont), multi_parent=sum(1 for c in classes if len(parents[c]) > 1),
             max_depth=max(depth.values()), roots=roots_sorted)
data = dict(stats=stats, ns=NS, nodes=nodes, props=props, cont=cont, gallery=gallery,
            xcheck=dict(src="DOC.md section 2 (Confirmed); fork eb4b4b4; 4.1 ontology vs XSD 4.1",
                        table=XCHECK_4_1, totals=dict(predicted=348, accepts=150, rejects=163, inconclusive=35),
                        mine_pred_this_file=mine_pred, mine_concrete_parent_pairs_this_file=mine_conc),
            families=dict(fam_counts), datatypes=dt_classes)
blob = json.dumps(data, separators=(",", ":"), sort_keys=True)
(OUT / f"{STEM}.json").write_text(blob)
man = dict(built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), input=str(TTL), input_sha256=hashlib.sha256(TTL.read_bytes()).hexdigest(),
           input_bytes=TTL.stat().st_size, rdflib=rdflib.__version__, output=f"{STEM}.json", output_sha256=hashlib.sha256(blob.encode()).hexdigest(),
           output_bytes=len(blob), stats=stats)
(OUT / ("manifest.json" if STEM == "ontology" else f"manifest.{STEM}.json")).write_text(json.dumps(man, indent=1))
print(json.dumps(stats))
print("pairs (this file):", sum(mine_pred.values()), "| concrete-parent pairs:", sum(mine_conc.values()), mine_conc)
print("bytes", len(blob), "sha", man["output_sha256"][:12])
