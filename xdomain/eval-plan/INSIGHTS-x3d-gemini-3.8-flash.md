# Insights: x3d x gemini-3.8-flash

60 first tries (20 prompts). Arms present: A0, A0+det, A1, A1+det, A2, A2-final, A3-final, A4-final.

## Cost, latency, tokens
- 176 model calls, estimated $1.46 (prices assumed in vertex.py), 54,327 tokens in, 379,110 out (thinking included by vertex.py).
- latency per call: median 102.8s, p90 519.4s, max 1457.8s (shared quota; 429 back-offs are not in these numbers).
- finish reasons: {'STOP': 174, 'MAX_TOKENS': 2}

## Validity by arm (strict gate)
| arm | all | tier A | tier B | tier C |
|---|---|---|---|---|
| A0 | 46/60 = 77% | 18/18 = 100% | 14/21 = 67% | 14/21 = 67% |
| A1 | 58/60 = 97% | 18/18 = 100% | 20/21 = 95% | 20/21 = 95% |
| A0+det | 46/60 = 77% | 18/18 = 100% | 14/21 = 67% | 14/21 = 67% |
| A1+det | 58/60 = 97% | 18/18 = 100% | 20/21 = 95% | 20/21 = 95% |
| A2-final | 60/60 = 100% | 18/18 = 100% | 21/21 = 100% | 21/21 = 100% |
| A4-final | 60/60 = 100% | 18/18 = 100% | 21/21 = 100% | 21/21 = 100% |
| A3-final | 57/60 = 95% | 18/18 = 100% | 20/21 = 95% | 19/21 = 90% |

## What fails first (14 invalid zero-shot answers)
| rule | answers | share of failures |
|---|---|---|
| XSD | 14 | 100% |

## Report loop: rounds to valid (A2, from the zero-shot answer)
| rounds used | documents |
|---|---|
| 0 | 46 |
| 1 | 14 |

Round-by-round conversion of the documents still invalid: round 1: 14/14 = 100%

## Rules that survive two or more rounds
none

## Valid is not complete (mechanical expectation: counts of parts)
- A0: 46/46 = 100% of valid documents meet the expectation
- A1: 58/58 = 100% of valid documents meet the expectation
- A0+det: 46/46 = 100% of valid documents meet the expectation
- A2-final: 60/60 = 100% of valid documents meet the expectation
- A4-final: 60/60 = 100% of valid documents meet the expectation
- A3-final: 57/57 = 100% of valid documents meet the expectation
- documents whose zero-shot answer met the expectation but whose repaired answer no longer does: 0 []

## Worked examples (report loop)
### X-B3 sample 1: a simple house with walls and a roof
- **zero-shot answer**: valid=False, errors=7, warnings=0, 3148 chars
  - [error] XSD Line 19: Line 19: Element 'Material', attribute 'roughness': The attribute 'roughness' is not allowed.
  - [error] XSD Line 29: Line 29: Element 'Material', attribute 'roughness': The attribute 'roughness' is not allowed.
  - [error] XSD Line 39: Line 39: Element 'Material', attribute 'roughness': The attribute 'roughness' is not allowed.
  - [error] XSD Line 58: Line 58: Element 'Material', attribute 'roughness': The attribute 'roughness' is not allowed.
- **after report 1**: valid=True, errors=0, warnings=0, 3078 chars, 14 changed lines
### X-B4 sample 0: a traffic light with a housing and three lamps
- **zero-shot answer**: valid=False, errors=7, warnings=0, 3229 chars
  - [error] XSD Line 16: Line 16: Element 'Material', attribute 'metalness': The attribute 'metalness' is not allowed.
  - [error] XSD Line 16: Line 16: Element 'Material', attribute 'roughness': The attribute 'roughness' is not allowed.
  - [error] XSD Line 26: Line 26: Element 'Material', attribute 'roughness': The attribute 'roughness' is not allowed.
  - [error] XSD Line 36: Line 36: Element 'Material', attribute 'roughness': The attribute 'roughness' is not allowed.
- **after report 1**: valid=True, errors=0, warnings=0, 3253 chars, 12 changed lines
### X-B4 sample 2: a traffic light with a housing and three lamps
- **zero-shot answer**: valid=False, errors=4, warnings=0, 3921 chars
  - [error] XSD Line 22: Line 22: Element 'Material', attribute 'roughness': The attribute 'roughness' is not allowed.
  - [error] XSD Line 32: Line 32: Element 'Material', attribute 'roughness': The attribute 'roughness' is not allowed.
  - [error] XSD Line 102: Line 102: Element 'Material', attribute 'metalness': The attribute 'metalness' is not allowed.
  - [error] XSD Line 102: Line 102: Element 'Material', attribute 'roughness': The attribute 'roughness' is not allowed.
- **after report 1**: valid=True, errors=0, warnings=0, 3933 chars, 6 changed lines

## Reading these numbers
- Gate = errors only after the strict policy; completeness is a floor (counts), not fidelity.
- Rates are for this model and these prompts; see PLAN.md threats.