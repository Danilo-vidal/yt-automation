import os
import base64
import textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from openai import OpenAI

OUTPUT = Path("thumb.jpg")
WIDTH, HEIGHT = 1280, 720

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# =========================
# GERAR IMAGEM COM IA
# =========================
def gerar_imagem_base(prompt):
    print("[THUMB] Gerando imagem com IA...")

    img = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size="1024x1024"
    )

    b64 = img.data[0].b64_json
    img_bytes = base64.b64decode(b64)

    path = "thumb_base.png"
    with open(path, "wb") as f:
        f.write(img_bytes)

    return path


# =========================
# QUEBRAR TEXTO EM LINHAS
# =========================
def quebrar_texto(texto, largura=18, max_linhas=3):
    linhas = textwrap.wrap(texto.upper(), width=largura)
    return linhas[:max_linhas]


# =========================
# DESENHAR TEXTO CENTRAL
# =========================
def desenhar_texto(img, texto):
    draw = ImageDraw.Draw(img)

    try:
        fonte = ImageFont.truetype("arialbd.ttf", 90)
    except:
        fonte = ImageFont.load_default()

    linhas = quebrar_texto(texto)

    y = HEIGHT // 2 - (len(linhas) * 60)

    for linha in linhas:
        w, h = draw.textbbox((0, 0), linha, font=fonte)[2:]

        x = (WIDTH - w) // 2

        # contorno preto
        for dx in [-3, -2, -1, 1, 2, 3]:
            for dy in [-3, -2, -1, 1, 2, 3]:
                draw.text((x + dx, y + dy), linha, font=fonte, fill="black")

        # texto branco
        draw.text((x, y), linha, font=fonte, fill="white")

        y += h + 10


# =========================
# FUNÇÃO PRINCIPAL
# =========================
def gerar_thumbnail(headline):
    prompt = f"{headline}, dramatic, protest, political tension, cinematic lighting, realistic, news photo"

    base_img_path = gerar_imagem_base(prompt)

    img = Image.open(base_img_path).convert("RGB")
    img = img.resize((WIDTH, HEIGHT))

    draw = ImageDraw.Draw(img)

    # faixa vermelha topo
    draw.rectangle([0, 0, WIDTH, 120], fill=(200, 0, 0))

    try:
        fonte_topo = ImageFont.truetype("arialbd.ttf", 50)
    except:
        fonte_topo = ImageFont.load_default()

    draw.text((30, 30), "URGENTE", font=fonte_topo, fill="white")

    # texto principal
    desenhar_texto(img, headline)

    img.save(OUTPUT)
    print("[THUMB] Thumbnail gerada com sucesso")


if __name__ == "__main__":
    gerar_thumbnail("Crise política explode no Brasil")