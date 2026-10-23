# Cross-domain potential of validator-backed MCP servers

## Inside X3D (measured, grade C; data/components.json; containment fields only, 7,604 pairs)
Each X3D component is a domain of its own. Share of the ontology's predicted placements that the XSD accepts, and how often X3DUOM's lists agree with the XSD:
- Highest accepted share: Sound 73.3% (agreement 93.5%), Rendering 70.2%, Shape 64.3%, Texturing 63.2%.
- Lowest accepted share: Layering 10.9% (agreement 56.5%), CubeMapTexturing 16.4%, Layout 18.6% (67.4%), Shaders 22.2%, **RigidBodyPhysics 25.3% (76.6%)**, Core 29.2% (76.4%).
- Reading (L): the more specialist a component's vocabulary, the less the supertype-level ranges say. RigidBodyPhysics is where the physics checks in the fork (X-09, X-10) were added.
- X3DUOM's lists agree with the XSD on 100% of the pairs they can judge for 13 components (Followers, Interpolation, Picking, Lighting, ...) and are weakest for Layering, Geometry2D, Layout, Geometry3D.

## Beyond X3D (my estimates, grade S; not measured)
Scored 0-3 on five criteria: spec as data, exact checker exists, fast and cheap, agents fail costly, provenance matters. Highest fit before any weighting: buildings (IFC/BIM), API contracts, glTF/USD, health records (FHIR), geospatial (OGC/CityJSON), finance (XBRL). Closest to this project: glTF/USD (same loop, other format), robotics URDF/SDF (physics), geospatial (X3D's Geospatial component), CAD STEP (X3D's CAD component). The validators named in the interactive view are ones I know of, not ones I tested.

## The reusable pattern (grade C numbers, from X3D)
Spec as data -> exact oracle -> agent loop with the report -> a second layer for what the oracle cannot see -> ontology as a map, not a gate -> a tether in the artifact. A portable tool kit: describe, validate, explain, repair, map, record.

## Prototyped 2026-10-21 (xdomain/README.md)
URDF (own rules, L) and glTF (Khronos validator, C) behind one MCP server with the same report shape and tether. Findings: the pattern ports; oracle severity is not gate policy (Khronos warns on a required unsupported extension); valid is not placed (URDF contact rule); no model was called, so agent failure rates remain unmeasured. USD not done.
