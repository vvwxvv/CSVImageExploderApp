"""
download_images_to_folders.py
─────────────────────────────────────────────────────────────────────────────
WORKFLOW
────────
  1. Read the CSV.
  2. Validate that every requested header column exists.
  3. For each row:
       a. Build the folder name from Header 1 (+ Header 2 if given).
       b. Create the folder under base_path.
       c. Collect every non-empty AllImage_* URL in that row.
       d. Download each image into the folder, named 1.jpg, 2.jpg, …
  4. Print a per-row summary and a final totals line.

USAGE (standalone)
──────────────────
  python download_images_to_folders.py

USAGE (imported)
────────────────
  from download_images_to_folders import download_images_to_folders

  download_images_to_folders(
      csv_file   = "imag_zly.csv",
      headers    = ["Title", "Year"],   # 1 or 2 column names
      base_path  = "./output_folders",
      separator  = "_",
      image_prefix = "AllImage_",
  )
"""

import os
import csv
import time
import urllib.request
import urllib.error
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _sanitize(name: str) -> str:
    """Strip invalid filesystem characters and lowercase."""
    for ch in '<>:"/\\|?*':
        name = name.replace(ch, '_')
    return name.strip('. ').lower()


def _build_folder_name(row: dict, headers: list, separator: str) -> str:
    """Join sanitized values of the requested headers into a folder name."""
    parts = [_sanitize(row.get(h, '').strip()) for h in headers]
    parts = [p for p in parts if p]           # drop empty parts
    return separator.join(parts) if parts else None


def _collect_image_urls(row: dict, image_prefix: str) -> list:
    """
    Return all non-empty URL values whose column name starts with image_prefix,
    sorted numerically (AllImage_1 before AllImage_10).
    """
    img_cols = sorted(
        [c for c in row if c.startswith(image_prefix)],
        key=lambda c: int(c[len(image_prefix):])
              if c[len(image_prefix):].isdigit() else 999999,
    )
    urls = []
    for col in img_cols:
        url = str(row.get(col, '')).strip()
        if url and url.lower() != 'nan':
            urls.append(url)
    return urls


def _guess_extension(url: str, content_type: str = '') -> str:
    """Return a file extension based on URL path or Content-Type header."""
    # Try the URL path first
    path = url.split('?')[0].rstrip('/')
    ext = os.path.splitext(path)[1].lower()
    if ext in ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff'):
        return ext

    # Fall back to Content-Type
    ct = content_type.lower()
    if 'jpeg' in ct or 'jpg' in ct:
        return '.jpg'
    if 'png' in ct:
        return '.png'
    if 'gif' in ct:
        return '.gif'
    if 'webp' in ct:
        return '.webp'

    # Default
    return '.jpg'


def _download_one(url: str, dest_path: str, retries: int = 2) -> bool:
    """
    Download a single URL to dest_path.
    Returns True on success, False on failure.
    """
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/124.0 Safari/537.36'
        )
    }
    req = urllib.request.Request(url, headers=headers)

    for attempt in range(1, retries + 2):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = resp.read()
                content_type = resp.headers.get('Content-Type', '')

            # Adjust extension if needed
            base, _ = os.path.splitext(dest_path)
            ext = _guess_extension(url, content_type)
            final_path = base + ext

            with open(final_path, 'wb') as f:
                f.write(data)
            return True

        except (urllib.error.URLError, OSError) as err:
            if attempt <= retries:
                time.sleep(1)
            else:
                print(f"    [FAIL] {os.path.basename(dest_path)} — {err}")
                return False

    return False


# ─────────────────────────────────────────────────────────────────────────────
# Main public function
# ─────────────────────────────────────────────────────────────────────────────

def download_images_to_folders(
    csv_file:     str,
    headers:      list,
    base_path:    str  = '.',
    separator:    str  = '_',
    image_prefix: str  = 'AllImage_',
    max_workers:  int  = 5,
) -> dict:
    """
    Read a CSV, create one folder per row (named from the chosen headers),
    and download every AllImage_* URL in that row into its folder.

    Args:
        csv_file     : path to the CSV file
        headers      : list of 1 or 2 column names used to name each folder
        base_path    : root directory where folders are created
        separator    : character(s) joining the two header parts  (default '_')
        image_prefix : prefix of image URL columns                (default 'AllImage_')
        max_workers  : parallel download threads per row          (default 5)

    Returns:
        dict with keys 'folders_created', 'images_downloaded', 'images_failed'
    """

    # ── Validate arguments ───────────────────────────────────────────────────
    if not isinstance(headers, (list, tuple)) or not (1 <= len(headers) <= 2):
        raise ValueError("'headers' must be a list of 1 or 2 column names.")

    # ── Read CSV ─────────────────────────────────────────────────────────────
    Path(base_path).mkdir(parents=True, exist_ok=True)

    total_folders   = 0
    total_downloaded = 0
    total_failed    = 0

    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        csv_headers = reader.fieldnames or []

        # ── Validate header columns exist ────────────────────────────────────
        missing = [h for h in headers if h not in csv_headers]
        if missing:
            raise ValueError(
                f"Column(s) not found in CSV: {missing}\n"
                f"Available columns: {csv_headers}"
            )

        rows = list(reader)

    print(f"\n{'─'*60}")
    print(f"  CSV        : {csv_file}")
    print(f"  Headers    : {headers}")
    print(f"  Base path  : {base_path}")
    print(f"  Separator  : '{separator}'")
    print(f"  Img prefix : {image_prefix}")
    print(f"  Total rows : {len(rows)}")
    print(f"{'─'*60}\n")

    # ── Process each row ─────────────────────────────────────────────────────
    for row_num, row in enumerate(rows, start=2):

        # STEP 1 — Build folder name
        folder_name = _build_folder_name(row, headers, separator)
        if not folder_name:
            print(f"[SKIP] Row {row_num} — no usable value in {headers}")
            continue

        # STEP 2 — Create folder
        folder_path = os.path.join(base_path, folder_name)
        Path(folder_path).mkdir(parents=True, exist_ok=True)
        total_folders += 1
        print(f"[FOLDER] {folder_path}")

        # STEP 3 — Collect image URLs
        urls = _collect_image_urls(row, image_prefix)
        if not urls:
            print(f"  (no images found in row {row_num})\n")
            continue

        print(f"  Downloading {len(urls)} image(s)…")

        # STEP 4 — Download images in parallel
        # Build (url, dest_path) pairs — extension corrected after download
        tasks = {
            url: os.path.join(folder_path, f"{idx + 1}")
            for idx, url in enumerate(urls)
        }

        ok = fail = 0
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {
                pool.submit(_download_one, url, dest): url
                for url, dest in tasks.items()
            }
            for future in as_completed(futures):
                if future.result():
                    ok += 1
                else:
                    fail += 1

        total_downloaded += ok
        total_failed     += fail
        print(f"  ✓ {ok} downloaded   ✗ {fail} failed\n")

    # ── Summary ──────────────────────────────────────────────────────────────
    print(f"{'─'*60}")
    print(f"  DONE")
    print(f"  Folders created   : {total_folders}")
    print(f"  Images downloaded : {total_downloaded}")
    print(f"  Images failed     : {total_failed}")
    print(f"{'─'*60}\n")

    return {
        'folders_created':   total_folders,
        'images_downloaded': total_downloaded,
        'images_failed':     total_failed,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Standalone usage
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':

    # ── Example 1 — folder name from Title only ──────────────────────────────
    download_images_to_folders(
        csv_file     = 'imag_zly.csv',
        headers      = ['Title'],
        base_path    = './output_folders',
        separator    = '_',
        image_prefix = 'AllImage_',
    )

    # ── Example 2 — folder name from Title + Year ────────────────────────────
    # download_images_to_folders(
    #     csv_file     = 'imag_zly.csv',
    #     headers      = ['Title', 'Year'],
    #     base_path    = './output_folders',
    #     separator    = '_',
    #     image_prefix = 'AllImage_',
    # )
