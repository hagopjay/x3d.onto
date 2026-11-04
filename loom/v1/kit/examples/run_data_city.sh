#!/bin/sh
# Worked example: run Loom v1's kit on the Data City Loom project, read-only against incoming/.
# 1. copy the delivered project into a scratch work dir (incoming/ is never edited);
# 2. run the witnesses, record the unrun ones, accept under x3d-static/v1, write a receipt;
# 3. prove the gate bites on the real project: a post-witness edit and a planted trap must both reject.
set -eu
V1="$(cd "$(dirname "$0")/../.." && pwd)"
SRC="${1:-$V1/../incoming/unpacked/Data-City-Loom/Data-City-Loom}"
RUN="${2:-$V1/runs/data-city-$(date -u +%Y%m%d)}"
WORK="$V1/.work/data-city"
LOOM="$V1/kit/loom"
PROFILE="$V1/kit/profiles/x3d-static.json"
EV="$RUN/evidence"

[ -d "$WORK" ] && chmod -R u+w "$WORK"
rm -rf "$WORK" "$EV"; mkdir -p "$WORK" "$EV"
cp -R "$SRC/." "$WORK/"
chmod -R u+w "$WORK"   # incoming/ is read-only; only the scratch copy becomes writable
find "$WORK" -name __pycache__ -type d -prune -exec rm -rf {} +

"$LOOM" candidate "$WORK"
"$LOOM" grammar  "$WORK" --evidence "$EV" --files 'runs/*/world.x3d'
"$LOOM" traps    "$WORK" --evidence "$EV" --files 'runs/*/world.x3d' --host strict
# Truth: the project's own source-to-scene gate (exit 0 pass, 1 contract violation, 2 instrument error).
# PYTHONDONTWRITEBYTECODE keeps __pycache__ out of the candidate while the witness runs.
PYTHONDONTWRITEBYTECODE=1 "$LOOM" command "$WORK" --evidence "$EV" --name truth -- \
  python3 -m citycore.cli runs/baseline/source.csv runs/baseline/manifest.json --scene runs/baseline/world.x3d
PYTHONDONTWRITEBYTECODE=1 "$LOOM" foldback "$WORK" --evidence "$EV" --patch "$WORK/integration/data-city-gates.patch"
for w in behaviour eyes host; do
  "$LOOM" record "$WORK" --evidence "$EV" --name "$w" --status not_run --grade L \
    --reason "Needs a real browser (X_ITE headless, frames, strict host copy); not run by the v1 agent. The projects agent runs the pages."
done

"$LOOM" accept  "$WORK" --evidence "$EV" --profile "$PROFILE"
"$LOOM" receipt "$WORK" --evidence "$EV" --profile "$PROFILE" --subject "Data City Loom (delivered zip), static profile" \
  --out "$RUN/receipt.json" --outputs "$WORK/runs/baseline/world.x3d" "$WORK/runs/revised/world.x3d" --force
"$LOOM" verify-receipt "$RUN/receipt.json"

# Negative controls on the real project (expected exit 1 with the named code).
echo "--- control: edit a generated scene after the witnesses ran -> STALE_WITNESS"
printf '\n<!-- hand edit -->\n' >> "$WORK/runs/baseline/world.x3d"
if "$LOOM" accept "$WORK" --evidence "$EV" --profile "$PROFILE" > "$RUN/control-stale.json"; then echo "SURVIVING_CONTROL stale"; exit 1; fi
cat "$RUN/control-stale.json"
echo "--- control: plant a colour above 1 -> traps fail"
sed -i '' 's/diffuseColor="\([^"]*\)"/diffuseColor="1.5 0 0"/' "$WORK/runs/baseline/world.x3d"
"$LOOM" traps "$WORK" --evidence "$RUN/control-evidence" --files 'runs/*/world.x3d' --host strict > /dev/null
python3 -I -c "import json,sys; r=json.load(open(sys.argv[1])); print({'status': r['status'], 'errors': r['measurements']['errors']}); sys.exit(0 if r['status']=='fail' else 1)" "$RUN/control-evidence/traps.json"
echo "done: $RUN"
