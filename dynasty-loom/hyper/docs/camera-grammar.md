# Camera grammar for the dynasty hypersphere

Radius is time: founders at the core, the as-of year at the shell (R = 10). Houses are azimuth sectors west to east (founders' house at +Z, angle ∝ 2 + people). Lineages are fibers; a marriage is an arc on the shell of its year. Pocket units; the pocket sits in its host at scale 0.5.

Generator: `tools/build_camera_proof.py` (loom-view.json → `shots-<fam>.json`, `hyper-<fam>.x3d`, `camera*.x3d`). Proof: `proof/camera.html` + `camera.js`, driven by `tools/drive_camera.js`; results in `proof/camera-proof.json`.

## Shots

`sph(az, el, d)` is a point at distance d from the centre. "Fill" is the share of the frame height the subject's bounding sphere fills, so d = r / (fill · tan(fov/2)).

| Shot | Size | Beat | Position and target from data | fov | Move in |
|---|---|---|---|---|---|
| Host | ELS | A small bright world inside a larger one | Host space: target the pocket centre, el 14°, pocket fills 40% | 0.90 | Bound at load |
| Inside | POV | Everything grows out of the core | Founders' axis uf: pos −2.6·uf + 0.55Y − 0.45·side, target 6·uf + Y + 0.4·side (just outside the core glow) | 1.15 | **Plunge**: 7 s, from Host through the shell |
| Colossus | MS, low | The largest house towers over you | Largest sector φ: pos sph(φ, −40°, 8.4), target sph(φ, 18°, 2.2) | 1.22 | Flight |
| EyeToEye | CU, rolled | One life at one year | Year = first dated marriage, else first child's birth, else mid-life (marked computed); point at r(year) on that life's fiber; up = radial (time-up); lead room in the direction of the next marriage | 0.62 | Flight |
| Crown | LS, top | The houses as a compass | sph(π, 74°, d), shell fills 86% | 1.00 | Flight |
| House_<h> | MS | One house | Sector bisector; the sector's chord fills 70% of the width; at least R + 1.5 out | 0.75 | Flight |
| Present | MCU, rolled | One person's whole life, parents and marriages | The life segment fills 62% of the height, el 10°, up radial | 0.75 | Flight, or **pick** (click a bead) |
| Wide | LS | The whole dynasty at once | sph(0, 16°, d), shell fills 74% | 0.80 | Flight |
| Flywheel | LS | Idle: the world keeps turning | sph(0, 20°, 23) on a rig that turns once in 120 s | 0.85 | Native bind, 2.4 s; idle after 40 s |

## Recipes

**Every shot (standard X3D).** One `Viewpoint` per shot (DEF = name, description = beat, centerOfRotation = target); any X3D browser gets them with `NavigationInfo transitionType='ANIMATE' transitionTime='1.6'`. The pocket EXPORTs them; the host IMPORTs them via `Inline DEF='Pocket'`.

**Rolled shots (EyeToEye, Present).** Put the Viewpoint in `Transform DEF='Frame_<shot>'` whose +Y is the shot's up, with zero roll inside. X_ITE's EXAMINE straightens to the Viewpoint's local Y on every bind and first drag: at the root the horizon snaps 59.9° → 0° (Confirmed, control); in an up frame roll stays 0.

**Flights (page side, `flyTo`).** These use one `Viewpoint DEF='Probe'` inside `Transform DEF='ProbeFrame'`.
1. Read the real pose from `ProximitySensor DEF='CamSense'` (size 1e6); it reports in pocket units through the scaled Inline.
2. Set the NavigationInfo to TELEPORT. Write the Probe at that pose, with ProbeFrame turned to the camera's **current** up, then `set_bind`. This binds with zero roll, so nothing jumps.
3. Each frame: van Wijk–Nuij zoom-and-pan (ρ = √2) on a quintic-smootherstep clock; the direction slerps with ease(1.15k − 0.075), and fov and up follow. Write `position`, `orientation`, `fieldOfView` and `centerOfRotation` (= target) in ProbeFrame's local frame.
4. Arrival: restore the transition type, turn ProbeFrame to the shot's up, rewrite the same world pose, no rebind. Switch NavigationInfo 3 frames later and only if its type changes (its bind straightens again).

Duration = clamp(2.2 + 0.55·S + 0.9·turn, 3.5, 7.5) s, where S is the path length in the screen widths van Wijk measures and turn is in radians. The plunge is fixed at 7 s.

**Plunge.** A Probe flight Host → Inside, crossing `ProximitySensor DEF='ShellSense'` (20³, "enter pocket"). The pocket pages' rig keeps `centerOfRotation` fixed in a moving rig, so after the plunge a drag orbits a point 22 host units behind the pocket: 983 px drift, camera leaves the sphere (Confirmed). Fix: set centerOfRotation = −rig.translation each frame (0 px, Confirmed), or use the Probe.

**Present / pick.** Beads carry `TouchSensor DEF='PickTouch_*'`, and `touchTime` calls `flyTo` from whatever pose the user has orbited to.

**Flywheel (scriptless, open-ended: the tour ends on it).** `TimeSensor DEF='FlywheelClock' cycleInterval='120' loop='true'` → `OrientationInterpolator` (5 keys, 0 to 2π about Y) → `Transform DEF='FlywheelRig'` holding `Viewpoint DEF='Flywheel'`.

**Inside's navigation.** `<NavigationInfo USE='NavFly' containerField='navigationInfo'/>` inside the Viewpoint (X3D 4.0). Binding Inside binds FLY. The transition into Inside uses the timing of the NavigationInfo bound before it (1.6 s), not its own (2.4 s) (Confirmed).

## Chaining a tour

Tour: Host → plunge to Inside → Colossus → EyeToEye → Crown → House_vienna → Present → Wide → Flywheel.
- **Vary the size:** neighbours never share a class (ELS, POV, MS, CU, LS, MS, MCU, LS).
- **No repeated framing:** the axis turns ≥ 20° or distance changes ≥ 2× (`chain_checks`; turns 17.9°–157°).
- **Hold to read:** clamp(1.5 + words/3, 4, 9) s, rounded up; measured holds meet it.
- **The user wins.** Pointerdown stops the tour or flight; the next pick flies from where the user is. `h` holds the tour.
- **Keep the grades.** Captions carry ∑ for counts, else the record's grade; estimated and computed years say so.

## Graded findings

- **Confirmed** (headless X_ITE 16.5.1, drive_camera.js):
  - All seven Probe flights in the tour land within 0.001 units and 0.001°.
  - No speed spike measured on the frame clock. Peak/mean speed ≤ 3.4 (linear), ≤ 5.3 (angular).
  - The first step is 0% of the path.
- **Confirmed:** EXAMINE after a flight into a rolled shot: 17.5° drag, 0 px pivot drift, distance kept, roll 0. A bead click afterwards fires its TouchSensor; the pick flight starts without a jump.
- **Confirmed:** native ANIMATE eases in and out over ~1.6 s.
- **Confirmed:** the Flywheel turns at 0.05236 rad/s; the radius is constant.
- **Confirmed:** IMPORTs work through a scaled Inline; Habsburg and Darwin–Wedgwood shots land exactly.
- **Confirmed** (xmllint against x3d-4.0.xsd; fork validator): all six X3D files validate with 0 errors.
- **Confirmed** (Artifact CSP copy): boots and flies; only X_ITE's own font and WebAssembly are refused, as in scene2's gate.
- **Likely:** SwiftShader frames vary (median 67–117 ms, worst 233 ms); moves are functions of the clock, so a slow frame lengthens a step without bending the path.
- **Performance** (SwiftShader, relative only): the pocket has 7,200 triangles and 3,375 line segments, and the host 640 triangles. Tour median 13–18 fps at 1527×923 across runs.
- **Likely** (contact sheets, Read): Crown, Wide, House and Flywheel compose well. EyeToEye and Present need a visible subject mark (the year point is unmarked in the stand-in geometry); an early-year CU (Habsburg 1280) lands inside the core glow, so clamp CUs outside the halo.
- **Suspected:** a phone needs lower `multisampling` and the pocket pages' fps quality step (untested).
