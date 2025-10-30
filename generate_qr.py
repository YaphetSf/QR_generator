#!/usr/bin/env python3
import argparse
import os
import re
import sys
from datetime import datetime
from urllib.parse import urlparse

try:
    import qrcode
    from qrcode.constants import ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q, ERROR_CORRECT_H
except Exception as import_error:  # pragma: no cover
    print("Missing dependency: qrcode. Install with `pip install -r requirements.txt`.", file=sys.stderr)
    raise


ERROR_CORRECTION_MAP = {
    "L": ERROR_CORRECT_L,
    "M": ERROR_CORRECT_M,
    "Q": ERROR_CORRECT_Q,
    "H": ERROR_CORRECT_H,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a QR code PNG from a single URL and save into Outputs/",
    )
    parser.add_argument("url", nargs="?", help="The URL to encode into the QR code")
    parser.add_argument("--url", dest="url_flag", help="Alternative way to pass the URL")
    parser.add_argument("--size", type=int, default=600, help="Output PNG size in pixels (width=height)")
    parser.add_argument(
        "--ec",
        choices=["L", "M", "Q", "H"],
        default="M",
        help="Error correction level (L/M/Q/H)",
    )
    parser.add_argument("--quiet-zone", type=int, default=4, help="Quiet zone (border) in modules")
    parser.add_argument("--force", action="store_true", help="Overwrite if output file already exists")
    return parser.parse_args()


def validate_url(url: str) -> str:
    if not url:
        raise ValueError("URL is required")
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"Invalid URL: {url}")
    return url


def sanitize_filename_component(text: str) -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("._-")
    return text or "qr"


def derive_filename(url: str) -> str:
    parsed = urlparse(url)
    host = sanitize_filename_component(parsed.netloc)
    path_parts = [p for p in parsed.path.split("/") if p]
    tail = sanitize_filename_component(path_parts[-1]) if path_parts else ""
    stem = f"{host}_{tail}" if tail else host
    stem = stem or "qr"
    return f"{stem}.png"


def ensure_outputs_dir(repo_root: str) -> str:
    outputs_dir = os.path.join(repo_root, "Outputs")
    os.makedirs(outputs_dir, exist_ok=True)
    return outputs_dir


def build_qr_image(url: str, error_correction_key: str, quiet_zone: int, target_size: int):
    error_correction = ERROR_CORRECTION_MAP[error_correction_key]
    qr = qrcode.QRCode(
        version=None,
        error_correction=error_correction,
        box_size=10,
        border=quiet_zone,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    # Resize to requested size (keeping square)
    try:
        from PIL import Image
        img = img.resize((target_size, target_size), resample=Image.NEAREST)
    except Exception:
        # Fallback if PIL not present (qrcode[pil] should install it)
        img = img.resize((target_size, target_size))
    return img


def main() -> int:
    args = parse_args()
    url = args.url_flag or args.url

    try:
        url = validate_url(url)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2

    repo_root = os.path.dirname(os.path.abspath(__file__))
    outputs_dir = ensure_outputs_dir(repo_root)

    filename = derive_filename(url)
    output_path = os.path.join(outputs_dir, filename)

    if os.path.exists(output_path) and not args.force:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stem, ext = os.path.splitext(filename)
        output_path = os.path.join(outputs_dir, f"{stem}_{timestamp}{ext}")

    try:
        img = build_qr_image(url, args.ec, args.quiet_zone, args.size)
        img.save(output_path)
    except Exception as e:  # pragma: no cover
        print(f"Failed to generate QR code: {e}", file=sys.stderr)
        return 1

    print(output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())


