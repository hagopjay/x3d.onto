# LOOM HANDOFF (POST): paste as the done-when

Paste under PRE in the same first message. The agent fills it at the end; a missing item means the work is not done. Based on the 1 Nov kickoff doc's POST [KICK]; item 9 is new in v1.

```
LOOM HANDOFF (POST). Fill every item before you say "done". A missing item means not done.

1. RECEIPTS: one Loom Receipt v1 (loom.receipt/1) per artifact: subject; candidate sha256; profile;
   tools with versions and commits; outputs with bytes and sha256; each required witness record's hash;
   the not-run witnesses with reasons; model calls by prompt hash with a cached flag; budget;
   limitations; prev (the receipt it replaces). Run `loom verify-receipt` on each.
2. WITNESS TABLE: witness | tool and version | status (pass/fail/error/not_run/not_applicable/deferred)
   | grade | evidence path | what a pass does not establish. Red rows stay red, with reason and fix plan.
3. NUMBERS: every number names its witness, commit and renderer, and carries C/L/S. Model judgements are
   S. Synthetic fixtures are labelled synthetic. No software-GL frame rates presented as performance.
4. FRAMES: <N> stills at fixed times from the headless render, one run under the host-policy copy, a
   contact sheet, before and after frames for every visual change; each frame's sha256 in the record.
5. LESSONS: each new trap as a FACTS entry (symptom, cause, fix, test, scope, reproducer path); a proposed
   gate rule with one passing and one failing fixture; whether it belongs upstream (held until "send").
6. SPEND: the ledger lines and the total against the cap.
7. VERSIONS: what is new against v<N>, where v<N> still lives, links to both.
8. NEXT: open questions, one line each, and the one step you recommend.
9. FOLD-BACK: the additions-only patch (tools/<name>/, README, smoke.py with its negative controls), its
   sha256, and the output of `loom foldback` on it (clean apply; smoke green under python and python -O).
```
