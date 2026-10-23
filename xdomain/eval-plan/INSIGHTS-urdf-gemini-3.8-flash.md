# Insights: urdf x gemini-3.8-flash

60 first tries (20 prompts). Arms present: A0, A0+det, A1, A1+det, A2, A2-final, A3-final, A4-final.

## Cost, latency, tokens
- 133 model calls, estimated $1.93 (prices assumed in vertex.py), 128,397 tokens in, 489,830 out (thinking included by vertex.py).
- latency per call: median 167.7s, p90 582.5s, max 1214.4s (shared quota; 429 back-offs are not in these numbers).
- finish reasons: {'STOP': 124, 'MAX_TOKENS': 9}

## Validity by arm (strict gate)
| arm | all | tier A | tier B | tier C |
|---|---|---|---|---|
| A0 | 57/60 = 95% | 18/18 = 100% | 18/18 = 100% | 21/24 = 88% |
| A1 | 60/60 = 100% | 18/18 = 100% | 18/18 = 100% | 24/24 = 100% |
| A0+det | 57/60 = 95% | 18/18 = 100% | 18/18 = 100% | 21/24 = 88% |
| A1+det | 60/60 = 100% | 18/18 = 100% | 18/18 = 100% | 24/24 = 100% |
| A2-final | 60/60 = 100% | 18/18 = 100% | 18/18 = 100% | 24/24 = 100% |
| A4-final | 60/60 = 100% | 18/18 = 100% | 18/18 = 100% | 24/24 = 100% |
| A3-final | 58/60 = 97% | 18/18 = 100% | 18/18 = 100% | 22/24 = 92% |

## What fails first (3 invalid zero-shot answers)
| rule | answers | share of failures |
|---|---|---|
| U-00 | 3 | 100% |

## Report loop: rounds to valid (A2, from the zero-shot answer)
| rounds used | documents |
|---|---|
| 0 | 57 |
| 1 | 3 |

Round-by-round conversion of the documents still invalid: round 1: 3/3 = 100%

## Rules that survive two or more rounds
none

## Valid is not complete (mechanical expectation: counts of parts)
- A0: 50/57 = 88% of valid documents meet the expectation
- A1: 55/60 = 92% of valid documents meet the expectation
- A0+det: 50/57 = 88% of valid documents meet the expectation
- A2-final: 53/60 = 88% of valid documents meet the expectation
- A4-final: 53/60 = 88% of valid documents meet the expectation
- A3-final: 51/58 = 88% of valid documents meet the expectation
- documents whose zero-shot answer met the expectation but whose repaired answer no longer does: 0 []

## Worked examples (report loop)
### U-C4 sample 0: a hexapod with six legs of three revolute joints each
- **zero-shot answer**: valid=False, errors=1, warnings=0, 14936 chars
  - [error] U-00 line 1: not well-formed XML: Start tag expected, '<' not found, line 1, column 1
- **after report 1**: valid=True, errors=0, warnings=12, 16244 chars, 40 changed lines
  - [warning] U-16 line 90: joint 'lf_joint_femur' attaches lf_femur at (0.05, 0, 0), outside parent 'lf_coxa' geometry (radius 0.015, z -0.025 to 0.025): the part floa
  - [warning] U-16 line 119: joint 'lf_joint_tibia' attaches lf_tibia at (0.08, 0, 0), outside parent 'lf_femur' geometry (radius 0.012, z -0.04 to 0.04): the part float
  - [warning] U-16 line 178: joint 'lm_joint_femur' attaches lm_femur at (0.05, 0, 0), outside parent 'lm_coxa' geometry (radius 0.015, z -0.025 to 0.025): the part floa
  - [warning] U-16 line 207: joint 'lm_joint_tibia' attaches lm_tibia at (0.08, 0, 0), outside parent 'lm_femur' geometry (radius 0.012, z -0.04 to 0.04): the part float
### U-C4 sample 1: a hexapod with six legs of three revolute joints each
- **zero-shot answer**: valid=False, errors=1, warnings=0, 15724 chars
  - [error] U-00 line 1: not well-formed XML: Start tag expected, '<' not found, line 1, column 1
- **after report 1**: valid=True, errors=0, warnings=12, 16475 chars, 34 changed lines
  - [warning] U-16 line 70: joint 'lf_c2_joint' attaches lf_femur_link at (0.05, 0, 0), outside parent 'lf_coxa_link' geometry (radius 0.015, z -0.025 to 0.025): the pa
  - [warning] U-16 line 99: joint 'lf_c3_joint' attaches lf_tibia_link at (0.08, 0, 0), outside parent 'lf_femur_link' geometry (radius 0.012, z -0.04 to 0.04): the par
  - [warning] U-16 line 158: joint 'lm_c2_joint' attaches lm_femur_link at (0.05, 0, 0), outside parent 'lm_coxa_link' geometry (radius 0.015, z -0.025 to 0.025): the pa
  - [warning] U-16 line 187: joint 'lm_c3_joint' attaches lm_tibia_link at (0.08, 0, 0), outside parent 'lm_femur_link' geometry (radius 0.012, z -0.04 to 0.04): the par
### U-C4 sample 2: a hexapod with six legs of three revolute joints each
- **zero-shot answer**: valid=False, errors=1, warnings=0, 15757 chars
  - [error] U-00 line 1: not well-formed XML: Start tag expected, '<' not found, line 1, column 1
- **after report 1**: valid=True, errors=0, warnings=12, 16083 chars, 17 changed lines
  - [warning] U-16 line 68: joint 'lf_femur_joint' attaches lf_femur at (0.04, 0, 0), outside parent 'lf_coxa' geometry (radius 0.015, z -0.02 to 0.02): the part floats
  - [warning] U-16 line 96: joint 'lf_tibia_joint' attaches lf_tibia at (0.08, 0, 0), outside parent 'lf_femur' geometry (radius 0.012, z -0.04 to 0.04): the part float
  - [warning] U-16 line 153: joint 'lm_femur_joint' attaches lm_femur at (0.04, 0, 0), outside parent 'lm_coxa' geometry (radius 0.015, z -0.02 to 0.02): the part floats
  - [warning] U-16 line 181: joint 'lm_tibia_joint' attaches lm_tibia at (0.08, 0, 0), outside parent 'lm_femur' geometry (radius 0.012, z -0.04 to 0.04): the part float

## Reading these numbers
- Gate = errors only after the strict policy; completeness is a floor (counts), not fidelity.
- Rates are for this model and these prompts; see PLAN.md threats.