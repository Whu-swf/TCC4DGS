"""调用 STGS 文件夹内的方法代码，渲染多视角轨迹并编码为 MP4。"""

import argparse
import os
import re
import runpy
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_METHOD_ROOT = Path("/home/swf/code/STGS/SpacetimeGaussians")
DEFAULT_OUTPUT = "stgs_multiview.mp4"


def resolve_input_path(path: Path, method_root: Path) -> Path:
    """相对路径优先按调用目录解析，不存在时再按 STGS 根目录解析。"""
    if path.is_absolute():
        return path.resolve()
    caller_path = path.resolve()
    project_path = (method_root / path).resolve()
    return caller_path if caller_path.exists() else project_path


def natural_key(path: Path):
    """按文件名中的数字自然排序。"""
    return [int(part) if part.isdigit() else part.lower()
            for part in re.split(r"(\d+)", path.name)]


def normalize(vector, np):
    """归一化三维向量，并拒绝退化方向。"""
    norm = np.linalg.norm(vector)
    if norm < 1e-8:
        raise ValueError("相机轨迹包含零长度方向向量。")
    return vector / norm


def generate_sweep_positions(base, target, world_up, camera_centers, frame_count, np):
    """生成左到右、上到下、外到里的连续相机轨迹。"""
    forward = normalize(target - base, np)
    right = np.cross(forward, world_up)
    if np.linalg.norm(right) < 1e-8:
        fallback_up = np.array([0.0, 0.0, 1.0])
        if abs(float(np.dot(forward, fallback_up))) > 0.95:
            fallback_up = np.array([0.0, 1.0, 0.0])
        right = np.cross(forward, fallback_up)
    right = normalize(right, np)
    up = normalize(np.cross(right, forward), np)

    center_distances = np.linalg.norm(camera_centers - base[None], axis=1)
    spread = np.percentile(center_distances, 75)
    focus_distance = np.linalg.norm(target - base)
    # 将轨迹位移统一缩小到原范围的 60%。
    scale = max(float(spread), float(focus_distance) * 0.03, 1e-3) * 0.6
    waypoints = np.stack(
        [
            base - right * 0.8 * scale,
            base + right * 0.8 * scale,
            base + up * 0.5 * scale,
            base - up * 0.5 * scale,
            base - forward * 0.65 * scale,
            base + forward * 0.4 * scale,
        ]
    )
    waypoint_times = np.array(
        [0.0, 1.0 / 3.0, 5.0 / 12.0, 2.0 / 3.0, 3.0 / 4.0, 1.0]
    )

    positions = []
    for progress in np.linspace(0.0, 1.0, frame_count):
        segment = min(
            np.searchsorted(waypoint_times, progress, side="right") - 1,
            len(waypoints) - 2,
        )
        segment = max(segment, 0)
        local = (
            (progress - waypoint_times[segment])
            / (waypoint_times[segment + 1] - waypoint_times[segment])
        )
        local = local * local * (3.0 - 2.0 * local)
        positions.append(
            (1.0 - local) * waypoints[segment] + local * waypoints[segment + 1]
        )
    return np.stack(positions)


def run_local_multiview_test(test_args):
    """在 STGS 进程内替换多视角相机加载器，再运行方法目录的 test.py。"""
    method_root = Path(os.environ["RENDER_METHOD_ROOT"]).expanduser().resolve()
    thirdparty_root = method_root / "thirdparty" / "gaussian_splatting"
    sys.path.insert(0, str(method_root))
    sys.path.append(str(thirdparty_root))

    import numpy as np
    import torch
    from scene import dataset_readers
    from utils.graphics_utils import (
        getProjectionMatrix,
        getProjectionMatrixCV,
        getWorld2View2,
    )

    def read_colmap_cameras_mv(
        cam_extrinsics,
        cam_intrinsics,
        images_folder,
        near,
        far,
        startime=0,
        duration=50,
    ):
        del images_folder, startime
        if not cam_extrinsics:
            raise ValueError("COLMAP 相机列表为空，无法生成多视角轨迹。")

        camera_names = [extrinsic.name for extrinsic in cam_extrinsics.values()]
        reference_name = (
            "cam00.png"
            if "cam00.png" in camera_names
            else sorted(camera_names, key=lambda name: natural_key(Path(name)))[0]
        )
        print(f"\n多视角参考相机：{reference_name}")

        camera_centers = []
        for extrinsic in cam_extrinsics.values():
            capture_r = np.transpose(dataset_readers.qvec2rotmat(extrinsic.qvec))
            capture_t = np.array(extrinsic.tvec)
            capture_w2c = getWorld2View2(capture_r, capture_t)
            camera_centers.append(np.linalg.inv(capture_w2c)[:3, 3])
        camera_centers = np.stack(camera_centers)

        reference = next(
            extrinsic
            for extrinsic in cam_extrinsics.values()
            if extrinsic.name == reference_name
        )
        intr = cam_intrinsics[reference.camera_id]
        height, width = intr.height, intr.width
        rotation = np.transpose(dataset_readers.qvec2rotmat(reference.qvec))
        translation = np.array(reference.tvec)
        world_view = torch.tensor(
            getWorld2View2(rotation, translation), dtype=torch.float32, device="cuda"
        ).transpose(0, 1)

        if intr.model == "SIMPLE_PINHOLE":
            focal_x = focal_y = intr.params[0]
            principal_x, principal_y = intr.params[1], intr.params[2]
        elif intr.model == "PINHOLE":
            focal_x, focal_y = intr.params[0], intr.params[1]
            principal_x, principal_y = intr.params[2], intr.params[3]
        else:
            raise ValueError(f"不支持的 COLMAP 相机模型：{intr.model}")
        fov_y = dataset_readers.focal2fov(focal_y, height)
        fov_x = dataset_readers.focal2fov(focal_x, width)
        cxr = principal_x / width - 0.5
        cyr = principal_y / height - 0.5
        if cyr != 0.0:
            projection = getProjectionMatrixCV(
                znear=0.01, zfar=100.0, fovX=fov_x, fovY=fov_y, cx=cxr, cy=cyr
            ).transpose(0, 1).cuda()
        else:
            projection = getProjectionMatrix(
                znear=0.01, zfar=100.0, fovX=fov_x, fovY=fov_y
            ).transpose(0, 1).cuda()

        camera_center = world_view.inverse()[3, :3]
        projected = torch.tensor((0, 0, 1, 1), dtype=torch.float32, device="cuda")
        projected = projected.unsqueeze(0) @ projection.T.inverse().T
        direction_local = projected / projected[:, 3:]
        camera_to_world = world_view.T.inverse()
        direction = direction_local[:, :3] @ camera_to_world[:3, :3].T
        ray_direction = torch.nn.functional.normalize(direction, p=2.0, dim=-1)
        target = camera_center + ray_direction * 30.0

        frame_count = int(os.environ.get("STGS_MULTIVIEW_FRAMES", "300"))
        if frame_count < 2:
            raise ValueError("STGS_MULTIVIEW_FRAMES 必须至少为 2。")
        base_np = camera_center.cpu().numpy()
        target_np = target.squeeze(0).cpu().numpy()
        positions = generate_sweep_positions(
            base_np, target_np, -rotation[:, 1], camera_centers, frame_count, np
        )

        cam_infos = []
        for index, new_center in enumerate(positions):
            new_forward = target_np - new_center
            new_right = normalize(np.cross(rotation[:, 1], new_forward), np)
            new_up = normalize(np.cross(new_forward, new_right), np)
            new_rotation = np.stack(
                [new_right, new_up, normalize(new_forward, np)], axis=1
            )
            camera_to_world = np.eye(4)
            camera_to_world[:3, :3] = new_rotation
            camera_to_world[:3, 3] = new_center
            new_translation = np.linalg.inv(camera_to_world)[:3, 3]
            cam_infos.append(
                dataset_readers.CameraInfo(
                    uid=index,
                    R=new_rotation,
                    T=new_translation,
                    FovY=fov_y,
                    FovX=fov_x,
                    image=None,
                    image_path=None,
                    image_name=f"mv_{index}",
                    width=width,
                    height=height,
                    near=near,
                    far=far,
                    timestamp=index / frame_count,
                    pose=1,
                    hpdirecitons=0,
                    cxr=0.0,
                    cyr=0.0,
                )
            )
        return cam_infos

    dataset_readers.readColmapCamerasMv = read_colmap_cameras_mv
    old_argv = sys.argv
    try:
        sys.argv = [str(method_root / "test.py"), *test_args]
        runpy.run_path(str(method_root / "test.py"), run_name="__main__")
    finally:
        sys.argv = old_argv


def find_latest_frames(model_path: Path, split: str) -> Path:
    candidates = [path for path in (model_path / split).glob("ours_*/renders")
                  if path.is_dir()]
    if not candidates:
        raise FileNotFoundError(
            f"未找到渲染帧目录：{model_path / split / 'ours_*' / 'renders'}"
        )
    return max(candidates, key=lambda path: path.stat().st_mtime)


def encode_video(frame_dir: Path, output: Path, fps: int, pattern: str) -> None:
    if fps <= 0:
        raise ValueError("FPS 必须大于 0。")
    frames = sorted(
        (path for path in frame_dir.glob(pattern) if path.is_file()),
        key=natural_key,
    )
    if not frames:
        raise FileNotFoundError(f"{frame_dir} 中没有匹配 {pattern!r} 的图像。")
    output.parent.mkdir(parents=True, exist_ok=True)

    # 优先调用 ffmpeg，生成浏览器兼容的 H.264/yuv420p 视频。
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
        raise RuntimeError(
            "未找到 ffmpeg 或 imageio；请先安装 ffmpeg，或安装 imageio 与 imageio-ffmpeg。"
        ) from exc

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
                raise ValueError(
                    f"帧尺寸不一致：{frame_path} 为 {size}，预期 {expected_size}。"
                )
            writer.append_data(frame)

    print(f"视频已生成：{output}（{len(frames)} 帧，{fps} FPS）")


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--method-root", type=Path, default=DEFAULT_METHOD_ROOT,
        help="STGS 方法根目录",
    )
    parser.add_argument("--model-path", type=Path, required=True, help="训练模型目录")
    parser.add_argument(
        "--source-path", type=Path, required=True,
        help="预处理后的场景目录（通常为 colmap_0）",
    )
    parser.add_argument("--config", type=Path, required=True, help="场景 JSON 配置文件")
    parser.add_argument(
        "--iteration", type=int, default=-1,
        help="测试迭代；-1 表示自动选择最新迭代",
    )
    parser.add_argument("--valloader", default="colmapvalid", help="验证数据加载器")
    parser.add_argument(
        "--multiview", action="store_true",
        help="渲染连续自由视角轨迹，而不是测试视角序列",
    )
    parser.add_argument("--multiview-frames", type=int, default=300)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--frame-pattern", default="*.png")
    parser.add_argument("--frames-dir", type=Path, help="直接使用已有帧目录")
    parser.add_argument("--output", type=Path, default=Path(DEFAULT_OUTPUT))
    parser.add_argument("--skip-render", action="store_true", help="仅编码已有帧")
    parser.add_argument("--dry-run", action="store_true", help="只打印渲染命令")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.multiview_frames < 2:
        raise ValueError("--multiview-frames 必须至少为 2。")

    method_root = args.method_root.expanduser().resolve()
    model_path = resolve_input_path(args.model_path, method_root)
    source_path = resolve_input_path(args.source_path, method_root)
    config_path = resolve_input_path(args.config, method_root)
    split = "mv" if args.multiview else "test"
    valloader = "colmapmv" if args.multiview else args.valloader
    test_script = method_root / "test.py"
    test_args = [
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
    display_command = [sys.executable, str(test_script), *test_args]
    print("STGS 渲染命令：", subprocess.list2cmdline(display_command))
    if args.dry_run:
        return

    if not args.skip_render:
        if not test_script.is_file():
            raise FileNotFoundError(f"STGS 方法入口不存在：{test_script}")
        if not config_path.is_file():
            raise FileNotFoundError(f"配置文件不存在：{config_path}")
        if not model_path.is_dir():
            raise FileNotFoundError(f"模型目录不存在：{model_path}")
        if not source_path.is_dir():
            raise FileNotFoundError(f"场景目录不存在：{source_path}")
        render_env = os.environ.copy()
        render_env["STGS_MULTIVIEW_FRAMES"] = str(args.multiview_frames)
        render_env["RENDER_METHOD_ROOT"] = str(method_root)
        command = display_command
        if args.multiview:
            command = [
                sys.executable,
                str(SCRIPT_DIR / "render_scene_video.py"),
                "--_run-local-multiview",
                *test_args,
            ]
        subprocess.run(command, cwd=method_root, check=True, env=render_env)

    frame_dir = args.frames_dir or find_latest_frames(model_path, split)
    encode_video(
        frame_dir.resolve(), args.output.resolve(), args.fps, args.frame_pattern
    )


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--_run-local-multiview":
        run_local_multiview_test(sys.argv[2:])
    else:
        main()
