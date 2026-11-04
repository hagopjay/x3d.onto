"""Two-sided controls for loomkit, run under normal Python and `python -O`.

Each negative control must be rejected with its INTENDED diagnostic; any other exception counts as a
broken test, not a caught defect (Loomsong debrief section 12: IndexError is not a rejection).
A negative that passes raises SURVIVING_CONTROL. Fixtures are synthetic and labelled so.

  python3 -I kit/tests/test_gates.py          # runs both modes and writes kit/tests/last-run.json
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT))

from loomkit import accept as acc  # noqa: E402
from loomkit import picture, receipt, sweep, traps  # noqa: E402
from loomkit.core import GateError, candidate, sha256_file, write_witness  # noqa: E402

PROFILE = {"schema": "loom.profile/1", "name": "synthetic/test", "required": [
    {"witness": "grammar"}, {"witness": "traps"},
    {"witness": "behaviour", "allow": ["deferred"]},
    {"witness": "truth", "coverage": {"rows": True}}], "visible_not_run": ["eyes"]}


def expect(code: str, fn) -> dict:
    try:
        fn()
    except GateError as e:
        if e.code != code:
            raise RuntimeError(f"WRONG_DIAGNOSTIC: expected {code}, got {e.code}") from None
        return {"expected": code, "caught": e.code}
    raise RuntimeError(f"SURVIVING_CONTROL: {code}")


def fixture(td: Path) -> tuple[Path, Path, str]:
    root, ev = td / "cand", td / "evidence"
    (root / "gen").mkdir(parents=True)
    (root / "gen/build.py").write_text("print('synthetic generator')\n")
    (root / "world.x3d").write_text("<X3D version='4.0'><Scene/></X3D>\n")
    s = candidate(root)["sha256"]
    for n in ("grammar", "traps"):
        write_witness(ev, root, s, n, "pass", "C", {"tool": "synthetic"})
    write_witness(ev, root, s, "behaviour", "deferred", "L", {"tool": "synthetic"}, reason="static profile: no browser here")
    log = ev / "truth.log"; ev.mkdir(exist_ok=True); log.write_text("ok\n")
    write_witness(ev, root, s, "truth", "pass", "C", {"tool": "synthetic"}, coverage={"rows": True},
                  evidence=[{"path": "truth.log", "sha256": sha256_file(log)}])
    return root, ev, s


def edit(ev: Path, name: str, **changes) -> None:
    p = ev / f"{name}.json"; r = json.loads(p.read_text()); r.update(changes); p.write_text(json.dumps(r))


def acceptance_controls() -> list[dict]:
    rows = []
    with tempfile.TemporaryDirectory(prefix="loomkit-test-") as d:
        root, ev, s = fixture(Path(d))
        good = acc.accept(root, ev, PROFILE)
        if good["status"] != "accepted":
            raise RuntimeError("POSITIVE_CONTROL_REJECTED")
        rows.append({"case": "complete candidate", "result": "accepted"})
    cases = [
        ("missing witness", "MISSING_WITNESS", lambda r, e: (e / "traps.json").unlink()),
        ("red witness", "WITNESS_NOT_PASS", lambda r, e: edit(e, "grammar", status="fail")),
        ("instrument error", "WITNESS_NOT_PASS", lambda r, e: edit(e, "grammar", status="error")),
        ("not run", "WITNESS_NOT_PASS", lambda r, e: edit(e, "traps", status="not_run")),
        ("deferred without reason", "STATUS_NEEDS_REASON", lambda r, e: edit(e, "behaviour", reason="")),
        ("deferral not allowed", "WITNESS_NOT_PASS", lambda r, e: edit(e, "traps", status="deferred", reason="later")),
        ("stale: generator edited after witnesses", "STALE_WITNESS", lambda r, e: (r / "gen/build.py").write_text("print('changed')\n")),
        ("stale: new file added", "STALE_WITNESS", lambda r, e: (r / "extra.js").write_text("//\n")),
        ("development record", "DEVELOPMENT_WITNESS", lambda r, e: edit(e, "grammar", development=True)),
        ("pass graded S", "UNMEASURED_REQUIRED_WITNESS", lambda r, e: edit(e, "traps", grade="S")),
        ("coverage absent", "COVERAGE_REQUIRED", lambda r, e: edit(e, "truth", coverage={})),
        ("evidence edited", "EVIDENCE_DRIFT", lambda r, e: (e / "truth.log").write_text("edited\n")),
        ("wrong witness name", "WRONG_WITNESS_NAME", lambda r, e: edit(e, "grammar", witness="eyes")),
        ("malformed record", "MALFORMED_WITNESS", lambda r, e: (e / "traps.json").write_text("{not json")),
    ]
    for label, code, mutate in cases:
        with tempfile.TemporaryDirectory(prefix="loomkit-test-") as d:
            root, ev, s = fixture(Path(d))
            mutate(root, ev)
            rows.append({"case": label, **expect(code, lambda: acc.accept(root, ev, PROFILE))})
    with tempfile.TemporaryDirectory(prefix="loomkit-test-") as d:
        p = Path(d) / "empty.json"; p.write_text(json.dumps({"schema": "loom.profile/1", "name": "x", "required": []}))
        rows.append({"case": "empty profile", **expect("EMPTY_PROFILE", lambda: acc.load_profile(p))})
    with tempfile.TemporaryDirectory(prefix="loomkit-test-") as d:
        root, ev, s = fixture(Path(d))
        (root / "gen/build.py").write_text("print('changed mid-run')\n")
        rows.append({"case": "candidate changed during witness", **expect(
            "CANDIDATE_CHANGED_DURING_WITNESS", lambda: write_witness(ev, root, s, "eyes", "pass", "C", {}))})
    return rows


TRAP_CASES = {  # rule: (passing XML, failing XML). Synthetic fixtures.
    "shader-raw-source": ("<X3D version='4.0'><Scene><ShaderPart>data:x-shader/x-fragment,#version 300 es\nvoid main(){}</ShaderPart></Scene></X3D>",
                          "<X3D version='4.0'><Scene><ShaderPart>#version 300 es\nvoid main(){}</ShaderPart></Scene></X3D>"),
    "route-before-def": ("<X3D><Scene><TimeSensor DEF='T'/><Transform DEF='B'/><ROUTE fromNode='T' fromField='fraction_changed' toNode='B' toField='set_x'/></Scene></X3D>",
                         "<X3D><Scene><TimeSensor DEF='T'/><ROUTE fromNode='T' fromField='fraction_changed' toNode='B' toField='set_x'/><Transform DEF='B'/></Scene></X3D>"),
    "route-undefined": ("<X3D><Scene><TimeSensor DEF='T'/><Transform DEF='B'/><ROUTE fromNode='T' fromField='a' toNode='B' toField='b'/></Scene></X3D>",
                        "<X3D><Scene><TimeSensor DEF='T'/><ROUTE fromNode='T' fromField='a' toNode='Nope' toField='b'/></Scene></X3D>"),
    "color-range": ("<X3D><Scene><Material diffuseColor='1 0.5 0'/></Scene></X3D>",
                    "<X3D><Scene><Material diffuseColor='1.2 0.5 0'/></Scene></X3D>"),
    "color-emissive-white": ("<X3D><Scene><Material diffuseColor='0.9 0.1 0.1' emissiveColor='0.2 0 0'/></Scene></X3D>",
                             "<X3D><Scene><Material diffuseColor='0.9 0.1 0.1' emissiveColor='1 1 1'/></Scene></X3D>"),
    "splat-bbox": ("<X3D version='4.1'><Scene><GaussianSplats bboxSize='2 2 2' bboxCenter='0 0 0'/></Scene></X3D>",
                   "<X3D version='4.1'><Scene><GaussianSplats/></Scene></X3D>"),
    "movie-not-still": ("<X3D><Scene><MovieTexture url='\"clip.mp4\"'/></Scene></X3D>",
                        "<X3D><Scene><MovieTexture url='\"poster.png\"'/></Scene></X3D>"),
    "version-fits-nodes": ("<X3D version='4.1'><Scene><RenderedTexture/></Scene></X3D>",
                           "<X3D version='4.0'><Scene><RenderedTexture/></Scene></X3D>"),
    "no-script-under-host": ("<X3D><Scene><Transform/></Scene></X3D>", "<X3D><Scene><Script/></Scene></X3D>"),
    "metadata-containerfield": ("<X3D><Scene><Shape><MetadataSet containerField='metadata' name='row'/></Shape></Scene></X3D>",
                                "<X3D><Scene><Shape><MetadataSet name='row'/></Shape></Scene></X3D>"),
    "glsl-reserved-active": ("<X3D><Scene><ShaderPart>data:x-shader/x-fragment,in float sounding;void main(){}</ShaderPart></Scene></X3D>",
                             "<X3D><Scene><ShaderPart>data:x-shader/x-fragment,in float active;void main(){}</ShaderPart></Scene></X3D>"),
}


def trap_controls() -> list[dict]:
    if set(TRAP_CASES) != set(traps.RULES):
        raise RuntimeError("TRAP_RULE_WITHOUT_TWO_SIDED_TEST: " + str(set(traps.RULES) ^ set(TRAP_CASES)))
    rows = []
    for rule, (good, bad) in TRAP_CASES.items():
        prof = {"host": "strict"}
        g = [h.rule for h in traps.check(good.encode(), prof)]
        b = [h.rule for h in traps.check(bad.encode(), prof)]
        if rule in g:
            raise RuntimeError(f"FALSE_POSITIVE: {rule}")
        if rule not in b:
            raise RuntimeError(f"SURVIVING_CONTROL: {rule}")
        rows.append({"rule": rule, "passing_fixture": "clean", "failing_fixture": "caught"})
    return rows


def picture_controls() -> list[dict]:
    s, frames = "a" * 64, {"shot-01": "b" * 64, "shot-02": "c" * 64}
    good = {"schema": "loom.picture-review/1", "subject_sha256": s, "reviewer": "synthetic fixture", "state": "suspected",
            "images": dict(frames), "flags": [{"id": "f1", "view": "shot-01", "region": [0.1, 0.1, 0.6, 0.5],
                                               "concern": "Collar floats above the left post; seat it.", "state": "suspected"}],
            "scope": "protocol test only"}
    picture.validate(good, s, frames)
    rows = [{"case": "located suspected flag", "result": "accepted"}]
    muts = [("score field", "PICTURE_FIELDS", lambda r: r.update(score=9)),
            ("score in prose", "PICTURE_GRADING", lambda r: r.update(scope="overall 7/10")),
            ("confirmed state", "MODEL_TRUTH_PROMOTION", lambda r: r.update(state="confirmed")),
            ("flag promoted", "MODEL_TRUTH_PROMOTION", lambda r: r["flags"][0].update(state="confirmed")),
            ("stale review", "STALE_PICTURE_REVIEW", lambda r: r.update(subject_sha256="d" * 64)),
            ("missing view", "PICTURE_COVERAGE", lambda r: r["images"].pop("shot-02")),
            ("wrong image", "PICTURE_IMAGE_BINDING", lambda r: r["images"].update({"shot-01": "e" * 64})),
            ("bad region", "PICTURE_REGION", lambda r: r["flags"][0].update(region=[0.9, 0.1, 0.2, 0.5])),
            ("vague concern", "PICTURE_CONCERN", lambda r: r["flags"][0].update(concern="bad")),
            ("duplicate flag", "PICTURE_DUPLICATE", lambda r: r["flags"].append(dict(r["flags"][0])))]
    for label, code, m in muts:
        r = copy.deepcopy(good); m(r)
        rows.append({"case": label, **expect(code, lambda: picture.validate(r, s, frames))})
    return rows


def receipt_controls() -> list[dict]:
    rows = []
    with tempfile.TemporaryDirectory(prefix="loomkit-test-") as d:
        root, ev, s = fixture(Path(d))
        result = acc.accept(root, ev, PROFILE)
        r = receipt.build("synthetic", result, candidate(root)["files"], [root / "world.x3d"], {}, {}, [], [], {}, None, [])
        dest = Path(d) / "receipts/synthetic.json"
        receipt.write(r, dest)
        receipt.verify(dest)
        rows.append({"case": "write and verify", "result": "intact"})
        rows.append({"case": "overwrite refused", **expect("RECEIPT_EXISTS", lambda: receipt.write(r, dest))})
        t = json.loads(dest.read_text()); t["grade"] = "S"; dest.write_text(json.dumps(t))
        rows.append({"case": "edited receipt", **expect("RECEIPT_DRIFT", lambda: receipt.verify(dest))})
    return rows


def sweep_controls() -> list[dict]:
    # Leak words are assembled from fragments so this file itself passes the sweep, and the rule set is
    # inline so the public copy (which omits kit/profiles/public-sweep.json) can still run this test.
    vendor, host, cost, other, home = "Gem" + "ini", "claude" + ".ai", "$" + "36.16", "Open" + "AI", "/Us" + "ers/"
    rules = {"schema": "loom.sweep-rules/1",
             "replace": [{"pattern": vendor, "with": "a hosted model"}, {"pattern": host.replace(".", "\\."), "with": "the hosting app"},
                         {"pattern": r"(?<![\w\"])\$\d[\d,]*(?:\.\d+)?", "with": "[cost withheld]"}],
             "forbid": [vendor, other, host.replace(".", "\\."), home + "[A-Za-z0-9_-]+", r"(?<![\w\"'])\$\d[\d,]*\.\d{2}"]}
    rows = []
    with tempfile.TemporaryDirectory(prefix="loomkit-test-") as d:
        src, dst = Path(d) / "src", Path(d) / "dst"; src.mkdir()
        (src / "a.md").write_text(f"Judged by {vendor} judge for {cost}; see {host}; run.sh uses \"$0\".\n")
        rep = sweep.sweep(src, dst, rules, set())
        out = (dst / "a.md").read_text()
        if rep["status"] != "pass" or vendor in out or cost in out or '"$0"' not in out:
            raise RuntimeError("SWEEP_POSITIVE_FAILED: " + out)
        rows.append({"case": "vendor, cost and host removed; shell positional argument kept", "result": "clean"})
        (src / "b.md").write_text("Also tried " + other + " and " + home + "someone/x.\n")
        rep = sweep.sweep(src, dst, rules, set())
        if rep["status"] != "fail" or len(rep["residue"]) != 2:
            raise RuntimeError("SURVIVING_CONTROL: LEAK_RESIDUE")
        rows.append({"case": "uncovered leak reported as residue", "expected": "LEAK_RESIDUE", "caught": "LEAK_RESIDUE"})
    return rows


def run_all() -> dict:
    return {"acceptance": acceptance_controls(), "traps": trap_controls(),
            "picture": picture_controls(), "receipt": receipt_controls(), "sweep": sweep_controls(), "optimized": bool(sys.flags.optimize)}


if __name__ == "__main__":
    if "--child" in sys.argv:
        print(json.dumps(run_all()))
        sys.exit(0)
    report = {"schema": "loomkit.self-test/1", "scope": "Synthetic fixtures exercising the real predicates; not a project run.", "modes": []}
    for flags in ([], ["-O"]):
        p = subprocess.run([sys.executable, "-I", *flags, __file__, "--child"], capture_output=True, text=True)
        if p.returncode != 0:
            print(p.stdout, p.stderr, file=sys.stderr)
            sys.exit(1)
        res = json.loads(p.stdout)
        negatives = sum(1 for k in ("acceptance", "picture", "receipt", "sweep") for row in res[k] if "caught" in row)
        report["modes"].append({"optimized": res["optimized"], "negative_controls_caught": negatives,
                                "trap_rules_two_sided": len(res["traps"]), "detail": res})
    out = KIT / "tests/last-run.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    for m in report["modes"]:
        print(f"optimized={m['optimized']}: {m['negative_controls_caught']} negative controls caught with the intended code; "
              f"{m['trap_rules_two_sided']} trap rules pass their clean fixture and catch their failing one")
