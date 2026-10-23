# Results so far (interim; glTF re-run in progress), gemini-3.8-flash, 20 prompts x 3 samples = 60 first tries per arm

Mechanical tables: `RESULTS.md`, `INSIGHTS-*.md`. Grades: C = measured here. All numbers are for this model and these prompts; 60 first tries give wide intervals.

## X3D (fork validator: XSD plus semantic gate) - finished
| arm | valid | note |
|---|---|---|
| A0 zero-shot | 46/60 = 76.7% [64.6, 85.6] | all 14 failures are XSD errors, almost all invented PBR attributes (`Material roughness`/`metalness`), the same defect the 2024-design rerun found |
| A1 two examples | 58/60 = 96.7% | +20 points vs A0, gained 14 lost 2, exact McNemar p = 0.004 (H2 supported) |
| A0 + deterministic repair | 46/60 | adds nothing here (H3) |
| A2 report loop (<=3 rounds) | 60/60 = 100% | all 14 failures fixed in one round; paired vs A0 p = 1.2e-4 |
| A3 blind resamples | 57/60 = 95% | A2 minus A3 = +5 points, 3 gained 0 lost, p = 0.25: **below the pre-registered 10-point rule, so H1 is not established**; the report helps, a retry helps almost as much, and 60 trials cannot separate them |
| A4 det repair then loop | 60/60 | same as A2 |
Completeness (part counts) 100% in every arm; the Gemini judge rated all 118 valid documents it saw 2 of 2.

## URDF (my own rules, grade L) - finished
A0 57/60 = 95.0%; A1 60/60; det repair adds 0; A2 60/60; A3 58/60 (96.7%); A2 minus A3 = +3.3 points, p = 0.5 (H1 not established). **All 3 zero-shot failures are one prompt, the hexapod (U-C4), where the answer hit the 8,192-token limit (finish MAX_TOKENS) and was truncated**: a budget artifact, not a modelling failure. Completeness 88% of valid documents meet the part-count expectation in every arm, a floor, not fidelity. **Goodhart signal (H4, small n):** the 3 hexapods repaired by the loop are valid but each carries 12 contact warnings (joints attached outside the parent geometry), and the Gemini judge rated them partly right (mean 1.0 of 2, 0 of 3 fully) while it rated first-try documents 1.98 of 2; the loop bought validity, not fidelity, on exactly the documents it touched. Judge and mechanical check agree on 101 of 119 documents.

## glTF - not final
The first run hit the 8,192-token limit on **58% of calls** (223 of 387; Gemini's hidden reasoning plus base64 arithmetic), so its failures measure the token budget, not the loop. I stopped it and kept it apart (`runs/gltf-8k/`, 53 completed first tries, $10.2): A0 34%, A1 60%, deterministic repair alone lifts A0 to 49% (it fixes buffer byteLength and min/max bookkeeping, no model call), report loop 54.7%, det repair then loop 64%, blind resamples 58.5%. Treat as truncation-confounded. A re-run with a 32,768-token limit is running now (cap $25); the watchdog will finish and write the judge, insights and the demo pillars.

## What this says so far
1. The report loop reaches 100% where first-try validity is imperfect, and the deterministic repairer adds little for these models; few-shot examples are the strongest first-try lever (X3D +20 points).
2. **A blind retry is nearly as good as the report at this scale**: the pre-registered 10-point bar is not met for X3D or URDF. A larger n or harder prompts are needed to separate them.
3. Valid is not complete or placed: the loop's repairs can leave contact warnings and partial fidelity (URDF hexapods), which the judge sees and the validator does not.
4. Operational: Gemini flash call latency here is minutes (median 103 s X3D, 168 s URDF) on the shared project; and a token limit that is too low silently turns capability into truncation: log `finish` always.
5. Cost so far: X3D $1.46, URDF $1.93, glTF 8k run $10.2, estimated at the prices assumed in vertex.py.
