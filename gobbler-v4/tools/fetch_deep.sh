#!/bin/sh
# Fetch the Gobbler 3 Deep build and X_ITE into gobbler-v4/data/deep and gobbler-v4/vendor (both git-ignored), verify their hashes,
# and patch the engine. Needs curl, tar, sha256sum (or shasum) and, for X_ITE, npm. Run from anywhere: make v4-data
set -eu
HERE=$(cd "$(dirname "$0")/.." && pwd)
SHA=51e185f6a830c2c70d055f8894b5dd2d735c20c3          # hagopjay/x3d.ML, branch claude/project-thread-0105va, "Gobbler 3 Deep"
BASE=https://raw.githubusercontent.com/hagopjay/x3d.ML/$SHA/gobbler-v3/deep/build-private
XITE=16.5.1
D=$HERE/data/deep
mkdir -p "$D" "$HERE/vendor"
sum() { if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | cut -d' ' -f1; else shasum -a 256 "$1" | cut -d' ' -f1; fi; }
get() {    # name sha256
  [ -f "$D/$1" ] && [ "$(sum "$D/$1")" = "$2" ] && { echo "have  $1"; return; }
  curl -fsSL "$BASE/$1" -o "$D/$1.part" || { rm -f "$D/$1.part"; echo "download failed: $1" >&2; exit 1; }
  mv "$D/$1.part" "$D/$1"
  [ "$(sum "$D/$1")" = "$2" ] || { echo "HASH MISMATCH for $1" >&2; exit 1; }
  echo "got   $1"
}
get graph-v3.json        36a308c89af35877b6b66520e05fa8563f738c28b6cff5b623418528a237cca9
get gobbler3.x3d         c73500bab832d3c3c2fc4eceedb199a10b7d9aa97ec6dfee5943d1bcc45748d4
get common.js            a3112205c7cb0a1694d0304acce850b8fc8d1ac556edbb7c71e942837be44aaa
get common.css           58d76ea3bf7cc689fb15d84f18b97b9bebb0823b11f82f15dc578fc93d80a8a8
get gobbler3-receipt.json dfcd208f2532a1120bc89f0baf9e9c663d7f9b6d9e21d31cc281a555f44b708d
python3 -I "$HERE/tools/patch_engine.py" "$D/common.js" "$HERE/engine/common.js"
if [ ! -f "$HERE/vendor/x_ite/x_ite.min.js" ]; then
  T=$(mktemp -d); (cd "$T" && npm pack "x_ite@$XITE" >/dev/null && tar xzf "x_ite-$XITE.tgz")
  mkdir -p "$HERE/vendor/x_ite"; cp -R "$T/package/dist/." "$HERE/vendor/x_ite/"; rm -rf "$T"; echo "got   vendor/x_ite $XITE"
else echo "have  vendor/x_ite"; fi
