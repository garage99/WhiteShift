from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QEvent, QPointF, QSettings, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel,
    QGraphicsPixmapItem, QGraphicsScene, QGraphicsView, QListWidget,
    QMainWindow, QMessageBox, QPushButton, QSlider, QSplitter, QVBoxLayout,
    QWidget,
)

try:
    from .core import (
        ConvertedImage, convert_image, default_cmyk_profile, is_cmyk_profile,
        output_name, save_converted,
    )
except ImportError:  # Direct script execution and PyInstaller entry point.
    try:
        from png_black_converter.core import (
            ConvertedImage, convert_image, default_cmyk_profile, is_cmyk_profile,
            output_name, save_converted,
        )
    except ImportError:
        from core import (
            ConvertedImage, convert_image, default_cmyk_profile, is_cmyk_profile,
            output_name, save_converted,
        )


STYLE = """
QWidget#appRoot { background: #f3f5f8; color: #20242b; font-size: 13px; }
QWidget#settingsPanel, QFrame#previewCard {
    background: #ffffff; border: 1px solid #d9dee7; border-radius: 10px;
}
QLabel#previewTitle { font-size: 15px; font-weight: 700; color: #252a32; }
QListWidget {
    background: #f8f9fb; border: 1px solid #e5e8ee; border-radius: 6px;
    padding: 4px; outline: none;
}
QListWidget::item { min-height: 30px; padding: 3px 7px; border-radius: 4px; }
QListWidget::item:selected { color: #ffffff; background: #316fe8; }
QPushButton { min-height: 32px; padding: 0 13px; border-radius: 7px; font-weight: 600; }
QPushButton#secondaryButton { color: #26303d; background: #ffffff; border: 1px solid #c7cfdb; }
QPushButton#secondaryButton:hover { background: #f4f7fb; border-color: #9eabc0; }
QPushButton#primaryButton { color: #ffffff; background: #316fe8; border: 1px solid #2864d8; }
QPushButton#primaryButton:hover { background: #2864d8; }
QPushButton#resetButton { color: #a23535; background: #fff7f7; border: 1px solid #d9a6a6; }
QPushButton#resetButton:hover { background: #ffe9e9; border-color: #b85c5c; }
QSlider::groove:horizontal { height: 4px; border-radius: 2px; background: #d9dfe8; }
QSlider::sub-page:horizontal { background: #4f7ee8; border-radius: 2px; }
QSlider::handle:horizontal {
    width: 16px; margin: -6px 0; border-radius: 8px;
    background: #ffffff; border: 2px solid #4f7ee8;
}
QGraphicsView { border: 1px solid #e5e8ee; border-radius: 6px; }
"""


class DropList(QListWidget):
    files_dropped = Signal(list)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setToolTip("PNG、JPEG、PSDファイルをここへドロップ")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        self.files_dropped.emit(paths)
        event.acceptProposedAction()


class PreviewView(QGraphicsView):
    center_changed = Signal(object)
    wheel_zoom = Signal(int)

    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.item = QGraphicsPixmapItem()
        self.scene.addItem(self.item)
        self._zoom = 1.0
        self._syncing = False
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setBackgroundBrush(self._checkerboard())
        self.horizontalScrollBar().valueChanged.connect(self._center_moved)
        self.verticalScrollBar().valueChanged.connect(self._center_moved)

    @staticmethod
    def _checkerboard():
        tile = QPixmap(32, 32)
        tile.fill(QColor("#ebebeb"))
        painter = QPainter(tile)
        painter.fillRect(0, 0, 16, 16, QColor("#989898"))
        painter.fillRect(16, 16, 16, 16, QColor("#989898"))
        painter.end()
        return QBrush(tile)

    def set_image(self, image: Image.Image | None):
        if image is None:
            self.item.setPixmap(QPixmap())
            return
        data = image.tobytes("raw", "RGBA")
        qimage = QImage(data, image.width, image.height, image.width * 4, QImage.Format_RGBA8888).copy()
        self.item.setPixmap(QPixmap.fromImage(qimage))
        self.scene.setSceneRect(self.item.boundingRect())
        self._apply_zoom()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_zoom()

    def set_zoom(self, percent: int):
        center = self.mapToScene(self.viewport().rect().center())
        self._zoom = percent / 100.0
        self._apply_zoom(center)

    def _apply_zoom(self, center: QPointF | None = None):
        if self.item.pixmap().isNull():
            return
        self._syncing = True
        self.resetTransform()
        self.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
        self.scale(self._zoom, self._zoom)
        self.centerOn(center or self.scene.sceneRect().center())
        self._syncing = False

    def set_center(self, center: QPointF):
        self._syncing = True
        self.centerOn(center)
        self._syncing = False

    def _center_moved(self, *_):
        if not self._syncing and not self.item.pixmap().isNull():
            self.center_changed.emit(self.mapToScene(self.viewport().rect().center()))

    def wheelEvent(self, event):
        delta = event.angleDelta().y() or event.pixelDelta().y()
        if delta:
            self.wheel_zoom.emit(1 if delta > 0 else -1)
        event.accept()


class Preview(QFrame):
    def __init__(self, title: str):
        super().__init__()
        self.setObjectName("previewCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 12)
        heading = QLabel(title)
        heading.setObjectName("previewTitle")
        layout.addWidget(heading)
        self.view = PreviewView()
        self.view.setMinimumSize(280, 260)
        layout.addWidget(self.view, 1)

    def set_image(self, image: Image.Image | None):
        self.view.set_image(image)

    def set_zoom(self, percent: int):
        self.view.set_zoom(percent)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WhiteShift")
        self.resize(1400, 820)
        self.setMinimumSize(1000, 650)
        self.settings = QSettings("PNGTools", "WhiteToNearWhite")
        self.paths: list[Path] = []
        self.converted: dict[Path, ConvertedImage] = {}

        self.list = DropList()
        self.list.files_dropped.connect(self.add_files)
        self.list.currentRowChanged.connect(self.update_preview)
        choose = QPushButton("PNG / JPEG / PSDを選択")
        choose.setObjectName("secondaryButton")
        choose.clicked.connect(self.choose_files)
        remove = QPushButton("選択を削除")
        remove.setObjectName("resetButton")
        remove.clicked.connect(self.remove_selected)
        self.toggle = QCheckBox("変更箇所をシアンで確認")
        self.toggle.setChecked(True)
        self.toggle.toggled.connect(self.update_preview)
        self.output_mode = QComboBox()
        self.output_mode.addItem("RGB（PNG）", "RGB")
        self.output_mode.addItem("CMYK（PSD）", "CMYK")
        saved_mode = self.settings.value("outputMode", "RGB")
        self.output_mode.setCurrentIndex(max(0, self.output_mode.findData(saved_mode)))
        self.output_mode.currentIndexChanged.connect(self._output_mode_changed)
        detected_profile = default_cmyk_profile()
        saved_profile = self.settings.value(
            "cmykProfile", str(detected_profile) if detected_profile else ""
        )
        self.cmyk_profile = Path(saved_profile)
        self.profile_label = QLabel()
        self.profile_label.setWordWrap(True)
        profile_button = QPushButton("CMYKプロファイルを選択")
        profile_button.setObjectName("secondaryButton")
        profile_button.clicked.connect(self.choose_cmyk_profile)
        self.profile_button = profile_button
        export = QPushButton("書き出し")
        export.setObjectName("primaryButton")
        export.clicked.connect(self.export_all)
        self.status = QLabel("PNG、JPEG、PSDをドロップするか選択してください")

        left = QWidget()
        left.setObjectName("settingsPanel")
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("ファイル一覧（複数可）"))
        left_layout.addWidget(self.list)
        left_layout.addWidget(choose)
        left_layout.addWidget(remove)
        left_layout.addWidget(QLabel("出力カラーモード"))
        left_layout.addWidget(self.output_mode)
        left_layout.addWidget(self.profile_button)
        left_layout.addWidget(self.profile_label)
        left_layout.addWidget(export)

        previews = QWidget()
        preview_layout = QVBoxLayout(previews)
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("ズーム"))
        self.zoom = QSlider(Qt.Horizontal)
        self.zoom.setRange(100, 800)
        self.zoom.setSingleStep(25)
        self.zoom.setPageStep(100)
        self.zoom.setValue(100)
        self.zoom.setFixedWidth(220)
        self.zoom_label = QLabel("100%")
        toolbar.addWidget(self.zoom)
        toolbar.addWidget(self.zoom_label)
        toolbar.addStretch()
        toolbar.addWidget(QLabel("画像をドラッグして移動・ホイールでズーム"))
        panes = QHBoxLayout()
        self.before = Preview("元画像（72 dpi相当）")
        self.after = Preview("処理後（72 dpi相当）")
        panes.addWidget(self.before)
        panes.addWidget(self.after)
        preview_layout.addLayout(toolbar)
        preview_layout.addLayout(panes)
        preview_layout.addWidget(self.toggle)
        preview_layout.addWidget(self.status)

        splitter = QSplitter()
        splitter.addWidget(left)
        splitter.addWidget(previews)
        splitter.setSizes([270, 1130])
        splitter.setStretchFactor(1, 1)
        root = QWidget()
        root.setObjectName("appRoot")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(14, 14, 14, 10)
        root_layout.addWidget(splitter)
        self.setCentralWidget(root)
        self.setAcceptDrops(True)
        for widget in self.findChildren(QWidget):
            widget.setAcceptDrops(True)
        QApplication.instance().installEventFilter(self)
        self.zoom.valueChanged.connect(self._zoom_changed)
        self.before.view.wheel_zoom.connect(self._wheel_zoom)
        self.after.view.wheel_zoom.connect(self._wheel_zoom)
        self.before.view.center_changed.connect(self.after.view.set_center)
        self.after.view.center_changed.connect(self.before.view.set_center)
        self.setStyleSheet(STYLE)
        self._output_mode_changed()

    def eventFilter(self, watched, event):
        if (
            isinstance(watched, QWidget)
            and watched.window() is self
            and event.type() in (QEvent.DragEnter, QEvent.DragMove, QEvent.Drop)
            and event.mimeData().hasUrls()
        ):
            paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
            if event.type() == QEvent.Drop:
                self.add_files(paths)
            event.acceptProposedAction()
            return True
        return super().eventFilter(watched, event)

    def _zoom_changed(self, value: int):
        self.zoom_label.setText(f"{value}%")
        self.before.set_zoom(value)
        self.after.set_zoom(value)

    def _wheel_zoom(self, direction: int):
        self.zoom.setValue(self.zoom.value() + direction * self.zoom.singleStep())

    def _output_mode_changed(self, *_):
        mode = self.output_mode.currentData()
        self.settings.setValue("outputMode", mode)
        is_cmyk = mode == "CMYK"
        self.profile_button.setVisible(is_cmyk)
        self.profile_label.setVisible(is_cmyk)
        self.profile_label.setText(
            f"ICC: {self.cmyk_profile.name}"
            if self.cmyk_profile.is_file()
            else "ICCプロファイルを選択してください"
        )
        self.update_preview()

    def choose_cmyk_profile(self):
        start = str(self.cmyk_profile.parent if self.cmyk_profile.parent.exists() else Path.home())
        filename, _ = QFileDialog.getOpenFileName(
            self, "CMYK ICCプロファイルを選択", start, "ICCプロファイル (*.icc *.icm)"
        )
        if filename:
            if not is_cmyk_profile(filename):
                QMessageBox.warning(self, "選択不可", "CMYK用ICCプロファイルを選択してください。")
            else:
                self.cmyk_profile = Path(filename)
                self.settings.setValue("cmykProfile", filename)
                self._output_mode_changed()

    def choose_files(self):
        start = self.settings.value("lastInputDir", str(Path.home()))
        files, _ = QFileDialog.getOpenFileNames(
            self, "画像を選択", start, "対応画像 (*.png *.jpg *.jpeg *.psd)"
        )
        if files:
            self.settings.setValue("lastInputDir", str(Path(files[0]).parent))
            self.add_files(files)

    def add_files(self, files):
        rejected = []
        for raw in files:
            path = Path(raw).resolve()
            if path.suffix.lower() not in (".png", ".jpg", ".jpeg", ".psd") or not path.is_file():
                rejected.append(path.name)
                continue
            if path not in self.paths:
                try:
                    self.converted[path] = convert_image(path)
                except Exception as exc:
                    rejected.append(f"{path.name}（{exc}）")
                    continue
                self.paths.append(path)
                self.list.addItem(path.name)
        if self.paths and self.list.currentRow() < 0:
            self.list.setCurrentRow(0)
        if rejected:
            QMessageBox.warning(self, "読み込み不可", "次のファイルは追加できませんでした:\n" + "\n".join(rejected))

    def remove_selected(self):
        row = self.list.currentRow()
        if row < 0:
            return
        path = self.paths.pop(row)
        self.converted.pop(path, None)
        self.list.takeItem(row)
        if not self.paths:
            self.before.set_image(None)
            self.after.set_image(None)
            self.status.setText("PNG、JPEG、PSDをドロップするか選択してください")

    def update_preview(self, *_):
        row = self.list.currentRow()
        if not 0 <= row < len(self.paths):
            return
        path = self.paths[row]
        result = self.converted[path]
        self.before.set_image(result.original)
        self.after.set_image(result.preview if self.toggle.isChecked() else result.image)
        target = "CMYKの白 / #FEFEFE相当 → K1%" if result.color_mode == "CMYK" else "#FFFFFF / #FEFEFE → #FCFCFC"
        target += f"（{self.output_mode.currentText()}で保存）"
        self.status.setText(f"{path.name} — {target}: {result.changed_pixels:,} ピクセル")

    def export_all(self):
        if not self.paths:
            QMessageBox.information(self, "書き出し", "先にPNG、JPEGまたはPSDファイルを追加してください。")
            return
        mode = self.output_mode.currentData()
        if mode == "CMYK" and not self.cmyk_profile.is_file():
            QMessageBox.warning(self, "書き出し中止", "CMYK ICCプロファイルを選択してください。")
            return
        start = self.settings.value("lastOutputDir", str(self.paths[0].parent))
        folder = QFileDialog.getExistingDirectory(self, "保存先フォルダ", start)
        if not folder:
            return
        destination_dir = Path(folder)
        names = [output_name(p, mode) for p in self.paths]
        duplicates = sorted({name for name in names if names.count(name) > 1})
        if duplicates:
            QMessageBox.warning(self, "書き出し中止", "同じ出力名になる画像があります:\n" + "\n".join(duplicates))
            return
        conflicts = [name for name in names if (destination_dir / name).exists()]
        if conflicts:
            QMessageBox.warning(self, "書き出し中止", "元画像や既存ファイルは上書きしません。\n保存先に同名ファイルがあります:\n" + "\n".join(conflicts))
            return
        try:
            for path in self.paths:
                save_converted(
                    self.converted[path],
                    destination_dir / output_name(path, mode),
                    mode,
                    self.cmyk_profile if mode == "CMYK" else None,
                )
        except Exception as exc:
            QMessageBox.critical(self, "書き出しエラー", str(exc))
            return
        self.settings.setValue("lastOutputDir", str(destination_dir))
        QMessageBox.information(self, "完了", f"{len(self.paths)}枚を書き出しました。\n{destination_dir}")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("WhiteShift")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
