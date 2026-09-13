#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: npm run import:dryer-cad -- /absolute/path/to/model.dae" >&2
  exit 2
fi

script_dir="$(cd "$(dirname "$0")" && pwd)"
frontend_dir="$(cd "$script_dir/.." && pwd)"
blender_bin="${BLENDER_BIN:-/Applications/Blender.app/Contents/MacOS/Blender}"

"$blender_bin" --background --python "$script_dir/importIndustrialDryerCad.py" -- "$1" "$frontend_dir/public/models/industrial_dryer.glb"
