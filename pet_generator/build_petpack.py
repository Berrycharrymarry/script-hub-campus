from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Iterable, Sequence

from PIL import Image, ImageChops, ImageDraw, ImageOps, UnidentifiedImageError


FORMAT_VERSION = 1
MAX_FILES = 48
MAX_FILE_BYTES = 12 * 1024 * 1024
MAX_TOTAL_UPLOAD_BYTES = 32 * 1024 * 1024
MAX_PACK_BYTES = 48 * 1024 * 1024
MAX_EDGE = 2048
MAX_FRAMES_PER_ACTION = 120
MAX_TOTAL_FRAME_PIXELS = 48_000_000
SUPPORTED_SUFFIXES = {".gif", ".png", ".webp", ".jpg", ".jpeg", ".bmp"}
SUPPORTED_ROLES = {"idle", "click", "drag", "sleep", "custom"}

Image.MAX_IMAGE_PIXELS = 16_777_216


class PetpackError(RuntimeError):
    """Base error for callers that should not expose internal details."""


class PetpackInputError(PetpackError):
    """The uploaded files or form fields are invalid."""


class PetpackServiceError(PetpackError):
    """The service could not create an output despite valid input."""


def _clean_text(value: str, fallback: str, limit: int = 32) -> str:
    cleaned = re.sub(r"[\t\r\n]+", " ", value or "").strip()
    return (cleaned or fallback)[:limit]


def _safe_filename(value: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip(" .")
    return (cleaned or "我的桌宠")[:64]


def _duration_for(image: Image.Image, default: int = 60) -> int:
    duration = int(image.info.get("duration") or default)
    return max(20, min(2000, duration))


def _remove_edge_background(image: Image.Image, threshold: int) -> Image.Image:
    rgba = image.convert("RGBA")
    probe = rgba.copy()
    marker = (1, 2, 3, 4)
    corners = [
        (0, 0),
        (probe.width - 1, 0),
        (0, probe.height - 1),
        (probe.width - 1, probe.height - 1),
    ]
    for corner in corners:
        pixel = probe.getpixel(corner)
        # Transparent corners are already background. Skipping them also keeps
        # transparent GIF/PNG artwork from losing similarly coloured outlines.
        if pixel[3] >= 224 and pixel != marker:
            ImageDraw.floodfill(probe, corner, marker, thresh=threshold)

    difference = ImageChops.difference(probe, Image.new("RGBA", probe.size, marker))
    channels = difference.split()
    any_difference = ImageChops.lighter(
        ImageChops.lighter(channels[0], channels[1]),
        ImageChops.lighter(channels[2], channels[3]),
    )
    removed_background = any_difference.point(lambda value: 255 if value == 0 else 0)
    alpha = rgba.getchannel("A")
    alpha.paste(0, mask=removed_background)
    rgba.putalpha(alpha)
    return rgba


def _has_visible_contrast(image: Image.Image, threshold: int) -> bool:
    """Return whether a frame contains content distinct from its corner background."""
    rgba = image.convert("RGBA")
    corner = rgba.getpixel((0, 0))[:3]
    difference = ImageChops.difference(
        rgba.convert("RGB"), Image.new("RGB", rgba.size, corner)
    )
    strongest_difference = ImageChops.lighter(
        ImageChops.lighter(difference.getchannel("R"), difference.getchannel("G")),
        difference.getchannel("B"),
    )
    foreground = strongest_difference.point(
        lambda value: 255 if value > threshold else 0
    )
    return foreground.getbbox() is not None


def _open_image(source: Path) -> Image.Image:
    if source.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise PetpackInputError(f"不支持的图片格式：{source.name}")
    if not source.is_file():
        raise PetpackInputError(f"找不到图片：{source.name}")
    if source.stat().st_size > MAX_FILE_BYTES:
        raise PetpackInputError(f"图片超过 {MAX_FILE_BYTES // 1024 // 1024}MB：{source.name}")
    try:
        return Image.open(source)
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as error:
        raise PetpackInputError(f"图片无法解码：{source.name}") from error


def _validate_image(image: Image.Image, source: Path) -> tuple[int, int, int]:
    width, height = image.size
    frame_count = int(getattr(image, "n_frames", 1))
    if width < 1 or height < 1 or width > MAX_EDGE or height > MAX_EDGE:
        raise PetpackInputError(f"图片尺寸必须在 1～{MAX_EDGE}px：{source.name}")
    if frame_count < 1 or frame_count > MAX_FRAMES_PER_ACTION:
        raise PetpackInputError(f"动画帧数必须在 1～{MAX_FRAMES_PER_ACTION} 帧：{source.name}")
    return width, height, frame_count


def build_petpack(
    image_paths: Sequence[str | Path],
    output_path: str | Path,
    *,
    labels: Sequence[str] | None = None,
    roles: Sequence[str] | None = None,
    pet_name: str = "我的桌宠",
    default_size: int = 120,
    remove_background: bool = False,
    remove_background_indices: Sequence[int] | None = None,
    background_threshold: int = 32,
) -> Path:
    if not 1 <= len(image_paths) <= MAX_FILES:
        raise PetpackInputError(f"每个桌宠需要 1～{MAX_FILES} 个图片文件。")
    if not 72 <= int(default_size) <= 320:
        raise PetpackInputError("默认尺寸必须在 72～320px。")
    if not 0 <= int(background_threshold) <= 96:
        raise PetpackInputError("背景容差必须在 0～96。")

    sources = [Path(path).resolve() for path in image_paths]
    total_upload_bytes = sum(path.stat().st_size for path in sources if path.is_file())
    if total_upload_bytes > MAX_TOTAL_UPLOAD_BYTES:
        raise PetpackInputError(
            f"本次上传总大小不能超过 {MAX_TOTAL_UPLOAD_BYTES // 1024 // 1024}MB。"
        )

    action_labels = list(labels or [])
    while len(action_labels) < len(sources):
        action_labels.append(sources[len(action_labels)].stem)
    action_labels = [
        _clean_text(label, f"动作 {index + 1}", 24)
        for index, label in enumerate(action_labels[: len(sources)])
    ]

    action_roles = [str(role).lower().strip() for role in (roles or [])]
    while len(action_roles) < len(sources):
        action_roles.append("idle" if len(action_roles) != 1 else "click")
    action_roles = action_roles[: len(sources)]
    for role in action_roles:
        if role not in SUPPORTED_ROLES:
            raise PetpackInputError(f"不支持的动作角色：{role}")

    cleanup_indices = {int(index) for index in (remove_background_indices or [])}
    invalid_cleanup_indices = [index for index in cleanup_indices if index < 0 or index >= len(sources)]
    if invalid_cleanup_indices:
        raise PetpackInputError("指定了不存在的去背景动作序号。")

    name = _clean_text(pet_name, "我的桌宠", 32)
    output = Path(output_path).resolve()
    if output.suffix.lower() != ".petpack":
        output = output.with_suffix(".petpack")
    output.parent.mkdir(parents=True, exist_ok=True)

    identity = hashlib.sha256()
    identity.update(name.encode("utf-8"))
    identity.update(str(default_size).encode("ascii"))
    total_frame_pixels = 0

    try:
        with tempfile.TemporaryDirectory(prefix="petpack-build-") as temporary:
            work = Path(temporary)
            actions: list[dict[str, object]] = []
            icon_source: Path | None = None

            for action_index, (source, label, role) in enumerate(
                zip(sources, action_labels, action_roles)
            ):
                with _open_image(source) as image:
                    width, height, frame_count = _validate_image(image, source)
                    total_frame_pixels += width * height * frame_count
                    if total_frame_pixels > MAX_TOTAL_FRAME_PIXELS:
                        raise PetpackInputError(
                            f"所有动画解码后的总像素不能超过 {MAX_TOTAL_FRAME_PIXELS:,}。"
                        )

                    frames: list[dict[str, object]] = []
                    frame_paths: list[Path] = []
                    visible_frames: list[bool] = []
                    action_directory = work / "assets" / f"action{action_index:03d}"
                    action_directory.mkdir(parents=True, exist_ok=True)

                    for frame_index in range(frame_count):
                        image.seek(frame_index)
                        image.load()
                        original_frame = image.convert("RGBA")
                        frame = original_frame
                        if remove_background or action_index in cleanup_indices:
                            frame = _remove_edge_background(frame, int(background_threshold))
                            # Never turn a visible animation frame into a completely
                            # transparent one. Some compressed WebP delta frames use
                            # colours close to their edge colour; aggressive cleanup
                            # can otherwise erase the entire pose.
                            if (
                                frame.getchannel("A").getbbox() is None
                                and original_frame.getchannel("A").getbbox() is not None
                                and _has_visible_contrast(
                                    original_frame, int(background_threshold)
                                )
                            ):
                                frame = original_frame

                        frame_name = f"frame{frame_index:03d}.png"
                        frame_path = action_directory / frame_name
                        frame.save(frame_path, format="PNG", optimize=True)

                        duration = _duration_for(image, 800 if frame_count == 1 else 60)
                        relative = frame_path.relative_to(work).as_posix()
                        frames.append({"file": relative, "duration": duration})
                        frame_paths.append(frame_path)
                        visible_frames.append(frame.getchannel("A").getbbox() is not None)

                    if not any(visible_frames):
                        raise PetpackInputError(f"{source.name} 没有可见画面。")

                    # Empty padding frames at the beginning or end interrupt the
                    # visual seam of an otherwise looping animation. Keep internal
                    # transparent frames (they may be intentional), but trim the
                    # invisible edges before writing the manifest.
                    first_visible = visible_frames.index(True)
                    last_visible = len(visible_frames) - 1 - visible_frames[::-1].index(True)
                    for unused_path in frame_paths[:first_visible] + frame_paths[last_visible + 1 :]:
                        unused_path.unlink()
                    frames = frames[first_visible : last_visible + 1]
                    frame_paths = frame_paths[first_visible : last_visible + 1]

                    # A very long final-frame delay looks like playback stopped.
                    # Preserve natural pauses inside the animation while keeping
                    # the loop boundary responsive.
                    if len(frames) > 1:
                        frames[-1]["duration"] = min(int(frames[-1]["duration"]), 200)

                    if icon_source is None:
                        icon_source = frame_paths[0]
                    for frame_path in frame_paths:
                        identity.update(frame_path.read_bytes())

                    actions.append(
                        {
                            "name": label,
                            "role": role,
                            "loop": True,
                            "frames": frames,
                        }
                    )

            if icon_source is None:
                raise PetpackServiceError("没有生成可用的桌宠帧。")

            with Image.open(icon_source) as first_frame:
                icon = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
                contained = ImageOps.contain(first_frame.convert("RGBA"), (232, 232), Image.Resampling.LANCZOS)
                icon.alpha_composite(contained, ((256 - contained.width) // 2, (256 - contained.height) // 2))
                icon.save(work / "icon.png", format="PNG", optimize=True)

            manifest = {
                "formatVersion": FORMAT_VERSION,
                "id": identity.hexdigest()[:32],
                "name": name,
                "defaultSize": int(default_size),
                "icon": "icon.png",
                "actions": actions,
            }
            (work / "pet.json").write_text(
                json.dumps(manifest, ensure_ascii=False, separators=(",", ":")),
                encoding="utf-8",
            )

            temporary_output = work / (_safe_filename(name) + ".petpack")
            with zipfile.ZipFile(
                temporary_output,
                mode="w",
                compression=zipfile.ZIP_DEFLATED,
                compresslevel=6,
                allowZip64=False,
            ) as archive:
                archive.write(work / "pet.json", "pet.json")
                archive.write(work / "icon.png", "icon.png")
                for action in actions:
                    for frame in action["frames"]:  # type: ignore[index]
                        relative = str(frame["file"])  # type: ignore[index]
                        archive.write(work / relative, relative)

            if temporary_output.stat().st_size > MAX_PACK_BYTES:
                raise PetpackInputError(
                    f"生成后的资源包超过 {MAX_PACK_BYTES // 1024 // 1024}MB，请减少帧数或图片尺寸。"
                )
            shutil.copyfile(temporary_output, output)
    except PetpackError:
        raise
    except OSError as error:
        raise PetpackServiceError("生成服务暂时无法写入资源包。") from error

    return output


def _parse_arguments(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="把图片或动画打包成跨平台 .petpack 桌宠资源包。")
    parser.add_argument("--image", action="append", required=True, help="图片路径，可重复 1～48 次")
    parser.add_argument("--label", action="append", default=[], help="动作名称")
    parser.add_argument("--role", action="append", default=[], help="idle/click/drag/sleep/custom")
    parser.add_argument("--name", default="我的桌宠", help="桌宠名称")
    parser.add_argument("--size", type=int, default=120, help="默认尺寸，72～320")
    parser.add_argument("--remove-background", action="store_true", help="移除与图片边缘连通的纯色背景")
    parser.add_argument(
        "--remove-background-index",
        action="append",
        type=int,
        default=[],
        help="仅为指定动作去背景，可重复；动作序号从 1 开始",
    )
    parser.add_argument("--background-threshold", type=int, default=32, help="去背景颜色容差，0～96")
    parser.add_argument("--out", required=True, help="输出 .petpack 路径")
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    arguments = _parse_arguments(argv)
    try:
        output = build_petpack(
            arguments.image,
            arguments.out,
            labels=arguments.label,
            roles=arguments.role,
            pet_name=arguments.name,
            default_size=arguments.size,
            remove_background=arguments.remove_background,
            remove_background_indices=[index - 1 for index in arguments.remove_background_index],
            background_threshold=arguments.background_threshold,
        )
    except PetpackInputError as error:
        print(str(error), file=sys.stderr)
        return 2
    except PetpackServiceError as error:
        print(str(error), file=sys.stderr)
        return 3
    except PetpackError as error:
        print(str(error), file=sys.stderr)
        return 3
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
