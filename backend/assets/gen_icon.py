"""Genera el icono de PrestamoFlow (backend/assets/PrestamoFlow.ico).

Dibuja el logo de la marca: medallon redondeado con gradiente azul->morado,
un circulo interior (moneda) y el simbolo '$'. Se usa como icono del
ejecutable (PrestamoFlow.spec) y del instalador (prestamoflow.iss).

Ejecutar:  .venv\\Scripts\\python.exe backend\\assets\\gen_icon.py
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W = 256
FILE = Path(__file__).resolve().parent / "PrestamoFlow.ico"

C1 = (79, 70, 229)   # #4f46e5
C2 = (124, 58, 237)  # #7c3aed
WHITE = (255, 255, 255, 255)


def gradient(size):
    img = Image.new("RGBA", (size, size))
    for y in range(size):
        t = y / (size - 1)
        color = tuple(int(C1[i] + (C2[i] - C1[i]) * t) for i in range(3)) + (255,)
        for x in range(size):
            img.putpixel((x, y), color)
    return img


def make(size):
    img = gradient(size)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size, size], radius=int(size * 0.25), fill=255)
    img.putalpha(mask)

    d = ImageDraw.Draw(img)
    m = int(size * 0.31)
    d.ellipse([m, m, size - m, size - m], outline=WHITE, width=max(3, size // 27))

    font = None
    for name in ("arialbd.ttf", "DejaVuSans-Bold.ttf"):
        try:
            font = ImageFont.truetype(name, int(size * 0.52))
            break
        except OSError:
            continue
    if font:
        d.text((size / 2, size * 0.54), "$", font=font, fill=WHITE, anchor="mm")
    return img


if __name__ == "__main__":
    img = make(W)
    img.save(FILE, format="ICO", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    img2 = img.copy()
    img2.resize((64, 64)).save(FILE.with_suffix(".png"))
    print(f"icono generado: {FILE}")