import tempfile
import unittest
from pathlib import Path

import numpy as np
import photoshopapi as psapi
from PIL import Image
from psd_tools import PSDImage
from psd_tools.constants import ColorMode, Resource

from png_black_converter.core import (
    ConvertedImage, _convert_psd_pixels, convert_image, default_cmyk_profile,
    is_cmyk_profile, output_name, save_converted,
)


class ConversionTest(unittest.TestCase):
    def test_default_profile_is_cmyk_when_available(self):
        profile = default_cmyk_profile()
        if profile:
            self.assertTrue(is_cmyk_profile(profile))

    def test_exact_white_and_alpha_only(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "sample.png"
            image = Image.new("RGBA", (4, 1))
            image.putdata([
                (255, 255, 255, 255),
                (254, 254, 254, 77),
                (255, 255, 254, 255),
                (253, 253, 253, 255),
            ])
            image.save(source, dpi=(72, 72))
            result = convert_image(source)
            self.assertEqual(result.changed_pixels, 2)
            expected = [
                (252, 252, 252, 255),
                (252, 252, 252, 77),
                (255, 255, 254, 255),
                (253, 253, 253, 255),
            ]
            self.assertEqual([result.image.getpixel((x, 0)) for x in range(4)], expected)
            self.assertEqual(result.preview.getpixel((1, 0)), (0, 255, 255, 255))
            destination = Path(directory) / output_name(source)
            save_converted(result, destination)
            with Image.open(destination) as saved:
                saved_rgba = saved.convert("RGBA")
                self.assertEqual([saved_rgba.getpixel((x, 0)) for x in range(4)], expected)
            self.assertEqual(destination.name, "sample-.png")
            with self.assertRaises(FileExistsError):
                save_converted(result, destination)

    def test_jpeg_white_conversion_and_output_name(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "sample.jpg"
            Image.new("RGB", (2, 2), (255, 255, 255)).save(source, quality=100)
            result = convert_image(source)
            destination = Path(directory) / output_name(source)
            save_converted(result, destination)

            self.assertEqual(result.source_format, "JPEG")
            self.assertEqual(result.changed_pixels, 4)
            self.assertEqual(destination.name, "sample-.png")
            with Image.open(destination) as saved:
                self.assertEqual(saved.format, "PNG")
                self.assertEqual(saved.mode, "RGB")
                self.assertEqual(saved.convert("RGB").getpixel((0, 0)), (252, 252, 252))

    def test_selected_output_modes(self):
        profile = Path(
            "/System/Library/ColorSync/Profiles/Generic CMYK Profile.icc"
        )
        if not profile.is_file():
            self.skipTest("CMYK test profile is not installed")
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "sample.jpg"
            Image.new("RGB", (2, 2), (255, 255, 255)).save(source, quality=100)
            result = convert_image(source)
            destination = Path(directory) / output_name(source, "CMYK")
            save_converted(result, destination, "CMYK", profile)

            psd = PSDImage.open(destination)
            self.assertEqual(destination.name, "sample-.psd")
            self.assertEqual(psd.color_mode, ColorMode.CMYK)
            self.assertTrue(psd.image_resources.get_data(Resource.ICC_PROFILE))

    def test_rgb_output_keeps_transparency(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "sample.png"
            Image.new("RGBA", (1, 1), (255, 255, 255, 77)).save(source)
            result = convert_image(source)
            destination = Path(directory) / output_name(source, "RGB")
            save_converted(result, destination, "RGB")
            with Image.open(destination) as saved:
                self.assertEqual(saved.mode, "RGBA")
                self.assertEqual(saved.getpixel((0, 0)), (252, 252, 252, 77))

    def test_psd_rgb_and_cmyk_exact_white(self):
        rgb = np.array(
            [[[255, 255, 255], [254, 254, 254], [255, 255, 254]]], dtype=np.uint8
        )
        converted, mask = _convert_psd_pixels(
            rgb, "RGB", np.array([[0, 255, 255]], dtype=np.uint8)
        )
        self.assertEqual(mask.tolist(), [[False, True, False]])
        self.assertEqual(
            converted.tolist(), [[[255, 255, 255], [252, 252, 252], [255, 255, 254]]]
        )

        cmyk = np.array([[[0, 0, 0, 0], [0, 0, 0, 1]]], dtype=np.uint8)
        converted, mask = _convert_psd_pixels(cmyk, "CMYK", np.array([[128, 255]], dtype=np.uint8))
        self.assertEqual(mask.tolist(), [[True, True]])
        self.assertEqual(converted.tolist(), [[[0, 0, 0, 3], [0, 0, 0, 3]]])

    def test_flat_psd_write_preserves_alpha_channel(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "sample-.psd"
            channels = np.array([[[254]], [[254]], [[254]]], dtype=np.uint8)
            alpha = np.array([[77]], dtype=np.uint8)
            preview = Image.new("RGBA", (1, 1), (254, 254, 254, 77))
            converted = ConvertedImage(
                preview, preview, preview, 1, {}, "PSD", "RGB", channels, alpha
            )
            save_converted(converted, destination)
            document = psapi.LayeredFile_8bit.read(str(destination))
            layer = document.flat_layers[0]
            self.assertEqual(layer.get_image_data()[0].tolist(), [[254]])
            self.assertEqual(layer.get_image_data()[-1].tolist(), [[77]])
            self.assertEqual((layer.center_x, layer.center_y), (0.5, 0.5))
            self.assertEqual(len(document.flat_layers), 1)
            saved_layer = PSDImage.open(destination)[0]
            self.assertEqual(saved_layer.bbox, (0, 0, 1, 1))
            self.assertEqual(saved_layer.fill_opacity, 255)
            self.assertGreaterEqual(
                min(PSDImage.open(destination).topil().getpixel((0, 0))), 253
            )

    def test_cmyk_psd_write_uses_photoshop_channel_values(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "sample-.psd"
            channels = np.array([[[0]], [[0]], [[0]], [[3]]], dtype=np.uint8)
            alpha = np.array([[255]], dtype=np.uint8)
            preview = Image.new("RGBA", (1, 1), (252, 252, 252, 255))
            converted = ConvertedImage(
                preview, preview, preview, 1, {}, "PSD", "CMYK", channels, alpha
            )
            save_converted(converted, destination)
            layer = psapi.LayeredFile_8bit.read(str(destination)).flat_layers[0]
            data = layer.get_image_data()
            self.assertEqual([data[i][0, 0] for i in range(4)], [255, 255, 255, 252])


if __name__ == "__main__":
    unittest.main()
