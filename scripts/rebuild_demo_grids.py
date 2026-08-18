"""按统一顺序重建 README 使用的六场景对比视频拼图。"""

from pathlib import Path
import subprocess
import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "assets" / "videos" / "comparisons"
OUTPUT = ROOT / "demo"
SCENES = [
    "cut_roasted_beef",
    "flame_steak",
    "sear_steak",
    "actor1_4",
    "actor2_3",
    "actor5_6",
]
METHODS = [
    ("SpacetimeGaussians", "STGS + Ours (TCC4DGS)"),
    ("STGS", "STGS"),
    ("STGS_Fastgs", "STGS + FastGS"),
    ("4DGaussians", "4DGaussians"),
    ("3D-4DGS", "3D-4DGS"),
    ("Ex4DGS", "Ex4DGS"),
]
TILE_W, TILE_H = 640, 360


def label(frame: np.ndarray, text: str) -> np.ndarray:
    cv2.rectangle(frame, (0, 0), (min(TILE_W, 14 * len(text) + 26), 31), (18, 18, 18), -1)
    cv2.putText(frame, text, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (245, 245, 245), 1, cv2.LINE_AA)
    return frame


def make_scene(scene: str) -> None:
    captures = []
    for prefix, title in METHODS:
        path = SOURCE / f"{prefix}_{scene}.mp4"
        cap = cv2.VideoCapture(str(path))
        if not cap.isOpened():
            raise FileNotFoundError(path)
        captures.append((cap, title))

    temp = OUTPUT / f".{scene}.tmp.mp4"
    writer = cv2.VideoWriter(str(temp), cv2.VideoWriter_fourcc(*"mp4v"), 30, (TILE_W * 3, TILE_H * 2))
    if not writer.isOpened():
        raise RuntimeError(f"无法创建视频：{temp}")
    try:
        while True:
            tiles = []
            finished = False
            for cap, title in captures:
                ok, frame = cap.read()
                if not ok:
                    finished = True
                    break
                frame = cv2.resize(frame, (TILE_W, TILE_H), interpolation=cv2.INTER_AREA)
                tiles.append(label(frame, title))
            if finished:
                break
            grid = np.vstack((np.hstack(tiles[:3]), np.hstack(tiles[3:])))
            writer.write(grid)
    finally:
        writer.release()
        for cap, _ in captures:
            cap.release()

    mp4 = OUTPUT / f"{scene}.mp4"
    gif = OUTPUT / f"{scene}.gif"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(temp), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(mp4)], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp4), "-vf", "fps=15,scale=960:-1:flags=lanczos", "-loop", "0", str(gif)], check=True)
    temp.unlink(missing_ok=True)
    print(f"已生成：{mp4.name}、{gif.name}")


if __name__ == "__main__":
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for scene_name in SCENES:
        make_scene(scene_name)
