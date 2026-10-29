# The picture judge on the bird (plan step 11)

A vision model looks at stills of the live page next to two of the owner's own stills and scores them. The point was to turn "does it look right" into numbers that move when the scene changes, and to have the judge's own suggestions drive edits. This file says what was measured and what was not; the short version is that the judge **could not tell the edits made from its advice from no edits at all**, and that its loudest complaint (too dense) is also what the owner loves about the bird.

## Method

- **Stills.** 12 views of the page (the tour's shot list: establishing, face, push-in, three orbits, underside, tenders, heart, fan, feather, wing), 1527 x 923, `?ui=none&seed=0`, X_ITE 16.5.1 unpatched, full Chromium on SwiftShader software GL. A still is taken only after the camera sensor reports the target pose, then after a settle wait, and a frame that comes out near-black is retaken (`test/frames.js` has the same wait for the documentation frames).
- **Judge.** Two reference stills (the owner's) plus one candidate, in one request. Scores 1 to 10 for look match, beauty, clarity and polish, then one concrete change that would most improve the frame and one thing to keep. Three votes per still (two from a smaller model, one from a larger one), temperature 0.8, so 36 votes per round.
- **Score.** The mean of the four criteria, per vote; a still's score is the mean of its votes; an arm's score is the mean over the 12 stills.

## What was compared

| Arm | Scene |
|---|---|
| A | the scene without the two scene edits below |
| B | with the two scene edits that answer the first round's complaints: glowing nodes on the near feathers (the references put a node on every vertex) and the ontology beads pulled toward gold (the full rainbow read as clutter next to the gold references). The tour's Heart shot was also moved inside the shell (shell beads in front of the lens read as clutter), but that move is in the camera poses of all three arms, so the arms do not test it |
| C | B plus a variant of the knowledge graph with its colours pulled 70 percent toward gold (`?look=gold`) |

## Results

| Round | Scene | Mean score | Note |
|---|---|---|---|
| 1 | A | 3.56 | first capture |
| 2 | B | 3.36 | capture flaw: an all-black face still (11.6 KB, scored 2.33), so this round is not used |
| 2, judged again | the same 12 stills as round 2 | 3.45 | **the judge's own noise**: same images, +0.09 on the mean, 0.21 standard deviation per still |
| 2, gold | C | 3.59 | this capture was fine; compared with the flawed round 2 it made the gold graph look better than it was (an early reading, corrected before it was reported) |
| **A** | A, clean capture | **3.67** | 34 of 36 calls landed (two upstream 502s) |
| **B** | B | **3.56** | 36 of 36 |
| **C** | C | **3.43** | 35 of 36 |

Only the last three rows share a capture method, so only they are compared. Paired by still (12 pairs):

| Difference | Mean | Standard error | Stills up / down | Sign test |
|---|---|---|---|---|
| B minus A | -0.11 | 0.11 | 4 / 4 (4 equal) | p = 1 |
| C minus A | -0.24 | 0.11 | 1 / 11 | p about 0.006 |
| C minus B | -0.13 | 0.04 | 1 / 10 | p about 0.012 |

Reading, with grades:

- **The two scene edits made from the judge's advice (B against A) are not detectable.** The difference is about one standard error, and the judge repeating itself on identical images moves the mean by as much. **Confirmed** as a null result at this size; a small real effect is not ruled out.
- **The gold-tinted graph scored slightly lower** (-0.13 against B, ten of eleven stills down). **Likely** real and small. It does not show the gold graph looks worse to the owner.
- **Noise.** The pooled spread of the three votes on one still is about 0.9 on the 1 to 10 scale, almost all of it the fixed gap between the two models, which cancels when arms are compared; the larger model scores about 1.5 to 2 points lower than the smaller one throughout. The same 12 images judged twice moved the mean by 0.09 (standard error 0.06), and the paired differences between arms have a standard error of 0.11, so a difference smaller than about 0.2 (two standard errors) cannot be told from zero. The edits so far were smaller than that.
- **What the judge keeps asking for.** In about 72 of the 105 votes in arms A to C the top fix is to thin the scene out (fewer or sparser lines and nodes, less clutter); a looser keyword count (reduce, simplify, density, clutter, sparse) gives 83, which includes 11 votes that only ask for less bloom on the feather and wing stills. What it asks to keep is the facets (74 votes), the gold (44), the low-poly look (35) and the head (31). The dense knowledge-graph constellation is what the bird is, and the owner has said he loves it, so this is a **disagreement between the judge and the owner**, and the owner's eye is the judge of record.

## What it was good for

- It named three problems whose cheap fixes are listed above, and it exposed a capture problem: a black frame still gets a score (the all-black face still got 2.33), so a judge score is not a check that the picture exists. The capture now waits for the pose and retakes dark frames.

## What to try next (not done)

An arm D that **thins the graph on purpose** (fewer edges, drawn from the same data) is the one edit the judge's advice points at that is large enough to exceed its noise. It is also an edit the owner may not want, so it would be an experiment judged by his eye first, the model second. Another option is a bigger panel (more votes per still) before any further edit is judged.

## Files

The judge client and the round data live outside this folder (they name the model service, which is kept off the public repo); the stills, the votes and a contact sheet are in the thread's private files.
