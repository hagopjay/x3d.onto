# Portraits

AI-made portraits of the 26 tier-1 people in Dynasty Loom: the founders and the tour's subjects in the three families. Every one of them died long ago, and the generator refuses anyone without a recorded death year. Every image is AI-made. The page shows that on every portrait: the label in `manifest.json` is drawn beside the picture.

This folder is the permanent cache. The generator is cache-first, so it never asks for the same person twice. `tools/build_v2.py --manifest dynasty-loom/portraits/manifest.json` builds the page from it with no network access and no image model.

| Path | What it is |
|---|---|
| `manifest.json` | what the scene reads: per person the status, version, label, file paths (relative to this folder) and review note |
| `cache/<qid>/v1/` (or `v2/`) | `portrait.png` as made, `cutout-768.webp` and `thumb-256.webp` for the page, `meta.json` with the prompt and checks |
| `cache/<qid>/source/` | the reference picture the portrait follows (`reference.jpg`) and its Commons record (`source.json`: file page, author, licence, sha256) |
| `cache/<qid>/monogram/` | the initials card used before a portrait exists |
| `people.json`, `refs.json`, `labels.json` | who is in tier 1, the hand-picked reference files, the cleaned label text |
| `requests.jsonl` | the call log and budget (28 calls of 60). It holds no keys |
| `tools/portraits.py` | the generator: `refs`, `gen`, `review`, `post`. It reads its API key from the environment and never prints or stores it |

## Sources and licences

- 24 portraits follow a public-domain painting, drawing or photograph on Wikimedia Commons. Each `source.json` records the file page, author and licence as Commons gives them.
- Rudolf I follows a photograph of his tomb effigy in Speyer Cathedral by Haselburg-müller, licensed CC BY-SA 3.0. That photograph and the portrait made from it carry CC BY-SA 3.0, and the page credits the photographer word for word.
- Mayer Amschel Rothschild and Albert I are imagined: no authenticated likeness survives. Their labels say so. Their `source.json` records why no reference was used.
- Mariana of Austria has two versions. v1 failed review and is kept as the record; v2 is the one shown.

## Rules the generator keeps

- Labels are not optional. A portrait without its label is never shown.
- No portraits of living or possibly living people.
- Rothschild portraits stay dignified: period dress, neutral expression, no caricature.
- A person not yet made shows one shared silhouette, never a likeness (`--placeholders`, see the v2 section of the main README).
