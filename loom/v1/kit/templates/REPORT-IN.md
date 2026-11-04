# Report-in brief for an agent working elsewhere

Paste to any agent whose work should join the Loom. Fill the bracket. From the definition doc's "Brief for the agent still out" [DEF]; item 9 is new in v1.

```
You are working for HagopJay on [the task you gave it]. Before you continue, report in, in this exact
shape, so your work can join the Loom (how this X3D family makes 3D worlds an AI can be held accountable to).

1. ASK: your task in one sentence, in my words if you have them.
2. STATE: done / in progress / blocked, and the last thing you finished.
3. WHERE: every repo, branch and commit (short sha) you wrote to, and every file you produced outside a
   repo, with its path and sha256.
4. NUMBERS: each result with its unit, the instrument behind it (validator commit, X_ITE version, browser,
   renderer, hardware) and a grade: C = a tool ran and showed it; L = read or reasoned, not run;
   S = suspected or written by a model. Label synthetic fixtures. Never quote software-GL frame rates.
5. WITNESSES: which ran on your outputs, with status (pass/fail/error/not_run/not_applicable/deferred):
   Grammar, Meaning, Traps, Behaviour, Eyes, Host, Receipts, Truth, Budget, and any domain witness.
6. LESSONS: any trap you hit that a validator passed, with a minimal reproducer path. These become rules.
7. SPEND: model calls made, cached or not, and any cloud resource you started.
8. OPEN: what is unfinished, what you need from me, and anything that would need my "send".
9. FOLD-BACK: if you have a lesson, an additions-only patch under tools/<name>/ with a smoke test that
   carries the failing case, and its sha256.

Rules while you finish: no model or vendor names, cloud project ids, identities, costs or private links
in anything public; nothing goes to outside repos or the Web3D Consortium without my "send"; never
overwrite a demo, add a version; at most 3 agents at once; ask before any new paid resource or download.
```
