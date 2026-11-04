# Loom v1

The X3D Loom, consolidated: one definition, its sources, what the other model's patches taught, and a small kit that runs. Built 3 November 2026 from the Drive folder, the project zips and their PR patches, and the notes on this Mac. Local git repository; no remote.

| File | What it is |
|---|---|
| [LOOM-v1.md](LOOM-v1.md) | **The definition.** Purpose, roles, 20 laws, the ten-step loop, artefacts, gates and thresholds, measurements with grades, 45 failure modes, roadmap, open questions, decisions |
| [SOURCES.md](SOURCES.md) | Every input, what it gave, how it was read, and the 14 places sources disagree, each with its resolution |
| [LEARNINGS-from-patches.md](LEARNINGS-from-patches.md) | The seven patches and the Loomsong v1 → v4 history, turned into 25 reusable rules |
| [GLOSSARY.md](GLOSSARY.md) | The words |
| [kit/](kit/) | `loomkit` (Python standard library), profiles, templates, examples, tests |
| [runs/](runs/) | This repo's own evidence: Data City through the kit, the fold-back survey, the traps corpus run |

## Use it on a project

1. Paste [kit/templates/KICKOFF-PRE.md](kit/templates/KICKOFF-PRE.md) and [HANDOFF-POST.md](kit/templates/HANDOFF-POST.md) as the first message, with `LOOM-v1.md` attached.
2. Run the witnesses into a run folder outside the project, then accept and write a receipt:

```bash
kit/loom grammar  PROJECT --evidence RUN/evidence --files 'path/*.x3d'
```
```bash
kit/loom traps    PROJECT --evidence RUN/evidence --files 'path/*.x3d' --host strict
```
```bash
kit/loom command  PROJECT --evidence RUN/evidence --name truth -- python3 -m your.gate args
```
```bash
kit/loom foldback PROJECT --evidence RUN/evidence --patch PROJECT/integration/your.patch
```
```bash
kit/loom record   PROJECT --evidence RUN/evidence --name eyes --status not_run --reason "why"
```
```bash
kit/loom accept   PROJECT --evidence RUN/evidence --profile kit/profiles/x3d-static.json
```
```bash
kit/loom receipt  PROJECT --evidence RUN/evidence --profile kit/profiles/x3d-static.json --subject "name" --out RUN/receipt.json
```

Exit codes: 0 passed, 1 contract violation (a stable code is printed), 2 instrument or input error. Set `LOOM_PYFLAGS=-O` to run everything optimised; the gates still hold. Grammar and Meaning use the x3d_mcp fork at `~/Projects/x3d/x3d_mcp`, or `--fork` / `LOOM_FORK` to point elsewhere.

## Publishing (law 16)

`kit/loom sweep . DEST --rules kit/profiles/public-sweep.json` writes a public copy: model and vendor names become neutral labels, costs and Drive ids are withheld, and the copy fails if any forbidden pattern survives (`SWEEP-REPORT.json`). The rules file stays private, since it lists the names it removes.

## Check that the kit works

```bash
python3 -I kit/tests/test_gates.py
```
```bash
kit/examples/run_data_city.sh
```
```bash
python3 -I kit/examples/check_all_foldbacks.py
```

The first runs 29 negative controls and 11 two-sided trap rules under normal Python and `-O`. The second takes the delivered Data City Loom (copied, never edited), accepts it under `x3d-static/v1`, writes a receipt, then shows that a post-witness edit and a planted trap are both rejected. The third applies every PR patch from the project zips in an empty repo and runs its smoke test both ways.

## Where it stands (3 Nov)

- Kit: tested (C). Data City: accepted under the static profile; its browser witnesses are visibly not run. Fold-backs: 4 of 5 pass; the IFC one fails its own positive control on this Mac (platform-dependent triangulation). Both loose patches reproduce their newer versions (projects agent).
- Not done here: browser witnesses, real-GPU anything, running the rules on x3d.onto's corpus, promoting any fold-back into its target repo. These wait on your word or on the projects agent. See LOOM-v1.md §10.
