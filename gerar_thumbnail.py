import os
import base64
import textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from openai import OpenAI

OUTPUT_DIR = Path("videos_gerados")
OUTPUT_DIR.mkdir(exist_ok=True)

OUTPUT = OUTPUT_DIR / "thumb.jpg"
BASE_IMG = OUTPUT_DIR / "thumb_base.png"

WIDTH, HEIGHT = 1280, 720

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def gerar_imagem_base(prompt: str) -> Path:
    print("[THUMB] Gerando imagem base com IA...")

    img = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size="1536x1024"
    )

    b64 = img.data[0].b64_json
    img_bytes = base64.b64decode(b64)
    BASE_IMG.write_bytes(img_bytes)

    return BASE_IMG


def quebrar_texto(texto, largura=18, max_linhas=3):
    linhas = textwrap.wrap(texto.upper(), width=largura)
    return linhas[:max_linhas]


def desenhar_texto(img, texto):
    draw = ImageDraw.Draw(img)

    try:
        fonte = ImageFont.truetype("arialbd.ttf", 82)
    except Exception:
        fonte = ImageFont.load_default()

    linhas = quebrar_texto(texto, largura=16, max_linhas=3)

    altura_total = 0
    medidas = []
    for linha in linhas:
        bbox = draw.textbbox((0, 0), linha, font=fonte)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        medidas.append((linha, w, h))
        altura_total += h + 8

    y = HEIGHT - altura_total - 50

    for linha, w, h in medidas:
        x = (WIDTH - w) // 2

        for dx in [-3, -2, -1, 1, 2, 3]:
            for dy in [-3, -2, -1, 1, 2, 3]:
                draw.text((x + dx, y + dy), linha, font=fonte, fill="black")

        draw.text((x, y), linha, font=fonte, fill="white")
        y += h + 8


def gerar_prompt_thumb(headline: str) -> str:
    return f"""
Crie uma thumbnail realista e cinematográfica para YouTube sobre notícia.

Tema:
{headline}

Diretrizes:
- composição horizontal 16:9
- personagem principal em destaque, close-up
- expressão intensa ou dramática
- fundo relacionado ao tema da notícia
- iluminação cinematográfica
- alto contraste
- visual impactante de thumbnail de canal grande
- sem texto na imagem
- sem letras
- sem logos
- sem tarja vermelha
- sem marca d'água
- aparência realista
"""


def gerar_thumbnail(headline: str):
    prompt = gerar_prompt_thumb(headline)
    base_img_path = gerar_imagem_base(prompt)

    img = Image.open(base_img_path).convert("RGB")
    img = img.resize((WIDTH, HEIGHT), Image.LANCZOS)

    # contraste e nitidez leves
    img = ImageEnhance.Contrast(img).enhance(1.10)
    img = ImageEnhance.Sharpness(img).enhance(1.08)

    # sombreado suave na parte inferior para leitura do texto
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle([0, HEIGHT - 230, WIDTH, HEIGHT], fill=(0, 0, 0, 110))

    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    desenhar_texto(img, headline)

    img.save(OUTPUT, quality=95)
    print(f"[THUMB] Thumbnail gerada com sucesso em: {OUTPUT}")


if __name__ == "__main__":
    gerar_thumbnail("Crise política explode no Brasil")