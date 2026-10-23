# Insights: gltf x gemini-3.8-flash

60 first tries (20 prompts). Arms present: A0, A0+det, A1, A1+det, A2, A2-final, A3-final, A4-final.

## Cost, latency, tokens
- 352 model calls, estimated $17.04 (prices assumed in vertex.py), 240,481 tokens in, 4,494,999 out (thinking included by vertex.py).
- latency per call: median 66.7s, p90 178.5s, max 437.2s (shared quota; 429 back-offs are not in these numbers).
- finish reasons: {'STOP': 345, 'MAX_TOKENS': 7}

## Validity by arm (strict gate)
| arm | all | tier A | tier B | tier C |
|---|---|---|---|---|
| A0 | 24/60 = 40% | 15/18 = 83% | 4/18 = 22% | 5/24 = 21% |
| A1 | 46/60 = 77% | 18/18 = 100% | 16/18 = 89% | 12/24 = 50% |
| A0+det | 32/60 = 53% | 18/18 = 100% | 7/18 = 39% | 7/24 = 29% |
| A1+det | 47/60 = 78% | 18/18 = 100% | 16/18 = 89% | 13/24 = 54% |
| A2-final | 49/60 = 82% | 18/18 = 100% | 14/18 = 78% | 17/24 = 71% |
| A4-final | 50/60 = 83% | 18/18 = 100% | 15/18 = 83% | 17/24 = 71% |
| A3-final | 40/60 = 67% | 16/18 = 89% | 10/18 = 56% | 14/24 = 58% |

## What fails first (36 invalid zero-shot answers)
| rule | answers | share of failures |
|---|---|---|
| ACCESSOR_MAX_MISMATCH | 27 | 75% |
| ACCESSOR_ELEMENT_OUT_OF_MAX_BOUND | 15 | 42% |
| ACCESSOR_INDEX_OOB | 11 | 31% |
| ACCESSOR_MIN_MISMATCH | 8 | 22% |
| BUFFER_BYTE_LENGTH_MISMATCH | 7 | 19% |
| ACCESSOR_ANIMATION_INPUT_NON_INCREASING | 5 | 14% |
| INVALID_URI | 4 | 11% |
| ACCESSOR_ELEMENT_OUT_OF_MIN_BOUND | 4 | 11% |
| ACCESSOR_ANIMATION_SAMPLER_OUTPUT_NON_NORMALIZED_QUATERNION | 3 | 8% |
| ACCESSOR_VECTOR3_NON_UNIT | 2 | 6% |
| MESH_PRIMITIVE_ACCESSOR_WITHOUT_BYTESTRIDE | 2 | 6% |
| INVALID_JSON | 2 | 6% |

## Report loop: rounds to valid (A2, from the zero-shot answer)
| rounds used | documents |
|---|---|
| 0 | 24 |
| 1 | 10 |
| 2 | 6 |
| 3 | 9 |
| never | 11 |

Round-by-round conversion of the documents still invalid: round 1: 10/36 = 28%; round 2: 6/26 = 23%; round 3: 9/20 = 45%

## Rules that survive two or more rounds
ACCESSOR_MAX_MISMATCH (15), INVALID_URI (12), ACCESSOR_ELEMENT_OUT_OF_MAX_BOUND (9), BUFFER_BYTE_LENGTH_MISMATCH (4), ACCESSOR_MIN_MISMATCH (4), ACCESSOR_INDEX_OOB (3), ACCESSOR_ELEMENT_OUT_OF_MIN_BOUND (3), ACCESSOR_INVALID_FLOAT (2)

## Valid is not complete (mechanical expectation: counts of parts)
- A0: 24/24 = 100% of valid documents meet the expectation
- A1: 46/46 = 100% of valid documents meet the expectation
- A0+det: 32/32 = 100% of valid documents meet the expectation
- A2-final: 49/49 = 100% of valid documents meet the expectation
- A4-final: 50/50 = 100% of valid documents meet the expectation
- A3-final: 40/40 = 100% of valid documents meet the expectation
- documents whose zero-shot answer met the expectation but whose repaired answer no longer does: 0 []

## Worked examples (report loop)
### G-A4 sample 1: a scene with an orthographic camera and a node with a non-uniform scale of 1, 2, 3
- **zero-shot answer**: valid=False, errors=1, warnings=0, 1272 chars
  - [error] ACCESSOR_MAX_MISMATCH /accessors/0/max/1: Declared maximum value for this component (1) does not match actual maximum (5.831554006032442e-39).
- **after report 1**: valid=False, errors=1, warnings=0, 1268 chars, 2 changed lines
  - [error] BUFFER_BYTE_LENGTH_MISMATCH /buffers/0: Actual data byte length (33) is less than the declared buffer byte length (36).
- **after report 2**: valid=True, errors=0, warnings=0, 1272 chars, 2 changed lines
### G-A4 sample 2: a scene with an orthographic camera and a node with a non-uniform scale of 1, 2, 3
- **zero-shot answer**: valid=False, errors=1, warnings=0, 1346 chars
  - [error] ACCESSOR_MAX_MISMATCH /accessors/0/max/1: Declared maximum value for this component (1) does not match actual maximum (5.831554006032442e-39).
- **after report 1**: valid=False, errors=1, warnings=0, 1342 chars, 2 changed lines
  - [error] BUFFER_BYTE_LENGTH_MISMATCH /buffers/0: Actual data byte length (33) is less than the declared buffer byte length (36).
- **after report 2**: valid=True, errors=0, warnings=0, 1346 chars, 2 changed lines
### G-A6 sample 1: a node using a 4x4 column-major matrix that translates by (2, 0, 0)
- **zero-shot answer**: valid=False, errors=1, warnings=0, 1009 chars
  - [error] ACCESSOR_MAX_MISMATCH /accessors/0/max/0: Declared maximum value for this component (1) does not match actual maximum (0.500030517578125).
- **after report 1**: valid=True, errors=0, warnings=0, 1009 chars, 2 changed lines

## Reading these numbers
- Gate = errors only after the strict policy; completeness is a floor (counts), not fidelity.
- Rates are for this model and these prompts; see PLAN.md threats.