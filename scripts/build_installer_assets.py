"""Prepare NSIS bitmap resources from the existing Racall logo; no redesign."""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def main():
    logo = Image.open(ROOT / "assets/icon.png").convert("RGBA")
    output = ROOT / "installer/assets"
    output.mkdir(exist_ok=True)
    # NSIS expects opaque 24-bit BMPs at its standard dialog dimensions.
    for name, size, logo_size, position in (
        ("header.bmp", (150, 57), (56, 56), (90, 0)),
        ("sidebar.bmp", (164, 314), (112, 112), (26, 30)),
    ):
        bitmap = Image.new("RGB", size, "white")
        mark = logo.resize(logo_size, Image.Resampling.LANCZOS)
        bitmap.paste(mark, position, mark)
        bitmap.save(output / name, format="BMP")
        print(output / name)


if __name__ == "__main__":
    main()
