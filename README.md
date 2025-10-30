## QR Generator (Python + uv)

Generate a QR code PNG for a single URL and save it into `Outputs/`.

### Requirements

- Python 3.9+
- uv (ultra-fast Python package manager). Install: `curl -LsSf https://astral.sh/uv/install.sh | sh` or see `https://docs.astral.sh/uv/`.

### Setup (once)

```bash
cd /Users/dingzhong/FUCK_iCloud/QR_generator
uv venv
source .venv/bin/activate  # on macOS/Linux; on Windows: .venv\\Scripts\\activate
uv sync  # installs dependencies from pyproject.toml
```

### Usage

- CLI (module entry point):

```bash
uv run generate-qr "https://apps.apple.com/us/app/magicshotbox/id6748461314"
```

- Or run the script directly:

```bash
uv run python generate_qr.py --url "https://apps.apple.com/us/app/magicshotbox/id6748461314"
```

The script prints the output path (PNG) and saves it under `Outputs/`.


(QR_generator) dingzhong@Mac QR_generator % uv run generate_qr.py --url "https://apps.apple.com/us/app/magicshotbox/id6748461314" --logo-name logo3.png --caption "Scan the QR code to download MagicShotBox APP"


### Options

```bash
python generate_qr.py --help

positional arguments:
  url                   The URL to encode into the QR code

options:
  --url URL             Alternative way to pass the URL
  --size SIZE           Output PNG size in pixels (default: 300)
  --ec {L,M,Q,H}        Error correction level (default: M)
  --quiet-zone N        Quiet zone in modules (default: 4)
  --force               Overwrite existing file
```

Example URL above references the MagicShotBox app on the App Store: `https://apps.apple.com/us/app/magicshotbox/id6748461314`.
