"""渲染 4DGaussians 场景，并编码为 GitHub 可播放的 MP4。"""

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def natural_key(path: Path):
    return [int(part) if part.isdigit() else part.lower()
            for part in re.split(r"(\d+)", path.name)]


def resolve_input_path(path: Path) -> Path:
    if path.is_absolute():
        return path.resolve()
    candidates = ((Path.cwd() / path).resolve(), (ROOT / path).resolve())
    return next((candidate for candidate in candidates if candidate.exists()), candidates[0])


def find_latest_frames(model_path: Path, split: str) -> Path:
    candidates = [path for path in (model_path / split).glob("ours_*/renders")
                  if path.is_dir()]
    if not candidates:
        raise FileNotFoundError(f"未找到 {model_path / split / 'ours_*' / 'renders'}")
    return max(candidates, key=lambda path: path.stat().st_mtime)


def encode_video(frame_dir: Path, output: Path, fps: int, pattern: str) -> None:
    if fps <= 0:
        raise ValueError("FPS 必须大于 0。")
    frames = sorted((path for path in frame_dir.glob(pattern) if path.is_file()),
                    key=natural_key)
    if not frames:
        raise FileNotFoundError(f"{frame_dir} 中没有匹配 {pattern!r} 的图像。")
    output.parent.mkdir(parents=True, exist_ok=True)

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        with tempfile.TemporaryDirectory(prefix="4dgs_video_") as temp_dir:
            concat_file = Path(temp_dir) / "frames.txt"
            duration = 1.0 / fps
            lines = []
            for frame_path in frames:
                normalized = str(frame_path.resolve()).replace("\\", "/").replace("'", "'\\''")
                lines.extend((f"file '{normalized}'", f"duration {duration:.9f}"))
            lines.append(f"file '{normalized}'")
            concat_file.write_text("\n".join(lines), encoding="utf-8")
            subprocess.run(
                [
                    ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                    "-f", "concat", "-safe", "0", "-i", str(concat_file),
                    "-vf", f"fps={fps},scale=trunc(iw/2)*2:trunc(ih/2)*2",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart", str(output),
                ],
                check=True,
            )
        print(f"视频已生成：{output}（{len(frames)} 帧，{fps} FPS）")
        return

    try:
        import imageio.v2 as imageio
    except ImportError as exc:
        raise RuntimeError(
            "未找到 ffmpeg 或 imageio；请安装 ffmpeg，或安装 imageio 与 imageio-ffmpeg。"
        ) from exc

    with imageio.get_writer(
        str(output), format="FFMPEG", fps=fps, codec="libx264",
        pixelformat="yuv420p", macro_block_size=2,
        ffmpeg_params=["-movflags", "+faststart"],
    ) as writer:
        expected_size = None
        for frame_path in frames:
            frame = imageio.imread(frame_path)
            if frame.ndim == 2:
                frame = frame[:, :, None].repeat(3, axis=2)
            frame = frame[:, :, :3]
            frame = frame[: frame.shape[0] // 2 * 2, : frame.shape[1] // 2 * 2]
            size = frame.shape[:2]
            if expected_size is None:
                expected_size = size
            elif size != expected_size:
                raise ValueError(f"帧尺寸不一致：{frame_path} 为 {size}，预期 {expected_size}。")
            writer.append_data(frame)

    print(f"视频已生成：{output}（{len(frames)} 帧，{fps} FPS）")


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-path", type=Path, required=True, help="训练模型目录")
    parser.add_argument("--source-path", type=Path, required=True, help="场景数据目录")
    parser.add_argument("--config", type=Path, required=True,
                        help="arguments 下对应场景的 Python 配置")
    parser.add_argument("--iteration", type=int, default=-1)
    parser.add_argument("--multiview", action="store_true",
                        help="渲染相机移动且时间推进的自由视点视频")
    parser.add_argument("--multiview-frames", type=int, default=300)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--frame-pattern", default="*.png")
    parser.add_argument("--frames-dir", type=Path, help="直接使用已有帧目录")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--skip-render", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    model_path = resolve_input_path(args.model_path)
    source_path = resolve_input_path(args.source_path)
    config_path = resolve_input_path(args.config)
    split = "mv" if args.multiview else "test"
    output = args.output or Path(
        "4dgaussians_multiview.mp4" if args.multiview else "4dgaussians.mp4"
    )

    command = [
        sys.executable, "render.py",
        "--model_path", str(model_path),
        "--source_path", str(source_path),
        "--configs", str(config_path),
        "--iteration", str(args.iteration),
        "--cameras_pt", "false",
        "--preload_gpu", "false",
        "--skip_train",
    ]
    if args.multiview:
        command.extend([
            "--skip_test", "--skip_video", "--render_multiview",
            "--multiview_frames", str(args.multiview_frames),
        ])
    else:
        command.append("--skip_video")

    print("渲染命令：", subprocess.list2cmdline(command))
    if args.dry_run:
        return

    for path, label in ((model_path, "模型目录"), (source_path, "场景目录")):
        if not path.exists():
            raise FileNotFoundError(f"{label}不存在：{path}")
    if not config_path.is_file():
        raise FileNotFoundError(f"配置文件不存在：{config_path}")
    if args.multiview_frames < 2:
        raise ValueError("--multiview-frames 必须至少为 2。")

    if not args.skip_render:
        subprocess.run(command, cwd=ROOT, check=True)

    frame_dir = resolve_input_path(args.frames_dir) if args.frames_dir else find_latest_frames(model_path, split)
    encode_video(frame_dir, output.resolve(), args.fps, args.frame_pattern)


if __name__ == "__main__":
    main()
