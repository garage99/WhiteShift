from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import os
from pathlib import Path

import numpy as np
import photoshopapi as psapi
from PIL import Image, ImageCms, PngImagePlugin
from psd_tools import PSDImage
from psd_tools.composite import composite
from psd_tools.constants import ColorMode, Tag


@dataclass
class ConvertedImage:
    original: Image.Image
    image: Image.Image
    preview: Image.Image
    changed_pixels: int
    source_info: dict
    source_format: str = "PNG"
    color_mode: str = "RGB"
    psd_channels: np.ndarray | None = None
    psd_alpha: np.ndarray | None = None


def is_cmyk_profile(path: str | Path) -> bool:
    try:
        profile = ImageCms.getOpenProfile(str(path))
        return profile.profile.xcolor_space.strip() == "CMYK"
    except Exception:
        return False


def default_cmyk_profile() -> Path | None:
    folders = [
        Path("/System/Library/ColorSync/Profiles"),
        Path("/Library/ColorSync/Profiles"),
    ]
    windows = os.environ.get("WINDIR")
    if windows:
        folders.insert(0, Path(windows) / "System32" / "spool" / "drivers" / "color")
    profiles = [
        path
        for folder in folders
        if folder.is_dir()
        for path in (*folder.glob("*.icc"), *folder.glob("*.icm"))
        if is_cmyk_profile(path)
    ]
    profiles.sort(key=lambda path: ("generic cmyk" not in path.name.lower(), path.name.lower()))
    return profiles[0] if profiles else None


def convert_image(path: str | Path) -> ConvertedImage:
    path = Path(path)
    if path.suffix.lower() == ".psd":
        return _convert_psd(path)

    source = Image.open(path)
    if source.format not in ("PNG", "JPEG"):
        source.close()
        raise ValueError("PNG、JPEG、PSD以外のファイルには対応していません。")

    source_format = source.format
    info = dict(source.info)
    rgba = source.convert("RGBA")
    source.close()
    pixels = bytearray(rgba.tobytes())
    preview_pixels = bytearray(pixels)
    changed = 0
    for i in range(0, len(pixels), 4):
        if pixels[i] == pixels[i + 1] == pixels[i + 2] and pixels[i] in (254, 255):
            pixels[i : i + 3] = b"\xfc\xfc\xfc"
            # Confirmation overlay must remain visible even when the source
            # pixel is fully transparent. Saved pixels use the original alpha.
            preview_pixels[i : i + 4] = b"\x00\xff\xff\xff"
            changed += 1

    size = rgba.size
    return ConvertedImage(
        rgba,
        Image.frombytes("RGBA", size, bytes(pixels)),
        Image.frombytes("RGBA", size, bytes(preview_pixels)),
        changed,
        info,
        source_format,
    )


def _convert_psd(path: Path) -> ConvertedImage:
    psd = PSDImage.open(path)
    if psd.depth != 8:
        raise ValueError("現在のベータ版は8bit PSDのみ対応しています。")
    if psd.color_mode not in (ColorMode.RGB, ColorMode.CMYK):
        raise ValueError("RGBまたはCMYKのPSDのみ対応しています。")

    mode = "CMYK" if psd.color_mode == ColorMode.CMYK else "RGB"
    rendered = psd.composite(ignore_preview=True, apply_icc=False)
    channels = np.asarray(rendered.convert(mode), dtype=np.uint8)
    backdrop = 0.0 if mode == "CMYK" else 1.0
    _, _, alpha = composite(psd, color=backdrop, alpha=0.0)
    alpha8 = np.rint(np.clip(alpha[..., 0] if alpha.ndim == 3 else alpha, 0, 1) * 255).astype(np.uint8)
    if rendered.mode == "RGBA":
        alpha8 = np.asarray(rendered.getchannel("A"), dtype=np.uint8)

    converted_channels, mask = _convert_psd_pixels(channels, mode, alpha8)
    if mode == "RGB":
        original = Image.fromarray(np.dstack((channels, alpha8)), "RGBA")
        result = Image.fromarray(np.dstack((converted_channels, alpha8)), "RGBA")
    else:
        original = _cmyk_preview(channels, alpha8)
        result = _cmyk_preview(converted_channels, alpha8)

    preview = np.array(result, copy=True)
    preview[mask] = (0, 255, 255, 255)
    info = {}
    try:
        with Image.open(path) as source:
            info = dict(source.info)
    except Exception:
        pass
    return ConvertedImage(
        original,
        result,
        Image.fromarray(preview, "RGBA"),
        int(mask.sum()),
        info,
        "PSD",
        mode,
        np.moveaxis(converted_channels, 2, 0),
        alpha8,
    )


def _convert_psd_pixels(
    channels: np.ndarray, mode: str, alpha: np.ndarray | None = None
) -> tuple[np.ndarray, np.ndarray]:
    converted = channels.copy()
    if mode == "RGB":
        mask = np.all(channels == channels[..., :1], axis=2) & np.isin(channels[..., 0], (254, 255))
        converted[mask] = 252
    else:
        mask = np.all(channels[..., :3] == 0, axis=2) & np.isin(channels[..., 3], (0, 1))
        converted[..., 3][mask] = 3  # 3/255 is Photoshop's 8bit K=1% step.
    if alpha is not None:
        mask &= alpha > 0
        converted[~mask] = channels[~mask]
    return converted, mask


def _cmyk_preview(channels: np.ndarray, alpha: np.ndarray) -> Image.Image:
    cmyk = Image.fromarray(channels, "CMYK")
    rgba = cmyk.convert("RGB").convert("RGBA")
    rgba.putalpha(Image.fromarray(alpha, "L"))
    return rgba


def output_name(path: str | Path, output_mode: str | None = None) -> str:
    path = Path(path)
    if output_mode:
        suffix = ".psd" if output_mode == "CMYK" else ".png"
    else:
        suffix = ".png" if path.suffix.lower() in (".jpg", ".jpeg") else path.suffix.lower()
    return f"{path.stem}-{suffix}"


def save_converted(
    converted: ConvertedImage,
    destination: str | Path,
    output_mode: str | None = None,
    cmyk_profile: str | Path | None = None,
) -> None:
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(destination)

    if output_mode == "CMYK":
        if not cmyk_profile:
            raise ValueError("CMYK ICCプロファイルを選択してください。")
        _save_as_cmyk(converted, destination, Path(cmyk_profile))
        return
    if output_mode == "RGB":
        _save_rgb_png(converted, destination)
        return

    if converted.source_format == "PSD":
        _save_psd(converted, destination)
        return

    info = converted.source_info
    pnginfo = PngImagePlugin.PngInfo()
    for key, value in info.items():
        if isinstance(value, str):
            pnginfo.add_text(key, value)

    kwargs = {"pnginfo": pnginfo}
    # RGBA already contains transparency; passing a palette transparency value
    # again is invalid after conversion.
    for key in ("icc_profile", "dpi", "exif"):
        if key in info:
            kwargs[key] = info[key]
    image = converted.image.convert("RGB") if converted.source_format == "JPEG" else converted.image
    image.save(destination, format="PNG", **kwargs)


def _embedded_profile(info: dict):
    data = info.get("icc_profile")
    if not data:
        return None
    try:
        return ImageCms.ImageCmsProfile(BytesIO(data))
    except Exception:
        return None


def _srgb_profile():
    return ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB"))


def _save_rgb_png(converted: ConvertedImage, destination: Path) -> None:
    image = converted.image.convert("RGB")
    if converted.color_mode == "CMYK" and converted.psd_channels is not None:
        source_profile = _embedded_profile(converted.source_info)
        if source_profile:
            cmyk = Image.fromarray(np.moveaxis(converted.psd_channels, 0, 2), "CMYK")
            image = ImageCms.profileToProfile(
                cmyk, source_profile, _srgb_profile(), outputMode="RGB"
            )
    alpha = converted.image.getchannel("A")
    if alpha.getextrema()[0] < 255:
        image.putalpha(alpha)
    info = dict(converted.source_info)
    info["icc_profile"] = _srgb_profile().tobytes()
    kwargs = {key: info[key] for key in ("icc_profile", "dpi", "exif") if key in info}
    image.save(destination, format="PNG", **kwargs)


def _save_as_cmyk(
    converted: ConvertedImage, destination: Path, profile_path: Path
) -> None:
    if not profile_path.is_file():
        raise ValueError("CMYK ICCプロファイルが見つかりません。")
    if not is_cmyk_profile(profile_path):
        raise ValueError("選択したICCプロファイルはCMYK用ではありません。")
    target_profile = ImageCms.getOpenProfile(str(profile_path))
    source_profile = _embedded_profile(converted.source_info)
    if converted.color_mode == "CMYK" and converted.psd_channels is not None:
        source = Image.fromarray(np.moveaxis(converted.psd_channels, 0, 2), "CMYK")
        source_profile = source_profile or target_profile
    else:
        source = converted.image.convert("RGB")
        source_profile = source_profile or _srgb_profile()
    cmyk = ImageCms.profileToProfile(
        source, source_profile, target_profile, outputMode="CMYK"
    )
    alpha = np.asarray(converted.image.getchannel("A"), dtype=np.uint8)
    info = dict(converted.source_info)
    info["icc_profile"] = profile_path.read_bytes()
    psd = ConvertedImage(
        converted.original,
        converted.image,
        converted.preview,
        converted.changed_pixels,
        info,
        "PSD",
        "CMYK",
        np.moveaxis(np.asarray(cmyk, dtype=np.uint8), 2, 0),
        alpha,
    )
    _save_psd(psd, destination)


def _save_psd(converted: ConvertedImage, destination: Path) -> None:
    assert converted.psd_channels is not None and converted.psd_alpha is not None
    height, width = converted.psd_alpha.shape
    mode = psapi.enum.ColorMode.cmyk if converted.color_mode == "CMYK" else psapi.enum.ColorMode.rgb
    channels = 255 - converted.psd_channels if converted.color_mode == "CMYK" else converted.psd_channels
    data = {i: np.ascontiguousarray(channel) for i, channel in enumerate(channels)}
    data[-1] = np.ascontiguousarray(converted.psd_alpha)
    document = psapi.LayeredFile_8bit(mode, width, height)
    layer = psapi.ImageLayer_8bit(
        data,
        "統合画像",
        width=width,
        height=height,
        color_mode=mode,
    )
    layer.center_x = width / 2
    layer.center_y = height / 2
    document.add_layer(layer)
    if "icc_profile" in converted.source_info:
        document.icc = list(converted.source_info["icc_profile"])
    if "dpi" in converted.source_info:
        document.dpi = float(converted.source_info["dpi"][0])
    document.write(str(destination))
    written = PSDImage.open(destination)
    written[0]._record.tagged_blocks.pop(Tag.BLEND_FILL_OPACITY, None)
    merged = written.composite(ignore_preview=True, color=1.0, alpha=1.0).convert(written.pil_mode)
    if converted.color_mode == "CMYK":
        merged = Image.merge("CMYK", tuple(channel.point(lambda value: 255 - value) for channel in merged.split()))
    written._record.image_data.set_data(
        [channel.tobytes() for channel in merged.split()], written._record.header
    )
    written.save(destination)
