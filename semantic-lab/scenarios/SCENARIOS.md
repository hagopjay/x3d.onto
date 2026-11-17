# Ontology + X3D scenarios, spec v1 (16 Nov 2026)

Ask (HagopJay, 16 Nov 14:25Z): 2-3 practical, insightful scenarios from different parts of society/industry showing how ontologies and X3D, as the visual information hub, work together. Picked on the card: **heritage, factory, hospital**.

Thesis carried from the lab: the ontology proposes, SHACL shapes dispose, the validator gates. New line for this set: **X3D says where and what it looks like; the ontology says what it is, why it matters and what rules it must obey. Questions that need both are the point.**

Every scenario has the same five-part spine, all live in the page (N3.js + Comunica + shacl-engine, same stack as the lab), all cross-checked in Python (rdflib + pyshacl):
1. **Scene**: a compact X3D 4.x scene, every meaningful node DEF'd, validated (x3d_mcp XSD + semantic), drawn by X_ITE.
2. **Domain graph**: instance data in a real open ontology, joined to the scene by one bridge property per node (`ex:depictedBy` -> the scene's DEF IRI from the faithful X3D->Turtle twin).
3. **Three questions** (SPARQL) that need BOTH graphs; the answer lights up in 3D.
4. **Two checks** (SHACL, incl. SPARQL constraints over X3D coordinates) that catch a scene contradicting the domain, or the domain contradicting the scene; a fault switch plants each one.
5. **One inference** that turns domain structure into what the viewer sees (transitive part-of, hosting chains, containment).
Plus: "why it takes both" box, the MCP calls an LLM would make (scene_to_rdf, sparql_scene, shacl_validate with extra_shapes_ttl), receipts with sources and C/L/S grades.

Scene rule for coordinates: equipment sits in flat, unrotated Transforms under one root, so world position = translation (documented on the page); SHACL-SPARQL reads `x3do:translation` lists.

## S1 Heritage: "The Osiris Shaft as a living record" (Giza)
- Ontologies: CIDOC-CRM 7.1.3 (CC BY 4.0) + CRMinf-style belief modelling (attribute assignment with a confidence tier); PROV-O for the model's own making.
- Scene: new compact Osiris Shaft study (levels 1-3, Chamber B with six side chambers, granite sarcophagus, the speculative Hall of Records link), tier colours documented cyan / theorized amber / speculative magenta, derived from giza-osiris-hall v1 (CC0 geometry; never overwrite v1).
- Domain: the v1 claims ledger (12 rows, each with tier, source, grade, viewpoint) becomes E13 Attribute Assignments; competing depth accounts (about 25 m, 30 m, 41.48 m) become three E16 Measurements of one E25 feature.
- Questions: (a) "show every element whose only support is Suspected" (spotlight magenta); (b) "where do the sources disagree about a dimension, and by how much" (three depth rulers light up with their source); (c) "what does the drawn model measure versus the record" (X3D Box/Cylinder size vs E54 value).
- Checks: every speculative element must carry an attribution with a source (plant: an untagged chamber); a drawn dimension must match a Documented measurement within 5 % (plant: shaft A drawn 12 m against 9.62 m).
- Inference: P46 is composed of (transitive) -> "everything inside Level 2" lights as one.
- Insight: the 3D model becomes the index of the archive, and the ontology keeps fact, theory and speculation apart in the picture itself.

## S2 Factory: "Cell 7, the line that checks its own layout"
- Ontologies: IDTA Asset Administration Shell RDF (aas-specs), W3C SOSA/SSN, QUDT units 3.x.
- Scene: assembly cell: 6-axis robot (joint Transform chain + interpolators), conveyor, three stations, a fence with a gate, five sensors (temperature, vibration, light curtain).
- Domain: each asset has a Shell with Nameplate and TechnicalData submodels (max reach, payload, rated temperature with QUDT unit); SOSA observations with mixed units (degC, degF, mm/s).
- Questions: (a) "which sensors read above their asset's rating, in one unit" (QUDT conversion inside SPARQL; red); (b) "what stops downstream if station 2 fails" (feeds chain); (c) "which assets lack a maintenance submodel".
- Checks: the robot's pick and place points must be within its AAS max reach, measured from X3D positions (plant: station 3 moved 0.4 m out of reach); every sensor's unit must be dimensionally right for its observed property (plant: vibration in degC).
- Inference: sosa:hosts / isHostedBy plus a feeds-into chain -> the whole affected line.
- Insight: the layout is checked against datasheets before steel is cut; the twin becomes the HMI.

## S3 Hospital: "Operating Room 4, ready or not"
- Ontologies: HL7 FHIR R5 RDF (fhir.ttl, open), W3C BOT (building topology). SNOMED CT left out (licensed); codes shown as plain FHIR CodeableConcept text.
- Scene: OR with table, anaesthesia machine, two surgical lights, C-arm, instrument tables, scrub sink, doors; sterile field drawn as a translucent zone.
- Domain: BOT building/storey/space/element; FHIR Device (status, next maintenance), Location, a scheduled Procedure with its required device list.
- Questions: (a) "is everything today's procedure needs in OR 4 and in service" (green; missing device = amber ghost); (b) "which devices are past their maintenance date" (red); (c) "route a C-arm from storage to OR 4" (BOT adjacency, the path lights).
- Checks: no non-sterile device inside the sterile field radius, from X3D positions (plant: a cart inside); a Device marked in use must be in the space its Location says (plant: scene and record disagree).
- Inference: bot:containsElement / hasSpace -> storey and building views roll up.
- Insight: facilities data, clinical scheduling and the room's geometry meet in one view; readiness is checked, not assumed.

## Gates
Private artifact preview first; x3d.demo only on his word. No SNOMED. Licences: CIDOC-CRM CC BY 4.0, BOT CC BY 1.0, SOSA/SSN W3C, QUDT CC BY 4.0, AAS specs (CC BY 4.0, check), FHIR (CC0/open). Leak sweep before publish. Every number names its source and grade. Never call the ontology a gate.
