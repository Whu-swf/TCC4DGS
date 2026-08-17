"""调用 SpacetimeGaussians 官方测试流程，并将渲染帧编码为 GitHub 可播放的 MP4。"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def resolve_input_path(path: Path) -> Path:
    """相对路径优先按调用目录解析，不存在时再按项目根目录解析。"""
    if path.is_absolute():
        return path.resolve()
    caller_path = path.resolve()
    project_path = (ROOT / path).resolve()
    return caller_path if caller_path.exists() else project_path


def natural_key(path: Path):
    """按文件名中的数字自然排序，避免 10.png 排在 2.png 前面。"""
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", path.name)]


def find_latest_frames(model_path: Path, split: str) -> Path:
    candidates = [path for path in (model_path / split).glob("ours_*/renders") if path.is_dir()]
    if not candidates:
        raise FileNotFoundError(f"未找到渲染帧目录：{model_path / split / 'ours_*' / 'renders'}")
    return max(candidates, key=lambda path: path.stat().st_mtime)


def encode_video(frame_dir: Path, output: Path, fps: int, pattern: str) -> None:
    if fps <= 0:
        raise ValueError("FPS 必须大于 0。")
    frames = sorted((path for path in frame_dir.glob(pattern) if path.is_file()), key=natural_key)
    if not frames:
        raise FileNotFoundError(f"{frame_dir} 中没有匹配 {pattern!r} 的图像。")
    output.parent.mkdir(parents=True, exist_ok=True)

    # 优先调用 ffmpeg，直接生成浏览器兼容的 H.264/yuv420p 视频。
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        with tempfile.TemporaryDirectory(prefix="stgs_video_") as temp_dir:
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
        raise RuntimeError("未找到 ffmpeg 或 imageio；请先安装 ffmpeg，或安装 imageio 与 imageio-ffmpeg。") from exc

    with imageio.get_writer(
        str(output),
        format="FFMPEG",
        fps=fps,
        codec="libx264",
        pixelformat="yuv420p",
        macro_block_size=2,
        ffmpeg_params=["-movflags", "+faststart"],
    ) as writer:
        expected_size = None
        for frame_path in frames:
            frame = imageio.imread(frame_path)
            if frame.ndim == 2:
                frame = frame[:, :, None].repeat(3, axis=2)
            frame = frame[:, :, :3]
            # yuv420p 要求宽高为偶数。
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
    parser.add_argument("--source-path", type=Path, required=True, help="预处理后的场景目录（通常为 colmap_0）")
    parser.add_argument("--config", type=Path, required=True, help="与场景对应的 JSON 配置文件")
    parser.add_argument("--iteration", type=int, default=-1, help="测试迭代；-1 表示自动选择最新迭代")
    parser.add_argument("--valloader", default="colmapvalid", help="验证数据加载器")
    parser.add_argument(
        "--multiview",
        action="store_true",
        help="渲染300帧连续自由视角轨迹，而不是测试视角序列",
    )
    parser.add_argument("--multiview-frames", type=int, default=300)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--frame-pattern", default="*.png", help="待编码帧的 glob 表达式")
    parser.add_argument("--frames-dir", type=Path, help="直接使用已有帧目录")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--skip-render", action="store_true", help="跳过官方渲染，仅编码已有帧")
    parser.add_argument("--dry-run", action="store_true", help="只打印渲染命令")
    return parser.parse_args()


def main():
    args = parse_args()
    model_path = resolve_input_path(args.model_path)
    source_path = resolve_input_path(args.source_path)
    config_path = resolve_input_path(args.config)
    split = "mv" if args.multiview else "test"
    valloader = "colmapmv" if args.multiview else args.valloader
    output = args.output or Path(
        "spacetime_gaussians_multiview.mp4" if args.multiview else "spacetime_gaussians.mp4"
    )
    command = [
        sys.executable,
        "test.py",
        "--quiet",
        "--eval",
        "--skip_train",
        "--valloader",
        valloader,
        "--configpath",
        str(config_path),
        "--model_path",
        str(model_path),
        "--source_path",
        str(source_path),
        "--test_iteration",
        str(args.iteration),
    ]
    print("渲染命令：", subprocess.list2cmdline(command))
    if args.dry_run:
        return
    if not config_path.is_file():
        raise FileNotFoundError(f"配置文件不存在：{config_path}")
    if not model_path.is_dir():
        raise FileNotFoundError(f"模型目录不存在：{model_path}")
    if not source_path.is_dir():
        raise FileNotFoundError(f"场景目录不存在：{source_path}")
    if args.multiview_frames < 2:
        raise ValueError("--multiview-frames 必须至少为 2。")
    if not args.skip_render:
        render_env = os.environ.copy()
        render_env["STGS_MULTIVIEW_FRAMES"] = str(args.multiview_frames)
        subprocess.run(command, cwd=ROOT, check=True, env=render_env)

    frame_dir = args.frames_dir or find_latest_frames(model_path, split)
    encode_video(frame_dir.resolve(), output.resolve(), args.fps, args.frame_pattern)


if __name__ == "__main__":
    main()
