# Morning note (written 2026-10-21 ~06:00Z, user asleep, "do your best")

**What is running unattended**
- Three runners (x3d, urdf, gltf): 20 prompts x 3 samples x arms A0, A1, A2, A3, A4, gemini-3.8-flash through `tools/vertex.py`, us-east4, $20 cumulative cap each, $60 total cap in `GO.json`. Logs `runs/full-*.log`; every paid answer with latency and tokens in `runs/raw-*.jsonl`.
- `watchdog.py` (log `runs/watchdog.log`): every 90 s restarts a dead runner, or one that has written nothing for 25 minutes; restarts resume from the raw log (answers already paid for are served from cache and counted toward the cap). Max 8 restarts per domain, 9 hours overall.
- When all three result files exist the watchdog runs, in order: the Gemini judge on valid documents (cap $3 each domain), `insights.py` per domain, `final_report.py` (writes `RESULTS.md`), the demo rebuild (fills the evaluation pillars) and the number audit, then writes `runs/WATCHDOG-DONE`.
- `caffeinate -i` is tied to the watchdog process so the Mac does not idle-sleep while it runs (it ends with the watchdog). A closed lid or a manual Sleep still stops everything: leave it open and plugged in. Processes resume from the cache if you restart them.

**Check in the morning**
`runs/watchdog.log`, then `RESULTS.md` and `INSIGHTS-*.md` if done; else `grep -c '^  \[' runs/full-*.log` for progress. Spend: `python3 -c` over `~/Projects/x3d/work/shroud-ai/ledger.jsonl` purposes starting `xdomain`.

**If something is stuck**
Kill with `pkill -f watchdog.py; pkill -f "runner.py --domain"`. Resume by `./run_full.sh` (cache keeps what was paid for). Partial results are never lost: `runs/raw-*.jsonl` has every answer.

**Not touched**: Cloud console and quota settings, vertex.py, other sessions' servers or jobs, any repo.
