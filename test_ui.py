import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PIL import Image
from PySide6.QtCore import QMimeData, QPointF, Qt, QUrl
from PySide6.QtGui import QDropEvent
from PySide6.QtWidgets import QApplication

from png_black_converter.app import MainWindow
from png_black_converter.theme import ACCENT, DARK, LIGHT, apply_theme


class PreviewTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_two_previews_share_zoom_and_center(self):
        window = MainWindow()
        image = Image.new("RGBA", (800, 1200), (255, 255, 255, 0))
        window.before.set_image(image)
        window.after.set_image(image)
        window.zoom.setValue(200)
        center = QPointF(300, 700)
        window.before.view.set_center(center)
        window.after.view.set_center(center)

        self.assertEqual(window.before.view.sceneRect(), window.after.view.sceneRect())
        self.assertAlmostEqual(
            window.before.view.transform().m11(),
            window.after.view.transform().m11(),
        )
        before_center = window.before.view.mapToScene(window.before.view.viewport().rect().center())
        after_center = window.after.view.mapToScene(window.after.view.viewport().rect().center())
        self.assertAlmostEqual(before_center.x(), after_center.x(), places=1)
        self.assertAlmostEqual(before_center.y(), after_center.y(), places=1)
        window.close()

    def test_jpeg_drop_works_over_preview(self):
        window = MainWindow()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "sample.jpg"
            Image.new("RGB", (2, 2), (255, 255, 255)).save(path, quality=100)
            mime = QMimeData()
            mime.setUrls([QUrl.fromLocalFile(str(path))])
            event = QDropEvent(
                QPointF(10, 10), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier
            )

            handled = window.eventFilter(window.after.view.viewport(), event)

            self.assertTrue(handled)
            self.assertEqual(window.paths, [path.resolve()])
        window.close()

    def test_output_mode_controls(self):
        window = MainWindow()
        window.output_mode.setCurrentIndex(window.output_mode.findData("CMYK"))
        self.assertTrue(window.profile_button.isVisibleTo(window))
        window.output_mode.setCurrentIndex(window.output_mode.findData("RGB"))
        self.assertFalse(window.profile_button.isVisible())
        window.close()

    def test_theme_lives_at_application_level(self):
        window = MainWindow()
        # Widgets carry object names only; all styling comes from theme.py.
        self.assertFalse(window.styleSheet())
        self.assertEqual(window.before.objectName(), "previewCard")
        window.close()

    def test_theme_has_light_and_dark_variants(self):
        try:
            apply_theme(self.app, dark=False)
            self.assertIn(ACCENT, self.app.styleSheet())
            self.assertIn(LIGHT["window"], self.app.styleSheet())
            apply_theme(self.app, dark=True)
            self.assertIn(DARK["window"], self.app.styleSheet())
            self.assertNotIn(LIGHT["window"], self.app.styleSheet())
        finally:
            self.app.setStyleSheet("")

    def test_file_count_badge(self):
        window = MainWindow()
        with tempfile.TemporaryDirectory() as folder:
            for name in ("a.png", "b.png"):
                Image.new("RGBA", (2, 2), (255, 255, 255, 255)).save(Path(folder) / name)
            window.add_files([str(Path(folder) / n) for n in ("a.png", "b.png")])
            self.assertEqual(window.count_badge.text(), "2")
            window.remove_selected()
            self.assertEqual(window.count_badge.text(), "1")
        window.close()


if __name__ == "__main__":
    unittest.main()
