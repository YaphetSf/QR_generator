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
    # Enhancements
    parser.add_argument(
        "--logo-name",
        help="Logo file name (or stem) to search under the Logos/ folder (e.g. 'mybrand' or 'mybrand.png')",
    )
    parser.add_argument(
        "--caption",
        help="Optional caption text to draw at the bottom of the image",
    )
    parser.add_argument(
        "--caption-size",
        type=int,
        help="Optional caption font size in pixels (auto-scales if omitted)",
    )
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


def find_logo_path(repo_root: str, logo_name: str | None) -> str | None:
    if not logo_name:
        return None
    logos_dir = os.path.join(repo_root, "Logos")
    if not os.path.isdir(logos_dir):
        return None

    # Normalize input: accept with or without extension
    desired_stem = os.path.splitext(logo_name)[0].lower()
    desired_filename = logo_name.lower()
    candidates = []
    try:
        for entry in os.listdir(logos_dir):
            entry_lower = entry.lower()
            stem_lower = os.path.splitext(entry_lower)[0]
            if entry_lower == desired_filename or stem_lower == desired_stem:
                candidates.append(os.path.join(logos_dir, entry))
    except Exception:
        return None

    # Prefer common image extensions
    def sort_key(p: str) -> int:
        ext = os.path.splitext(p)[1].lower()
        order = {".png": 0, ".jpg": 1, ".jpeg": 1, ".webp": 2, ".bmp": 3}
        return order.get(ext, 9)

    candidates.sort(key=sort_key)
    return candidates[0] if candidates else None


def overlay_logo(base_img, logo_path: str):
    try:
        from PIL import Image
        logo = Image.open(logo_path).convert("RGBA")
        base_img = base_img.convert("RGBA")

        # Scale logo to ~20% of QR width
        qr_w, qr_h = base_img.size
        max_logo_w = max(1, int(qr_w * 0.2))
        aspect = logo.width / max(logo.height, 1)
        new_w = max_logo_w
        new_h = int(new_w / max(aspect, 1e-6))
        logo = logo.resize((new_w, new_h), resample=Image.LANCZOS)

        # Center paste
        pos = ((qr_w - new_w) // 2, (qr_h - new_h) // 2)
        base_img.alpha_composite(logo, dest=pos)
        return base_img
    except Exception:
        return base_img


def _pick_truetype_font(preferred_size: int):
    try:
        from PIL import ImageFont
    except Exception:
        return None

    # Common macOS and generic candidates
    candidates = [
        "/Library/Fonts/Arial.ttf",
        "/Library/Fonts/Helvetica.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "DejaVuSans.ttf",
    ]
    for path in candidates:
        try:
            if os.path.exists(path):
                return ImageFont.truetype(path, preferred_size)
            # Also allow PIL to resolve by name in its font path
            if os.path.sep not in path:
                return ImageFont.truetype(path, preferred_size)
        except Exception:
            continue
    return None


def add_caption(base_img, caption: str | None, caption_size: int | None = None):
    if not caption:
        return base_img
    try:
        from PIL import Image, ImageDraw, ImageFont
        base_img = base_img.convert("RGBA")
        w, h = base_img.size
        # Determine font size relative to image width if not provided
        font_px = caption_size if caption_size and caption_size > 0 else max(20, int(w * 0.08))
        font = _pick_truetype_font(font_px)
        if font is None:
            # Fallback to default bitmap font
            font = ImageFont.load_default()
            # Best-effort scale calculation based on default bbox measured later

        # Pre-measure text to allocate exact space with padding
        tmp_img = Image.new("RGBA", (w, h), (255, 255, 255, 0))
        tmp_draw = ImageDraw.Draw(tmp_img)
        text = str(caption)
        bbox = tmp_draw.textbbox((0, 0), text, font=font, stroke_width=2)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        padding_y = max(12, int((font_px if caption_size else w * 0.02)))
        extra_h = max(text_h + padding_y * 2, 40)

        canvas = Image.new("RGBA", (w, h + extra_h), (255, 255, 255, 255))
        canvas.paste(base_img, (0, 0))

        draw = ImageDraw.Draw(canvas)
        x = max(0, (w - text_w) // 2)
        y = h + max(0, (extra_h - text_h) // 2)
        # Draw with a subtle stroke for readability
        draw.text((x, y), text, fill=(0, 0, 0, 255), font=font, stroke_width=2, stroke_fill=(255, 255, 255, 255))
        return canvas.convert("RGB")
    except Exception:
        return base_img


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

        # Optional logo overlay from Logos/
        logo_path = find_logo_path(repo_root, args.logo_name)
        if logo_path:
            img = overlay_logo(img, logo_path)

        # Optional caption text (auto-sizing with optional override)
        img = add_caption(img, args.caption, args.caption_size)

        img.save(output_path)
    except Exception as e:  # pragma: no cover
        print(f"Failed to generate QR code: {e}", file=sys.stderr)
        return 1

    print(output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())


