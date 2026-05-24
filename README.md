# CSV Image Exploder App

A modern desktop application for exploding multi-column image data in CSV files
into individual rows - perfect for e-commerce and product data pipelines.

==============================================================================

>> FEATURES

  [+] Image Column Exploding  : Converts multiple image columns
                                (e.g. AllImage_1, AllImage_2...) into rows
  [+] Custom Column Prefix    : Define your own image column prefix
  [+] Custom Output Column    : Name the output image column as you like
  [+] Auto Encoding           : Outputs UTF-8 encoded CSV files
  [+] Modern UI               : Drag & drop frameless window design
  [+] Empty Value Handling    : Automatically skips blank or NaN image cells

==============================================================================

>> REQUIREMENTS

  - Windows 10/11
  - Python 3.7+  (for source installation)
  - 100MB RAM
  - 50MB free space

==============================================================================

>> INSTALLATION

  --- Option 1: Executable (Recommended) ---

    1. Download the latest release
    2. Extract and run CSVImageExploder.exe

  --- Option 2: From Source ---

    git clone https://github.com/vvwxvv/CSVImageExploder.git
    cd CSVImageExploder
    python -m venv appenv
    appenv\Scripts\activate
    pip install -r requirements.txt
    python main.py

==============================================================================

>> HOW TO USE

  [1] Launch the application
  [2] Select CSV File        --> Choose your input CSV file
  [3] Select Output Dir      --> Choose where to save the result
  [4] Set Options:
        * Image Column Prefix      : prefix of your image columns
                                     (default: AllImage_)
        * Output Image Column Name : name for the output column
                                     (default: ImageURL)
  [5] Click "Start Exploding" to process

==============================================================================

>> INPUT / OUTPUT EXAMPLE

  Input CSV:
  +-----------+--------+------------------+------------------+------------------+
  | ProductID | Name   | AllImage_1       | AllImage_2       | AllImage_3       |
  +-----------+--------+------------------+------------------+------------------+
  | 001       | Apple  | http://img1.jpg  | http://img2.jpg  | http://img3.jpg  |
  | 002       | Orange | http://img4.jpg  |                  | http://img5.jpg  |
  +-----------+--------+------------------+------------------+------------------+

  Output CSV:
  +-----------+--------+------------------+
  | ProductID | Name   | ImageURL         |
  +-----------+--------+------------------+
  | 001       | Apple  | http://img1.jpg  |
  | 001       | Apple  | http://img2.jpg  |
  | 001       | Apple  | http://img3.jpg  |
  | 002       | Orange | http://img4.jpg  |
  | 002       | Orange | http://img5.jpg  |
  +-----------+--------+------------------+

  (*) Empty image cells are automatically skipped

==============================================================================

>> SUPPORTED FORMATS

  - Input      : CSV files with header row
  - Delimiters : Comma (auto-detected)
  - Encoding   : Auto-detected input, UTF-8 BOM output
  - Columns    : Any numbered suffix after your chosen prefix
  - Headers    : Required (first row as column names)

==============================================================================

>> EXAMPLES

  --- Default Settings ---

    Image Column Prefix      : AllImage_
    Output Image Column Name : ImageURL
    Result : AllImage_1, AllImage_2, AllImage_3 --> one ImageURL per row

  --- Custom Prefix ---

    Image Column Prefix      : Photo_
    Output Image Column Name : PhotoLink
    Result : Photo_1, Photo_2 ... --> one PhotoLink per row

  --- Large Datasets ---

    Input  : 1,000 products x 10 image columns
    Output : up to 10,000 individual image rows

==============================================================================

>> TROUBLESHOOTING

  +------------------------------+------------------------------------------+
  | Error                        | Fix                                      |
  +------------------------------+------------------------------------------+
  | No image columns found       | Check prefix matches exactly             |
  |                              | (case-sensitive)                         |
  +------------------------------+------------------------------------------+
  | No header row                | Ensure first row contains column names   |
  +------------------------------+------------------------------------------+
  | Encoding error               | Save input CSV as UTF-8 before running   |
  +------------------------------+------------------------------------------+
  | Empty output file            | All image cells may be blank             |
  |                              | -- check your data                       |
  +------------------------------+------------------------------------------+
  | Missing columns in output    | Column names with spaces must match      |
  |                              | exactly                                  |
  +------------------------------+------------------------------------------+

==============================================================================

>> LICENSE

  MIT License - see LICENSE file for details.

------------------------------------------------------------------------------

  Made with purpose for efficient product image data management.