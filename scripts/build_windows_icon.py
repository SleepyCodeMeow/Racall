"""Build the Windows ICO with optical sizing for captions, taskbar and Explorer.

The shared PNG keeps its presentation padding for installer artwork and other
platforms. Only Windows shell icons use the tighter artwork bounds below.
"""

from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)


def main():
    with Image.open(ROOT / "assets/icon.png") as source:
        source = source.convert("RGBA")
        # Ignore almost-transparent stray pixels outside the sticker. Retain a
        # four-source-pixel guard so its antialiased outline is not clipped.
        bounds = source.getchannel("A").point(lambda alpha: 255 if alpha >= 128 else 0).getbbox()
        if bounds is None:
            raise ValueError("The icon source has no visible artwork")
        left, top, right, bottom = bounds
        artwork = source.crop(
            (max(0, left - 4), max(0, top - 4), min(source.width, right + 4), min(source.height, bottom + 4))
        )

    frames = []
    for size in SIZES:
        # Small shell slots need the full canvas; large Explorer icons retain
        # a narrow optical margin. Always resample from the original artwork.
        inset = 0 if size <= 48 else round(size * 0.02)
        mark = ImageOps.contain(artwork, (size - 2 * inset, size - 2 * inset), Image.Resampling.LANCZOS)
        frame = Image.new("RGBA", (size, size))
        frame.alpha_composite(mark, ((size - mark.width) // 2, (size - mark.height) // 2))
        frames.append(frame)

    output = ROOT / "assets/icon.ico"
    frames[-1].save(output, format="ICO", sizes=[(size, size) for size in SIZES], append_images=frames[:-1])
    print(f"{output}: {', '.join(map(str, SIZES))} px")


if __name__ == "__main__":
    main()
