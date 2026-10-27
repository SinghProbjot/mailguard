"""Generates docs/banner.png (repository banner) and refreshes the app icon. Run: python docs/make_banner.py"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = Path(__file__).parent
W, H = 1600, 500
FONT_DIR = Path("C:/Windows/Fonts")


def font(name, size):
    for cand in (FONT_DIR / name, Path(name)):
        if cand.exists():
            return ImageFont.truetype(str(cand), size)
    return ImageFont.load_default()


def shield(size, fg=(72, 132, 255), fg2=(40, 90, 230)):
    s = size / 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.polygon([(32 * s, 3 * s), (59 * s, 13 * s), (55 * s, 41 * s), (32 * s, 61 * s), (9 * s, 41 * s), (5 * s, 13 * s)], fill=fg2)
    d.polygon([(32 * s, 8 * s), (54 * s, 16 * s), (51 * s, 39 * s), (32 * s, 56 * s), (13 * s, 39 * s), (10 * s, 16 * s)], fill=fg)
    d.line([(20 * s, 32 * s), (29 * s, 42 * s), (46 * s, 22 * s)], fill="white", width=int(6 * s), joint="curve")
    return img


def main():
    img = Image.new("RGB", (W, H), (15, 20, 32))
    d = ImageDraw.Draw(img)
    # soft gradient and glow
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=(int(15 + 10 * t), int(20 + 14 * t), int(32 + 30 * t)))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([120, -60, 760, 560], fill=(56, 110, 255, 70))
    glow = glow.filter(ImageFilter.GaussianBlur(120))
    img.paste(glow, (0, 0), glow)
    # thin grid lines for texture
    d = ImageDraw.Draw(img)
    for x in range(0, W, 80):
        d.line([(x, 0), (x, H)], fill=(255, 255, 255, 6) if False else (22, 28, 44), width=1)
    for y in range(0, H, 80):
        d.line([(0, y), (W, y)], fill=(22, 28, 44), width=1)
    # shield
    sh = shield(300)
    img.paste(sh, (150, 100), sh)
    # text
    title_f = font("bahnschrift.ttf", 150)
    sub_f = font("segoeui.ttf", 40)
    small_f = font("segoeui.ttf", 28)
    d.text((520, 118), "MailGuard", font=title_f, fill=(245, 247, 250))
    d.text((526, 290), "Local phishing protection for Outlook", font=sub_f, fill=(170, 184, 210))
    d.text((528, 352), "Rules, header checks and a local language model. Nothing leaves your PC.", font=small_f, fill=(120, 134, 160))
    img.save(HERE / "banner.png", optimize=True)
    print(HERE / "banner.png")


if __name__ == "__main__":
    main()
