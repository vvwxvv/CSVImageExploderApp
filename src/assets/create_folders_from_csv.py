import os
import csv
from pathlib import Path


def sanitize_folder_name(name):
    """Remove/replace invalid characters and lowercase."""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '_')
    name = name.strip('. ')
    return name.lower()


def create_folders_from_csv(
    csv_file,
    headers,
    base_path='.',
    separator='_',
):
    """
    Read a CSV and create folders from selected column values.

    Args:
        csv_file  : path to the CSV file
        headers   : list of 1 or 2 column names to use as folder name parts
        base_path : root directory where folders will be created
        separator : string used to join the parts (default '_')

    Returns:
        list of created folder paths
    """
    if not isinstance(headers, (list, tuple)) or not (1 <= len(headers) <= 2):
        raise ValueError("'headers' must be a list of 1 or 2 column names.")

    created_folders = []
    skipped_rows = []

    Path(base_path).mkdir(parents=True, exist_ok=True)

    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        csv_headers = reader.fieldnames or []
        missing = [h for h in headers if h not in csv_headers]
        if missing:
            raise ValueError(
                f"Column(s) not found in CSV: {missing}\n"
                f"Available columns: {csv_headers}"
            )

        for row_num, row in enumerate(reader, start=2):
            parts = []
            for h in headers:
                value = row.get(h, '').strip()
                if value:
                    parts.append(sanitize_folder_name(value))

            if not parts:
                skipped_rows.append(row_num)
                continue

            folder_name = separator.join(parts)
            folder_path = os.path.join(base_path, folder_name)

            try:
                Path(folder_path).mkdir(parents=True, exist_ok=True)
                created_folders.append(folder_path)
                print(f"[OK]      {folder_path}")
            except Exception as e:
                print(f"[ERROR]   Row {row_num} — {e}")

    if skipped_rows:
        print(f"\nSkipped {len(skipped_rows)} empty row(s): {skipped_rows}")

    print(f"\nDone — {len(created_folders)} folder(s) created in '{base_path}'")
    return created_folders


# ── Example usage ────────────────────────────────────────────────────────────
if __name__ == '__main__':

    # Example 1 – single header
    create_folders_from_csv(
        csv_file='artworks.csv',
        headers=['title'],
        base_path='./output_folders',
    )

    # Example 2 – two headers joined by '_'
    create_folders_from_csv(
        csv_file='artworks.csv',
        headers=['artist', 'title'],
        base_path='./output_folders',
    )

    # Example 3 – custom separator (dash)
    create_folders_from_csv(
        csv_file='artworks.csv',
        headers=['year', 'title'],
        base_path='./output_folders',
        separator='-',
    )