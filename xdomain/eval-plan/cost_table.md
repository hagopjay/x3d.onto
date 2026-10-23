| scenario | model | domain | calls (expected, mid) | expected USD low / mid / high failure | upper bound USD |
|---|---|---|---|---|---|
| pilot (5 prompts x 1 samples, arms A0+A2) | flash | both | 20 | $0.17 / $0.21 / $0.26 | $0.45 |
| pilot (5 prompts x 1 samples, arms A0+A2) | pro | both | 20 | $0.99 / $1.28 / $1.58 | $2.66 |
| lean (20 prompts x 2 samples, arms A0+A1+A2+A3) | flash | both | 314 | $2.62 / $3.38 / $4.14 | $6.92 |
| lean (20 prompts x 2 samples, arms A0+A1+A2+A3) | pro | both | 314 | $15.87 / $20.47 / $25.05 | $41.82 |
| full (20 prompts x 3 samples, arms A0+A1+A2+A3) | flash | both | 472 | $3.93 / $5.06 / $6.20 | $10.38 |

per call (flash): URDF doc ~1422 tokens, output incl. thinking ~2922, report-loop input ~1832; glTF doc ~1031, output ~2531, loop input ~1441
