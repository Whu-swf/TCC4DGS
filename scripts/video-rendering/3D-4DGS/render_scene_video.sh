#!/usr/bin/env bash
set -euo pipefail

# 默认批量渲染六个场景；设置 SCENE_NAME 可只渲染一个场景。
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python}"
DATA_ROOT="${DATA_ROOT:-/data/swf/4DGS}"
CONFIG_PATH="${CONFIG_PATH:-${SCRIPT_DIR}/configs/n3v/default.yaml}"
FPS="${FPS:-30}"
MULTIVIEW_FRAMES="${MULTIVIEW_FRAMES:-300}"
SCENE_NAMES=(actor1_4 actor2_3 actor5_6 cut_roasted_beef flame_steak sear_steak)
if [[ -n "${SCENE_NAME:-}" ]]; then
  SCENE_NAMES=("${SCENE_NAME}")
fi

for scene_name in "${SCENE_NAMES[@]}"; do
  source_path="${DATA_ROOT}/${scene_name}/colmap_0"
  model_path="${DATA_ROOT}/3D-4DGS/${scene_name}"
  checkpoint_path="${model_path}/chkpnt6000.pth"
  output_path="${DATA_ROOT}/videos/3D-4DGS_${scene_name}.mp4"

  mkdir -p "$(dirname -- "${output_path}")"
  CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}" "${PYTHON_BIN}" "${SCRIPT_DIR}/render_scene_video.py" \
    --config "${CONFIG_PATH}" \
    --source-path "${source_path}" \
    --model-path "${model_path}" \
    --checkpoint "${checkpoint_path}" \
    --multiview \
    --multiview-frames "${MULTIVIEW_FRAMES}" \
    --fps "${FPS}" \
    --output "${output_path}"
done
