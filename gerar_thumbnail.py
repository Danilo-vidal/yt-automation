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


def quebrar_texto(texto: str, max_linhas: int = 3, largura: int = 16):
    texto = texto.upper().strip()
    linhas = textwrap.wrap(texto, width=largura)

    if len(linhas) > max_linhas:
        linhas = linhas[:max_linhas]
        ultima = linhas[-1]
        if not ultima.endswith("..."):
            linhas[-1] = ultima[: max(0, len(ultima) - 3)] + "..."

    return linhas


def desenhar_texto_com_contorno(draw, pos, texto, fonte, fill="white", outline="black", espessura=4):
    x, y = pos
    for dx in range(-espessura, espessura + 1):
        for dy in range(-espessura, espessura + 1):
            if dx != 0 or dy != 0:
                draw.text((x + dx, y + dy), texto, font=fonte, fill=outline)
    draw.text((x, y), texto, font=fonte, fill=fill)


def gerar_thumbnail(texto: str, output_path: str = "videos_gerados/thumb.jpg"):
    base_path = escolher_imagem_base()

    img = Image.open(base_path).convert("RGB")

    # preencher 16:9 sem borda
    img_ratio = img.width / img.height
    target_ratio = W / H

    if img_ratio > target_ratio:
        novo_h = H
        novo_w = int(H * img_ratio)
    else:
        novo_w = W
        novo_h = int(W / img_ratio)

    img = img.resize((novo_w, novo_h), Image.LANCZOS)
    left = (novo_w - W) // 2
    top = (novo_h - H) // 2
    img = img.crop((left, top, left + W, top + H))

    # leve contraste visual
    fundo = img.filter(ImageFilter.GaussianBlur(1))
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 35))
    fundo = Image.alpha_composite(fundo.convert("RGBA"), overlay).convert("RGB")

    draw = ImageDraw.Draw(fundo)

    # faixa vermelha superior
    faixa_h = 95
    draw.rectangle((0, 0, W, faixa_h), fill=(191, 12, 19))

    fonte_topo = carregar_fonte(30)
    desenhar_texto_com_contorno(draw, (35, 25), "URGENTE", fonte_topo, fill="white", outline="black", espessura=2)

    # texto principal
    linhas = quebrar_texto(texto, max_linhas=3, largura=16)
    fonte_titulo = carregar_fonte(84)
    espaco = 12

    alturas = []
    larguras = []

    for linha in linhas:
        bbox = draw.textbbox((0, 0), linha, font=fonte_titulo)
        larguras.append(bbox[2] - bbox[0])
        alturas.append(bbox[3] - bbox[1])

    altura_total = sum(alturas) + espaco * (len(linhas) - 1)

    # posiciona mais para baixo, estilo thumb de notícia
    y = int(H * 0.52) - altura_total // 2

    for i, linha in enumerate(linhas):
        largura = larguras[i]
        altura = alturas[i]
        x = (W - largura) // 2
        desenhar_texto_com_contorno(
            draw,
            (x, y),
            linha,
            fonte_titulo,
            fill="white",
            outline="black",
            espessura=5,
        )
        y += altura + espaco

    # pequena sombra inferior para dar profundidade
    draw.rectangle((0, H - 90, W, H), fill=(0, 0, 0))

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fundo.save(out, quality=95)
    print(f"[OK] Thumbnail gerada: {out}")