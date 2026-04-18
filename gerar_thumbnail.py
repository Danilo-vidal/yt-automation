from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import textwrap

ASSETS_DIR = Path("assets")
OUTPUT_DIR = Path("videos_gerados")
W, H = 1280, 720


def carregar_fonte(tamanho: int):
    try:
        return ImageFont.truetype(str(ASSETS_DIR / "fonte.ttf"), tamanho)
    except Exception:
        return ImageFont.load_default()


def escolher_imagem_base():
    candidatas = (
        list(Path("videos_gerados").glob("img_*.jpg")) +
        list(ASSETS_DIR.glob("*.jpg")) +
        list(ASSETS_DIR.glob("*.png")) +
        list(ASSETS_DIR.glob("*.jpeg"))
    )
    if not candidatas:
        raise RuntimeError("Nenhuma imagem disponível para thumbnail.")
    return candidatas[0]


def gerar_thumbnail(headline: str, output_path: str = "videos_gerados/thumb.jpg"):
    img_path = escolher_imagem_base()
    img = Image.open(img_path).convert("RGB").resize((W, H), Image.LANCZOS)
    img = img.filter(ImageFilter.GaussianBlur(radius=1.5))

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 90))
    img = Image.alpha_composite(img.convert("RGBA"), overlay)

    draw = ImageDraw.Draw(img)

    # barra vermelha
    draw.rectangle([0, 0, W, 110], fill=(180, 20, 20, 230))
    fonte_topo = carregar_fonte(40)
    draw.text((40, 28), "URGENTE", font=fonte_topo, fill=(255, 255, 255))

    # caixa de destaque
    box_x1, box_y1, box_x2, box_y2 = 70, 180, 1210, 610
    draw.rounded_rectangle([box_x1, box_y1, box_x2, box_y2], radius=28, fill=(0, 0, 0, 170))

    fonte_texto = carregar_fonte(78)
    linhas = textwrap.wrap(headline.upper(), width=18)

    y = 235
    for linha in linhas[:4]:
        bbox = draw.textbbox((0, 0), linha, font=fonte_texto)
        largura = bbox[2] - bbox[0]
        x = (W - largura) // 2
        draw.text((x, y), linha, font=fonte_texto, fill=(255, 255, 255), stroke_width=4, stroke_fill=(0, 0, 0))
        y += 92

    img.convert("RGB").save(output_path, quality=95)
    print(f"[OK] Thumbnail gerada: {output_path}")


if __name__ == "__main__":
    gerar_thumbnail("Lula desafia líderes globais")
    