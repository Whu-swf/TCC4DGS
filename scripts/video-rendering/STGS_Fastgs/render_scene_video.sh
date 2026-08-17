#!/usr/bin/env bash
set -euo pipefail

# 默认批量渲染六个场景；设置 SCENE_NAME 可只渲染一个场景。
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python}"
METHOD_ROOT="${METHOD_ROOT:-/home/swf/code/STGS_Fastgs/SpacetimeGaussians}"
DATA_ROOT="${DATA_ROOT:-/data/swf/4DGS}"
ITERATION="${ITERATION:-30000}"
FPS="${FPS:-30}"
MULTIVIEW_FRAMES="${MULTIVIEW_FRAMES:-300}"
SCENE_NAMES=(actor1_4 actor2_3 actor5_6 cut_roasted_beef flame_steak sear_steak)
if [[ -n "${SCENE_NAME:-}" ]]; then
  SCENE_NAMES=("${SCENE_NAME}")
fi

for scene_name in "${SCENE_NAMES[@]}"; do
  source_path="${DATA_ROOT}/${scene_name}/colmap_0"
  model_path="${DATA_ROOT}/STGS_Fastgs/${scene_name}"
  config_path="${METHOD_ROOT}/configs/n3d_lite/${scene_name}.json"
  output_path="${DATA_ROOT}/videos/STGS_Fastgs_${scene_name}.mp4"

  mkdir -p "$(dirname -- "${output_path}")"
  CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}" "${PYTHON_BIN}" "${SCRIPT_DIR}/render_scene_video.py" \
    --method-root "${METHOD_ROOT}" \
    --config "${config_path}" \
    --source-path "${source_path}" \
    --model-path "${model_path}" \
    --iteration "${ITERATION}" \
    --multiview \
    --multiview-frames "${MULTIVIEW_FRAMES}" \
    --fps "${FPS}" \
    --output "${output_path}"
done
