import sys
import os
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
)
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QPixmap

import pandas as pd


# ──────────────────────────────────────────────────────────────────────────────
# Core logic
# ──────────────────────────────────────────────────────────────────────────────

def explode_image_rows_to_columns(
    input_csv: str,
    output_csv: str,
    image_prefix: str = "AllImage_",
    image_column_name: str = "ImageURL",
):
    df = pd.read_csv(input_csv, keep_default_na=False, dtype=str)

    image_cols = [c for c in df.columns if c.startswith(image_prefix)]
    image_cols.sort(
        key=lambda x: int(x.replace(image_prefix, ""))
        if x.replace(image_prefix, "").isdigit()
        else 999999
    )

    if not image_cols:
        raise ValueError(
            f'No image columns found with prefix "{image_prefix}".'
        )

    base_cols = [c for c in df.columns if c not in image_cols]
    output_rows = []

    for _, row in df.iterrows():
        base_data = {col: row[col] for col in base_cols}
        for img_col in image_cols:
            img_url = str(row[img_col]).strip()
            if img_url == "" or img_url.lower() == "nan":
                continue
            new_row = base_data.copy()
            new_row[image_column_name] = img_url
            output_rows.append(new_row)

    result_df = pd.DataFrame(output_rows)
    result_df.to_csv(output_csv, index=False, encoding="utf-8-sig")
    return len(result_df)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def get_resource_path(relative_path: str) -> str:
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)
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
    QPushButton:hover {
        background-color: #BEE0E8;
    }
    QLabel {
        border: none;
        border-radius: 0px;
    }
    QLabel#Logo {
        background-color: transparent;
    }
    QLabel#PathLabel {
        color: white;
        font-size: 20px;
        font-weight: bold;
        margin: 0 12px 4px 12px;
        background: transparent;
        border: none;
    }
    QLabel#SectionTitle {
        color: white;
        font-size: 20px;
        font-weight: bold;
        margin: 6px 12px 0 12px;
        background: transparent;
        border: none;
    }
    QLineEdit {
        border: 2px solid #ccc;
        border-radius: 8px;
        padding: 8px;
        margin: 6px 10px;
        color: black;
        background-color: white;
    }
    QMessageBox {
        background-color: #CDEBF0;
        color: black;
        font-size: 16px;
        border: 2px solid #BEE0E8;
        border-radius: 12px;
    }
    QMessageBox QPushButton {
        background-color: #CDEBF0;
        color: black;
        font-weight: bold;
        border: 2px solid #BEE0E8;
        border-radius: 8px;
        padding: 8px 16px;
        font-size: 14px;
        min-width: 80px;
        min-height: 35px;
    }
    QMessageBox QPushButton:hover {
        background-color: #BEE0E8;
    }
"""

# ──────────────────────────────────────────────────────────────────────────────
# Close button
# ──────────────────────────────────────────────────────────────────────────────

class CloseButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__("✕", parent)
        self.setFixedSize(32, 32)
        self.setStyleSheet(
            """
            QPushButton {
                background-color: #f0a0a0;
                color: #800000;
                font-weight: bold;
                font-size: 14px;
                border-radius: 16px;
                border: none;
                padding: 0;
                margin: 4px;
            }
            QPushButton:hover {
                background-color: #e05555;
                color: white;
            }
            """
        )


# ──────────────────────────────────────────────────────────────────────────────
# Main window
# ──────────────────────────────────────────────────────────────────────────────

class ExplodeImagesApp(QWidget):
    def __init__(self):
        super().__init__()
        self.input_csv_path = None
        self.output_directory = None
        self.setMouseTracking(True)
        self.oldPos = self.pos()
        self._init_ui()

    # ── UI construction ───────────────────────────────────────────────────────

    def _init_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setObjectName("App")
        self.setStyleSheet(APP_STYLESHEET)

        root = QVBoxLayout(self)
        root.setContentsMargins(5, 5, 5, 5)
        root.setSpacing(2)

        # Title bar
        root.addLayout(self._make_title_bar())

        # Logo — original size exactly as in your first code
        root.addWidget(self._make_logo())

        # ── Input CSV ─────────────────────────────────────────────────────
        self.csv_button = QPushButton("Select Input CSV File", self)
        self.csv_button.clicked.connect(self._select_input_csv)
        root.addWidget(self.csv_button)

        self.csv_label = QLabel("No file selected", self)
        self.csv_label.setObjectName("PathLabel")
        self.csv_label.setWordWrap(True)
        root.addWidget(self.csv_label)

        # ── Output directory ──────────────────────────────────────────────
        self.out_dir_button = QPushButton("Select Output Directory", self)
        self.out_dir_button.clicked.connect(self._select_output_directory)
        root.addWidget(self.out_dir_button)

        self.out_dir_label = QLabel("No directory selected", self)
        self.out_dir_label.setObjectName("PathLabel")
        self.out_dir_label.setWordWrap(True)
        root.addWidget(self.out_dir_label)

        # ── Optional parameters ───────────────────────────────────────────
        prefix_title = QLabel("Image Column Prefix", self)
        prefix_title.setObjectName("SectionTitle")
        root.addWidget(prefix_title)

        self.image_prefix_input = QLineEdit(self)
        self.image_prefix_input.setPlaceholderText("default: AllImage_")
        root.addWidget(self.image_prefix_input)

        col_name_title = QLabel("Output Image Column Name", self)
        col_name_title.setObjectName("SectionTitle")
        root.addWidget(col_name_title)

        self.image_col_name_input = QLineEdit(self)
        self.image_col_name_input.setPlaceholderText("default: ImageURL")
        root.addWidget(self.image_col_name_input)

        # ── Run button ────────────────────────────────────────────────────
        self.start_button = QPushButton("Start Exploding", self)
        self.start_button.clicked.connect(self._run)
        root.addWidget(self.start_button)

        root.addStretch()
        self.setLayout(root)
        self.resize(540, 880)  # restored to original height

    def _make_title_bar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        close_btn = CloseButton(self)
        close_btn.clicked.connect(self.close)
        bar.addWidget(close_btn, alignment=Qt.AlignRight)
        return bar

    def _make_logo(self) -> QLabel:
        logo = QLabel(self)
        cover_path = get_resource_path(os.path.join("static", "cover.png"))
        # ↓ restored exactly to your original one-liner
        pixmap = QPixmap(cover_path).scaled(500, 800)
        logo.setPixmap(pixmap)
        logo.setAlignment(Qt.AlignCenter)
        logo.setObjectName("Logo")
        return logo

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _select_input_csv(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Input CSV File", "", "CSV Files (*.csv)"
        )
        if path:
            self.input_csv_path = path
            self.csv_label.setText(os.path.basename(path))
            self.csv_label.setStyleSheet(
                "color: white; font-weight: bold;"
                "margin: 0 12px 4px 12px;"
                "background: transparent; border: none;"
            )

    def _select_output_directory(self):
        path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if path:
            self.output_directory = path
            self.out_dir_label.setText(path)
            self.out_dir_label.setStyleSheet(
                "color: white;font-weight: bold;"
                "margin: 0 12px 4px 12px;"
                "background: transparent; border: none;"
            )

    def _run(self):
        if not self.input_csv_path:
            QMessageBox.warning(self, "Missing Input", "Please select an input CSV file.")
            return
        if not self.output_directory:
            QMessageBox.warning(self, "Missing Output", "Please select an output directory.")
            return

        image_prefix = self.image_prefix_input.text().strip() or "AllImage_"
        image_column_name = self.image_col_name_input.text().strip() or "ImageURL"

        stem = os.path.splitext(os.path.basename(self.input_csv_path))[0]
        output_csv = os.path.join(self.output_directory, f"{stem}_images_rows.csv")

        try:
            total_rows = explode_image_rows_to_columns(
                input_csv=self.input_csv_path,
                output_csv=output_csv,
                image_prefix=image_prefix,
                image_column_name=image_column_name,
            )
            QMessageBox.information(
                self,
                "Success",
                f"Done! {total_rows} rows written.\n\nSaved to:\n{output_csv}",
            )
        except ValueError as e:
            QMessageBox.warning(self, "Error", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred:\n{str(e)}")

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
        event.accept()


# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ExplodeImagesApp()
    window.show()
    sys.exit(app.exec_())