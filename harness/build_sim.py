#!/usr/bin/env python3
"""Parse sim/*.ttl (SIMULATED vocabulary) and the real x3d_mcp test fixture, resolve every grounding against the 4.1 model, write data/sim.json.
usage: build_sim.py [x3d_mcp checkout]   (needs rdflib)"""
import json, sys, collections
from pathlib import Path
import rdflib
from rdflib import RDF, RDFS
HERE = Path(__file__).resolve().parent.parent
MCP = Path(sys.argv[1] if len(sys.argv) > 1 else "~/Projects/x3d/x3d_mcp").expanduser()
M = json.loads((HERE / "data" / "ontology41.json").read_text())
N = {n["id"]: n for n in M["nodes"]}; P = M["props"]
SIM = "https://example.invalid/sim/spatial-cognition#"; X = M["ns"]
nm = lambda u: str(u).split("#")[-1]
def field_ok(node, f):
    if node not in N: return False, "node missing"
    chain = [node] + N[node]["ancs"]
    p = P.get(f)
    if p and any(c in p["dom"] for c in chain): return True, ""
    if any(f in N[c]["fields"] for c in chain if c in N): return True, ""
    return False, "no such field on node or ancestors"
concepts, mods, total_triples = [], [], 0
for f in sorted((HERE / "sim").glob("*.ttl")):
    g = rdflib.Graph(); g.parse(str(f), format="turtle"); total_triples += len(g)
    cs = [s for s, o in g.subject_objects(RDF.type) if str(o) in (SIM + "Concept", SIM + "Rung")]
    for c in sorted(cs, key=nm):
        v = lambda p: next((str(o) for o in g.objects(c, rdflib.URIRef(SIM + p))), None)
        nodes = [{"n": nm(o), "ok": nm(o) in N} for o in g.objects(c, rdflib.URIRef(SIM + "x3dNode"))]
        fields = []
        for b in g.objects(c, rdflib.URIRef(SIM + "x3dField")):
            nd = nm(next(g.objects(b, rdflib.URIRef(SIM + "onNode")))); fd = str(next(g.objects(b, rdflib.URIRef(SIM + "field"))))
            ok, why = field_ok(nd, fd); fields.append({"n": nd, "f": fd, "ok": ok, "why": why})
        concepts.append(dict(id=nm(c), module=v("module"), label=v("label") or str(next(g.objects(c, RDFS.label), "")),
                             comment=str(next(g.objects(c, RDFS.comment), "")), grade=v("grade"), origin=v("origin"), rung=v("rung"),
                             tol=v("tolerance"), check=str(next(g.objects(c, rdflib.URIRef(SIM + "checkedBy")), "")) or None, basis=str(next(g.objects(c, rdflib.URIRef(SIM + "basis")), "")) or None,
                             kind="rung" if str(SIM + "Rung") in {str(o) for o in g.objects(c, RDF.type)} else "concept", nodes=sorted(nodes, key=lambda z: z["n"]), fields=sorted(fields, key=lambda z: (z["n"], z["f"]))))
    mods.append(dict(id=f.stem, file=f"sim/{f.name}", triples=len(g), concepts=len(cs)))
# the real fixture shipped in the fork's tests (2 concepts), in the real sc: namespace; reported separately
fx = MCP / "tests/fixtures/ontology_ext/mini_spatial.ttl"; fixture = None
if fx.exists():
    g = rdflib.Graph(); g.parse(str(fx), format="turtle")
    SC = "https://w3id.org/spatial-cognition#"; rows = []
    for c in g.subjects(RDF.type, rdflib.URIRef(SC + "Concept")):
        for o in g.objects(c, rdflib.URIRef(SC + "x3dNode")):
            rows.append(dict(concept=nm(c), node=nm(o), resolved=nm(o) in N))
    fixture = dict(file="x3d_mcp/tests/fixtures/ontology_ext/mini_spatial.ttl", triples=len(g), namespace=SC, rows=rows, note="real test fixture; one grounding is deliberately unresolvable")
ng = sum(len(c["nodes"]) for c in concepts); nr = sum(1 for c in concepts for z in c["nodes"] if z["ok"])
fg = sum(len(c["fields"]) for c in concepts); fr = sum(1 for c in concepts for z in c["fields"] if z["ok"])
unres = [dict(concept=c["id"], **z) for c in concepts for z in c["fields"] if not z["ok"]] + [dict(concept=c["id"], n=z["n"], f="(node)", why="class not in 4.1 ontology") for c in concepts for z in c["nodes"] if not z["ok"]]
out = dict(banner="SIMULATED: not Dr. Polys's sc: ontology; grade S; see sim/ and harness/gen_sim.py",
           reported_real=dict(source="README (27) finding 4 / DOC section 1 via fork PR #5 body, grade L", files=16, triples=418, x3d_terms_resolved=58, groundings_joined=41, namespace="https://w3id.org/spatial-cognition#"),
           modules=mods, concepts=concepts, fixture=fixture,
           stats=dict(files=len(mods), triples=total_triples, concepts=len(concepts), node_groundings=ng, node_resolved=nr, field_groundings=fg, field_resolved=fr, unresolved=unres,
                      by_rung=dict(collections.Counter(str(c["rung"]) for c in concepts if c["rung"] is not None)),
                      grounded_nodes=sorted({z["n"] for c in concepts for z in c["nodes"] if z["ok"]})))
(HERE / "data" / "sim.json").write_text(json.dumps(out, separators=(",", ":")))
print(json.dumps(out["stats"]["unresolved"], indent=0)[:1500]); print({k: v for k, v in out["stats"].items() if k not in ("unresolved", "grounded_nodes")}, "fixture", fixture and fixture["rows"])
