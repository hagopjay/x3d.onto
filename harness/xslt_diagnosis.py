#!/usr/bin/env python3
"""Why does the ontology over-predict? Count, per hasChild-family property in the 4.1 Turtle, how many parents (rdfs:domain) and ranges it accumulated.
The stylesheet (data/xslt/X3duomToX3dOntology.xslt, read in full) emits one `:has<Field>` property per declaring node, each with a single domain and its own
acceptableNodeTypes range; Turtle merges same-named subjects, so the pairing of domain with range is lost. This script measures that merge.
usage: xslt_diagnosis.py   (needs rdflib) -> data/xslt_diagnosis.json"""
import json, collections
from pathlib import Path
import rdflib
from rdflib import RDF, RDFS, OWL, BNode
H = Path(__file__).resolve().parent.parent / "data"
g = rdflib.Graph(); g.parse(str(H / "X3dOntology4.1.ttl"), format="turtle")
NS = "https://www.web3d.org/specifications/X3dOntology4.1#"; nm = lambda x: str(x)[len(NS):] if str(x).startswith(NS) else str(x)
hc = rdflib.URIRef(NS + "hasChild")
rows = []
for p in set(g.transitive_subjects(RDFS.subPropertyOf, hc)):
    if p == hc: continue
    dom = [o for o in g.objects(p, RDFS.domain)]
    rng_iri = [o for o in g.objects(p, RDFS.range) if not isinstance(o, BNode)]
    rng_union = [o for o in g.objects(p, RDFS.range) if isinstance(o, BNode)]
    union_members = set()
    for b in rng_union:
        for lst in g.objects(b, OWL.unionOf):
            union_members |= {nm(x) for x in rdflib.collection.Collection(g, lst)}
    rows.append(dict(prop=nm(p), domains=len(dom), iri_ranges=len(rng_iri), union_ranges=len(rng_union), union_members=len(union_members),
                     ranges_total=len(rng_iri) + len(union_members)))
rows.sort(key=lambda r: -(r["domains"] * max(1, r["ranges_total"])))
shared = [r for r in rows if r["domains"] > 1]
res = dict(properties=len(rows), shared_domain_properties=len(shared), single_domain=len(rows) - len(shared),
           max_domains=max(r["domains"] for r in rows), top=rows[:12],
           xslt=dict(file="data/xslt/X3duomToX3dOntology.xslt", lines=1220, bytes=67046, sha1="f443c05f480795a5b3d71a01d0839bf20d105f80", range_from="@acceptableNodeTypes (lines 787-807 abstract branch, 970-990 concrete branch)",
                     per_parent_inverse="fieldXHasParent[Parent] (lines 1114-1139); parent name omitted when field is 'children' (line 1119)",
                     domain_comment="lines 755-756: no owl:unionOf for rdfs:domain, 'simple unadorned list' instead"))
(H / "xslt_diagnosis.json").write_text(json.dumps(res, indent=1))
print(json.dumps({k: v for k, v in res.items() if k not in ("xslt",)}, indent=0)[:2400])
