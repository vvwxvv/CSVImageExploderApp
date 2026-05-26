import sys
import os
import csv
import time
import urllib.request
import urllib.error
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QMessageBox,
    QFileDialog,
    QProgressBar,
)
from PyQt5.QtCore import Qt, QPoint, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap


# ──────────────────────────────────────────────────────────────────────────────
# Core logic  (no pandas — stdlib only)
# ──────────────────────────────────────────────────────────────────────────────

def _sanitize(name: str) -> str:
    for ch in '<>:"/\\|?*':
        name = name.replace(ch, '_')
    return name.strip('. ').lower()


def _build_folder_name(row: dict, headers: list, separator: str) -> str:
    parts = [_sanitize(row.get(h, '').strip()) for h in headers]
    parts = [p for p in parts if p]
    return separator.join(parts) if parts else None


def _collect_image_urls(row: dict, image_prefix: str) -> list:
    img_cols = sorted(
        [c for c in row if c.startswith(image_prefix)],
        key=lambda c: int(c[len(image_prefix):])
        if c[len(image_prefix):].isdigit() else 999999,
    )
    return [
        str(row[col]).strip()
        for col in img_cols
        if str(row.get(col, '')).strip() not in ('', 'nan')
    ]


def _guess_ext(url: str, content_type: str = '') -> str:
    path = url.split('?')[0].rstrip('/')
    ext  = os.path.splitext(path)[1].lower()
    if ext in ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff'):
        return ext
    ct = content_type.lower()
    if 'jpeg' in ct or 'jpg' in ct: return '.jpg'
    if 'png'  in ct:                return '.png'
    if 'gif'  in ct:                return '.gif'
    if 'webp' in ct:                return '.webp'
    return '.jpg'


def _download_one(url: str, dest_base: str, retries: int = 2) -> bool:
    headers = {'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0 Safari/537.36'
    )}
    req = urllib.request.Request(url, headers=headers)
    for attempt in range(1, retries + 2):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = resp.read()
                ext  = _guess_ext(url, resp.headers.get('Content-Type', ''))
            with open(dest_base + ext, 'wb') as f:
                f.write(data)
            return True
        except Exception:
            if attempt <= retries:
                time.sleep(1)
    return False


def download_images_to_folders(
    csv_file:     str,
    headers:      list,
    base_path:    str = '.',
    separator:    str = '_',
    image_prefix: str = 'AllImage_',
    max_workers:  int = 5,
    progress_cb=None,   # callable(current_row, total_rows)
) -> dict:
    """
    WORKFLOW per CSV row
    ─────────────────────
    1. Build folder name  →  sanitize(Header1) + sep + sanitize(Header2)
    2. Create folder      →  base_path / folder_name /
    3. Collect URLs       →  all non-empty AllImage_* columns
    4. Download images    →  folder / 1.jpg, 2.jpg, …  (parallel)
    """
    if not isinstance(headers, (list, tuple)) or not (1 <= len(headers) <= 2):
        raise ValueError("'headers' must be a list of 1 or 2 column names.")

    Path(base_path).mkdir(parents=True, exist_ok=True)

    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        csv_cols = reader.fieldnames or []
        missing  = [h for h in headers if h not in csv_cols]
        if missing:
            raise ValueError(
                f"Column(s) not found in CSV: {missing}\n"
                f"Available columns: {csv_cols}"
            )
        rows = list(reader)

    total_folders    = 0
    total_downloaded = 0
    total_failed     = 0

    for idx, row in enumerate(rows):
        if progress_cb:
            progress_cb(idx + 1, len(rows))

        folder_name = _build_folder_name(row, headers, separator)
        if not folder_name:
            continue

        folder_path = os.path.join(base_path, folder_name)
        Path(folder_path).mkdir(parents=True, exist_ok=True)
        total_folders += 1

        urls = _collect_image_urls(row, image_prefix)
        if not urls:
            continue

        tasks = {
            url: os.path.join(folder_path, str(i + 1))
            for i, url in enumerate(urls)
        }

        ok = fail = 0
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {
                pool.submit(_download_one, url, dest): url
                for url, dest in tasks.items()
            }
            for future in as_completed(futures):
                if future.result(): ok   += 1
                else:               fail += 1

        total_downloaded += ok
        total_failed     += fail

    return {
        'folders_created':   total_folders,
        'images_downloaded': total_downloaded,
        'images_failed':     total_failed,
        'total_rows':        len(rows),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Background worker  (keeps UI responsive during download)
# ──────────────────────────────────────────────────────────────────────────────

class DownloadWorker(QThread):
    progress  = pyqtSignal(int, int)   # (current, total)
    finished  = pyqtSignal(dict)       # result dict
    error     = pyqtSignal(str)        # error message

    def __init__(self, kwargs: dict):
        super().__init__()
        self.kwargs = kwargs

    def run(self):
        try:
            result = download_images_to_folders(
                **self.kwargs,
                progress_cb=lambda cur, tot: self.progress.emit(cur, tot),
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


# ──────────────────────────────────────────────────────────────────────────────
# Stylesheet
# ──────────────────────────────────────────────────────────────────────────────

APP_STYLESHEET = """
    QWidget {
        font-family: 'Arial';
        background-color: transparent;
        border: 2px solid #CDEBF0;
        border-radius: 20px;
    }
    QPushButton {
        background-color: #CDEBF0;
        color: black;
        font-weight: bold;
        border-radius: 8px;
        border: none;
        padding: 10px;
        margin: 10px;
    }
    QPushButton:hover  { background-color: #BEE0E8; }
    QPushButton:disabled { background-color: #e0e0e0; color: #999; }

    QLabel {
        border: none;
        border-radius: 0px;
    }
    QLabel#Logo        { background-color: transparent; }
    QLabel#PathLabel   {
        color: white; font-size: 20px; font-weight: bold;
        margin: 0 12px 4px 12px;
        background: transparent; border: none;
    }
    QLabel#SectionTitle {
        color: white; font-size: 20px; font-weight: bold;
        margin: 6px 12px 0 12px;
        background: transparent; border: none;
    }
    QLineEdit {
        border: 2px solid #ccc;
        border-radius: 8px;
        padding: 8px;
        margin: 6px 10px;
        color: black;
        background-color: white;
    }
    QProgressBar {
        border: 2px solid #CDEBF0;
        border-radius: 8px;
        background-color: #f0f0f0;
        margin: 6px 10px;
        height: 18px;
        text-align: center;
        color: black;
    }
    QProgressBar::chunk { background-color: #CDEBF0; border-radius: 6px; }

    QMessageBox {
        background-color: #CDEBF0;
        color: black; font-size: 16px;
        border: 2px solid #BEE0E8; border-radius: 12px;
    }
    QMessageBox QPushButton {
        background-color: #CDEBF0; color: black; font-weight: bold;
        border: 2px solid #BEE0E8; border-radius: 8px;
        padding: 8px 16px; font-size: 14px;
        min-width: 80px; min-height: 35px;
    }
    QMessageBox QPushButton:hover { background-color: #BEE0E8; }
"""


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def get_resource_path(relative_path: str) -> str:
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath('.')
    return os.path.join(base_path, relative_path)


class CloseButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__('✕', parent)
        self.setFixedSize(32, 32)
        self.setStyleSheet("""
            QPushButton {
                background-color: #f0a0a0; color: #800000;
                font-weight: bold; font-size: 14px;
                border-radius: 16px; border: none;
                padding: 0; margin: 4px;
            }
            QPushButton:hover { background-color: #e05555; color: white; }
        """)


# ──────────────────────────────────────────────────────────────────────────────
# Main window
# ──────────────────────────────────────────────────────────────────────────────

class ExplodeImagesApp(QWidget):

    def __init__(self):
        super().__init__()
        self.input_csv_path  = None
        self.output_dir_path = None
        self.worker          = None
        self.setMouseTracking(True)
        self.oldPos = self.pos()
        self._init_ui()

    # ── UI construction ───────────────────────────────────────────────────────

    def _init_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setObjectName('App')
        self.setStyleSheet(APP_STYLESHEET)

        root = QVBoxLayout(self)
        root.setContentsMargins(5, 5, 5, 5)
        root.setSpacing(2)

        # Title bar
        root.addLayout(self._make_title_bar())

        # Logo
        root.addWidget(self._make_logo())

        # ── Header 1 (required) ───────────────────────────────────────────
        h1_title = QLabel('Header 1 — column name (required)', self)
        h1_title.setObjectName('SectionTitle')
        root.addWidget(h1_title)

        self.header1_input = QLineEdit(self)
        self.header1_input.setPlaceholderText('e.g.  Title')
        root.addWidget(self.header1_input)

        # ── Header 2 (optional) ───────────────────────────────────────────
        h2_title = QLabel('Header 2 — column name (optional)', self)
        h2_title.setObjectName('SectionTitle')
        root.addWidget(h2_title)

        self.header2_input = QLineEdit(self)
        self.header2_input.setPlaceholderText('e.g.  Year')
        root.addWidget(self.header2_input)

        # ── Image prefix (optional) ───────────────────────────────────────
        prefix_title = QLabel('Image Column Prefix (optional)', self)
        prefix_title.setObjectName('SectionTitle')
        root.addWidget(prefix_title)

        self.image_prefix_input = QLineEdit(self)
        self.image_prefix_input.setPlaceholderText('default: AllImage_')
        root.addWidget(self.image_prefix_input)

        # ── Input CSV ─────────────────────────────────────────────────────
        self.csv_button = QPushButton('Select Input CSV File', self)
        self.csv_button.clicked.connect(self._select_input_csv)
        root.addWidget(self.csv_button)

        self.csv_label = QLabel('No file selected', self)
        self.csv_label.setObjectName('PathLabel')
        self.csv_label.setWordWrap(True)
        root.addWidget(self.csv_label)

        # ── Output directory ──────────────────────────────────────────────
        self.out_dir_button = QPushButton('Select Output Folder', self)
        self.out_dir_button.clicked.connect(self._select_output_directory)
        root.addWidget(self.out_dir_button)

        self.out_dir_label = QLabel('No folder selected', self)
        self.out_dir_label.setObjectName('PathLabel')
        self.out_dir_label.setWordWrap(True)
        root.addWidget(self.out_dir_label)

        # ── Progress bar ──────────────────────────────────────────────────
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        root.addWidget(self.progress_bar)

        # ── Start button ──────────────────────────────────────────────────
        self.start_button = QPushButton('Start Downloading', self)
        self.start_button.clicked.connect(self._run)
        root.addWidget(self.start_button)

        root.addStretch()
        self.setLayout(root)
        self.resize(540, 880)

    def _make_title_bar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        close_btn = CloseButton(self)
        close_btn.clicked.connect(self.close)
        bar.addWidget(close_btn, alignment=Qt.AlignRight)
        return bar

    def _make_logo(self) -> QLabel:
        logo = QLabel(self)
        cover_path = get_resource_path(os.path.join('static', 'cover.png'))
        pixmap = QPixmap(cover_path).scaled(500, 800)
        logo.setPixmap(pixmap)
        logo.setAlignment(Qt.AlignCenter)
        logo.setObjectName('Logo')
        return logo

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _select_input_csv(self):
        path, _ = QFileDialog.getOpenFileName(
            self, 'Select Input CSV File', '', 'CSV Files (*.csv)'
        )
        if path:
            self.input_csv_path = path
            self.csv_label.setText(os.path.basename(path))

    def _select_output_directory(self):
        path = QFileDialog.getExistingDirectory(self, 'Select Output Folder')
        if path:
            self.output_dir_path = path
            self.out_dir_label.setText(path)

    def _run(self):
        # ── Validation ────────────────────────────────────────────────────
        h1 = self.header1_input.text().strip()
        h2 = self.header2_input.text().strip()

        if not h1:
            QMessageBox.warning(self, 'Missing Input', 'Please enter at least Header 1.')
            return
        if not self.input_csv_path:
            QMessageBox.warning(self, 'Missing Input', 'Please select an input CSV file.')
            return
        if not self.output_dir_path:
            QMessageBox.warning(self, 'Missing Input', 'Please select an output folder.')
            return

        headers = [h1] + ([h2] if h2 else [])
        image_prefix = self.image_prefix_input.text().strip() or 'AllImage_'

        # ── Setup progress bar ────────────────────────────────────────────
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.start_button.setEnabled(False)
        self.start_button.setText('Downloading…')

        # ── Start worker thread ───────────────────────────────────────────
        self.worker = DownloadWorker({
            'csv_file':     self.input_csv_path,
            'headers':      headers,
            'base_path':    self.output_dir_path,
            'separator':    '_',
            'image_prefix': image_prefix,
            'max_workers':  5,
        })
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_progress(self, current: int, total: int):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.progress_bar.setFormat(f'Row {current} / {total}')

    def _on_finished(self, result: dict):
        self._reset_ui()
        QMessageBox.information(
            self,
            'Done',
            f"✓  Folders created   : {result['folders_created']}\n"
            f"✓  Images downloaded : {result['images_downloaded']}\n"
            f"✗  Images failed     : {result['images_failed']}\n\n"
            f"Saved to:\n{self.output_dir_path}",
        )

    def _on_error(self, message: str):
        self._reset_ui()
        QMessageBox.critical(self, 'Error', message)

    def _reset_ui(self):
        self.progress_bar.setVisible(False)
        self.start_button.setEnabled(True)
        self.start_button.setText('Start Downloading')

    # ── Window drag ───────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.oldPos = event.globalPos()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            delta = QPoint(event.globalPos() - self.oldPos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.oldPos = event.globalPos()

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
        event.accept()


# ──────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ExplodeImagesApp()
    window.show()
    sys.exit(app.exec_())
