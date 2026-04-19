from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import textwrap

ASSETS_DIR = Path("assets")
OUTPUT_DIR = Path("videos_gerados")
W, H = 1280, 720

def carregar_fonte(tamanho: int):
    fontes_teste = [
        ASSETS_DIR / "fonte.ttf",
        Path("C:/Windows/Fonts/arialbd.ttf"),
        Path("C:/Windows/Fonts/Arialbd.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
    ]

    for caminho in fontes_teste:
        try:
            if caminho.exists():
                return ImageFont.truetype(str(caminho), tamanho)
        except Exception:
            pass

    return ImageFont.load_default()

def escolher_imagem_base():
    candidatas = list(OUTPUT_DIR.glob("img_*.jpg"))
    if candidatas:
        return candidatas[0]

    fallback = (
        list(ASSETS_DIR.glob("*.jpg")) +
        list(ASSETS_DIR.glob("*.png")) +
        list(ASSETS_DIR.glob("*.jpeg"))
    )

    if not fallback:
        raise RuntimeError("Nenhuma imagem disponível para gerar thumbnail.")

    return fallback[0]

def gerar_thumbnail(texto: str, output_path: str = "videos_gerados/thumb.jpg"):
    base_path = escolher_imagem_base()

    img = Image.open(base_path).convert("RGB")
    img = img.resize((W, H))

    # leve blur no fundo para destacar o texto
    fundo = img.filter(ImageFilter.GaussianBlur(2))

    draw = ImageDraw.Draw(fundo)

    # faixa vermelha superior
    draw.rectangle((0, 0, W, 110), fill=(191, 12, 19))
    fonte_topo = carregar_fonte(28)
    draw.text((40, 35), "URGENTE", font=fonte_topo, fill="white")

    # caixa preta inferior/central
    caixa_x1, caixa_y1 = 70, 360
    caixa_x2, caixa_y2 = W - 70, H - 50
    draw.rounded_rectangle(
        (caixa_x1, caixa_y1, caixa_x2, caixa_y2),
        radius=28,
        fill=(0, 0, 0)
    )

    # texto principal
    texto = texto.upper().strip()
    linhas = textwrap.wrap(texto, width=18)

    fonte_titulo = carregar_fonte(72)
    espaco_entre_linhas = 18

    alturas = []
    for linha in linhas:
        bbox = draw.textbbox((0, 0), linha, font=fonte_titulo)
        alturas.append(bbox[3] - bbox[1])

    altura_total = sum(alturas) + espaco_entre_linhas * (len(linhas) - 1)
    y = caixa_y1 + ((caixa_y2 - caixa_y1) - altura_total) // 2

    for i, linha in enumerate(linhas):
        bbox = draw.textbbox((0, 0), linha, font=fonte_titulo)
        largura = bbox[2] - bbox[0]
        altura = bbox[3] - bbox[1]
        x = (W - largura) // 2

        # contorno
        for dx, dy in [(-3, 0), (3, 0), (0, -3), (0, 3), (-2, -2), (2, 2), (-2, 2), (2, -2)]:
            draw.text((x + dx, y + dy), linha, font=fonte_titulo, fill="black")

        draw.text((x, y), linha, font=fonte_titulo, fill="white")
        y += altura + espaco_entre_linhas

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fundo.save(output_path, quality=95)
    print(f"[OK] Thumbnail gerada: {output_path}")