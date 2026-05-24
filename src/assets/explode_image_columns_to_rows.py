import os
import pandas as pd


def explode_image_rows_to_columns(
    input_csv: str,
    output_csv: str,
    image_prefix: str = "AllImage_",
    image_column_name: str = "ImageURL"
):

    # Read CSV
    df = pd.read_csv(
        input_csv,
        keep_default_na=False,
        dtype=str
    )

    # Detect image columns
    image_cols = [
        c for c in df.columns
        if c.startswith(image_prefix)
    ]

    # Sort numerically
    image_cols.sort(
        key=lambda x: int(x.replace(image_prefix, ""))
        if x.replace(image_prefix, "").isdigit()
        else 999999
    )

    if not image_cols:
        raise ValueError("No image columns found.")

    # Non-image columns
    base_cols = [
        c for c in df.columns
        if c not in image_cols
    ]

    output_rows = []

    # Convert images into multiple rows
    for _, row in df.iterrows():

        base_data = {
            col: row[col]
            for col in base_cols
        }

        for img_col in image_cols:

            img_url = str(row[img_col]).strip()

            # Skip empty
            if img_url == "" or img_url.lower() == "nan":
                continue

            new_row = base_data.copy()
            new_row[image_column_name] = img_url

            output_rows.append(new_row)

    # Create final dataframe
    result_df = pd.DataFrame(output_rows)

    # Save
    result_df.to_csv(
        output_csv,
        index=False,
        encoding='utf-8-sig'
    )

    print(f"\nSaved:")
    print(output_csv)

    print(f"\nTotal rows:")
    print(len(result_df))


if __name__ == "__main__":

    input_csv = "zly_enriched.csv"

    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)

    output_csv = os.path.join(
        output_dir,
        "zly_enriched_images_rows.csv"
    )

    explode_image_rows_to_columns(
        input_csv=input_csv,
        output_csv=output_csv,
        image_prefix="AllImage_"
    )