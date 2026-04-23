from pathlib import Path
from typing import List, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageStat
import textwrap
import cv2
import numpy as np

OUTPUT_DIR = Path("videos_gerados")
OUTPUT_DIR.mkdir(exist_ok=True)

OUTPUT = OUTPUT_DIR / "thumb.jpg"

WIDTH, HEIGHT = 1280, 720


# =========================
# SELEÇÃO INTELIGENTE
# =========================
def listar_frames() -> List[Path]:
    frames = sorted(OUTPUT_DIR.glob("frame_*.jpg"))
    return frames


def score_imagem(path: Path) -> float:
    img = cv2.imread(str(path))

    if img is None:
        return 0

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # brilho
    brilho = np.mean(gray)

    # contraste
    contraste = np.std(gray)

    # detecção de rosto
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)

    score_rosto = 50 if len(faces) > 0 else 0

    score_final = brilho + contraste + score_rosto

    return score_final


def escolher_melhor_imagem() -> Path:
    frames = listar_frames()

    if not frames:
        raise RuntimeError("Nenhum frame encontrado")

    ranking: List[Tuple[Path, float]] = []

    for f in frames:
        s = score_imagem(f)
        ranking.append((f, s))
        print(f"[THUMB] Score {f.name}: {s:.2f}")

    ranking.sort(key=lambda x: x[1], reverse=True)

    melhor = ranking[0][0]
    print(f"[THUMB] Melhor frame escolhido: {melhor}")

    return melhor


# =========================
# TEXTO
# =========================
def quebrar_texto(texto):
    return textwrap.wrap(texto.upper(), width=16)[:3]


def desenhar_texto(img, texto):
    draw = ImageDraw.Draw(img)

    try:
        fonte = ImageFont.truetype("arialbd.ttf", 82)
    except:
        fonte = ImageFont.load_default()

    linhas = quebrar_texto(texto)

    y = HEIGHT - 260

    for linha in linhas:
        w = draw.textlength(linha, font=fonte)
        x = (WIDTH - w) // 2

        # sombra
        for dx in [-3, 3]:
            for dy in [-3, 3]:
                draw.text((x + dx, y + dy), linha, font=fonte, fill="black")

        draw.text((x, y), linha, font=fonte, fill="white")
        y += 90


# =========================
# GERAÇÃO FINAL
# =========================
def gerar_thumbnail(headline: str):
    print("[THUMB] Gerando thumbnail...")

    base = escolher_melhor_imagem()

    img = Image.open(base).convert("RGB")

    # crop central
    img = img.resize((1280, 720))

    # melhorar qualidade
    img = ImageEnhance.Contrast(img).enhance(1.15)
    img = ImageEnhance.Sharpness(img).enhance(1.1)

    # overlay escuro
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle([0, HEIGHT - 250, WIDTH, HEIGHT], fill=(0, 0, 0, 120))

    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    desenhar_texto(img, headline)

    img.save(OUTPUT, quality=95)

    print(f"[THUMB] OK: {OUTPUT}")


if __name__ == "__main__":
    gerar_thumbnail("Teste thumbnail")