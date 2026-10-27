"""Generates assets/icon.png and assets/icon.ico (blue shield with a check mark)."""
from pathlib import Path


def make():
    from PIL import Image, ImageDraw
    out = Path(__file__).parent / "assets"
    out.mkdir(exist_ok=True)
    size = 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size / 64
    d.polygon([(32 * s, 3 * s), (59 * s, 13 * s), (55 * s, 41 * s), (32 * s, 61 * s), (9 * s, 41 * s), (5 * s, 13 * s)], fill=(31, 94, 255, 255))
    d.polygon([(32 * s, 8 * s), (54 * s, 16 * s), (51 * s, 39 * s), (32 * s, 56 * s), (13 * s, 39 * s), (10 * s, 16 * s)], fill=(60, 120, 255, 255))
    d.line([(20 * s, 32 * s), (29 * s, 42 * s), (46 * s, 22 * s)], fill="white", width=int(6 * s), joint="curve")
    img.save(out / "icon.png")
    img.save(out / "icon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    return out


if __name__ == "__main__":
    print(make())
