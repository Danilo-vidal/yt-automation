import os
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List

import requests
from PIL import Image, ImageDraw, ImageFont
import mutagen.mp3

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
OUTPUT_DIR = Path("videos_gerados")
ASSETS_DIR = Path("assets")
W, H = 1080, 1920
OUTPUT_DIR.mkdir(exist_ok=True)


def buscar_imagens(query: str, quantidade: int = 5):
    print(f"[IMAGENS] Query: {query}")
    print(f"[IMAGENS] PEXELS_API_KEY presente? {'SIM' if PEXELS_API_KEY else 'NAO'}")

    caminhos = []

    if PEXELS_API_KEY:
        try:
            print("[IMAGENS] Buscando no Pexels...")
            url = "https://api.pexels.com/v1/search"
            headers = {"Authorization": PEXELS_API_KEY}
            params = {
                "query": query,
                "per_page": quantidade,
                "orientation": "portrait",
            }
            resp = requests.get(url, headers=headers, params=params, timeout=20)
            print(f"[IMAGENS] Status Pexels: {resp.status_code}")
            resp.raise_for_status()

            fotos = resp.json().get("photos", [])
            print(f"[IMAGENS] Fotos retornadas: {len(fotos)}")

            for i, foto in enumerate(fotos):
                img_url = foto["src"]["large2x"]
                img_path = OUTPUT_DIR / f"img_{i}.jpg"

                img_resp = requests.get(img_url, timeout=20)
                img_resp.raise_for_status()
                img_path.write_bytes(img_resp.content)

                caminhos.append(img_path)

            print(f"[IMAGENS] Baixadas do Pexels: {len(caminhos)}")

        except Exception as e:
            print(f"[WARN] Falha no Pexels, usando imagens locais. Detalhe: {e}")

    if not caminhos:
        locais = (
            list(ASSETS_DIR.glob("*.jpg"))
            + list(ASSETS_DIR.glob("*.png"))
            + list(ASSETS_DIR.glob("*.jpeg"))
        )
        print(f"[IMAGENS] Usando assets locais: {len(locais)}")
        caminhos.extend(locais[:quantidade])

    return caminhos


def formatar_tempo_srt(segundos: float) -> str:
    h = int(segundos // 3600)
    m = int((segundos % 3600) // 60)
    s = int(segundos % 60)
    ms = int((segundos % 1) * 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def gerar_srt_simples(texto: str, audio_path: Path) -> Path:
    import re

    duracao = mutagen.mp3.MP3(str(audio_path)).info.length
    texto = re.sub(r"\s+", " ", texto).strip()
    palavras = texto.split()

    grupos = []
    tamanho_grupo = 4

    for i in range(0, len(palavras), tamanho_grupo):
        grupo = " ".join(palavras[i:i + tamanho_grupo])
        grupos.append(grupo)

    if not grupos:
        grupos = [texto]

    # legenda ligeiramente mais “adiantada” para acompanhar melhor o TTS
    dur_por_grupo = max((duracao / len(grupos)) * 0.92, 0.7)
    adiantamento = 0.32

    srt_path = audio_path.with_suffix(".srt")

    inicio = 0.0
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, grupo in enumerate(grupos, 1):
            real_inicio = max(0.0, inicio - adiantamento)
            fim = inicio + dur_por_grupo
            f.write(
                f"{i}\n"
                f"{formatar_tempo_srt(real_inicio)} --> {formatar_tempo_srt(fim)}\n"
                f"{grupo}\n\n"
            )
            inicio = fim

    return srt_path


def compor_frame(img_path: Path, titulo: str, indice: int) -> Path:
    img = Image.open(img_path).convert("RGB")
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

    draw = ImageDraw.Draw(img)

    draw.rectangle([0, 0, W, 140], fill=(12, 12, 12))
    draw.rectangle([0, 0, 10, 140], fill=(220, 30, 30))

    try:
        fonte_titulo = ImageFont.truetype(str(ASSETS_DIR / "fonte.ttf"), 44)
        fonte_canal = ImageFont.truetype(str(ASSETS_DIR / "fonte.ttf"), 26)
    except Exception:
        fonte_titulo = ImageFont.load_default()
        fonte_canal = ImageFont.load_default()

    titulo_curto = titulo[:85] + "..." if len(titulo) > 85 else titulo
    draw.text((26, 14), titulo_curto, font=fonte_titulo, fill=(255, 255, 255))
    draw.text((26, 58), "POLÍTICA AGORA", font=fonte_canal, fill=(220, 220, 220))

    logo_path = ASSETS_DIR / "logo.png"
    if logo_path.exists():
        logo = Image.open(logo_path).convert("RGBA").resize((54, 54))
        img.paste(logo, (W - 80, 18), logo)

    frame_path = OUTPUT_DIR / f"frame_{indice:03d}.jpg"
    img.save(frame_path, quality=95)
    return frame_path


def montar_slideshow(frames: List[Path], audio_path: Path, srt_path: Path, duracao_audio: float) -> Path:
    corpo_path = OUTPUT_DIR / "corpo.mp4"
    duracao_por_frame = duracao_audio / len(frames)

    inputs = []
    filtros = []

    for i, frame in enumerate(frames):
        inputs += ["-loop", "1", "-t", str(duracao_por_frame), "-i", str(frame)]
        filtros.append(
            f"[{i}:v]scale=2200:-1,"
            f"zoompan=z='min(zoom+0.0008,1.08)':"
            f"x='iw/2-(iw/zoom/2)':"
            f"y='ih/2-(ih/zoom/2)':"
            f"d={int(duracao_por_frame * 25)}:s={W}x{H}:fps=25,"
            f"setsar=1[v{i}]"
        )

    concat_inputs = "".join(f"[v{i}]" for i in range(len(frames)))
    filtros.append(f"{concat_inputs}concat=n={len(frames)}:v=1:a=0[vout]")

    srt_escaped = str(srt_path.resolve()).replace("\\", "/").replace(":", "\\:")
    filtros.append(
    f"[vout]subtitles='{srt_escaped}':force_style='FontName=Arial,FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&H00000000,Outline=3,Shadow=0,Alignment=2,MarginV=120,Bold=1'[vfinal]"
)

    filter_complex = ";".join(filtros)

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-i", str(audio_path),
        "-filter_complex", filter_complex,
        "-map", "[vfinal]",
        "-map", f"{len(frames)}:a",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "22",
        "-c:a", "aac",
        "-b:a", "160k",
        "-shortest",
        "-movflags", "+faststart",
        str(corpo_path),
    ]

    subprocess.run(cmd, check=True)
    return corpo_path


def adicionar_trilha(corpo_path: Path) -> Path:
    trilha = ASSETS_DIR / "trilha.mp3"
    if not trilha.exists():
        return corpo_path

    saida = OUTPUT_DIR / "corpo_com_trilha.mp4"

    cmd = [
        "ffmpeg", "-y",
        "-i", str(corpo_path),
        "-stream_loop", "-1", "-i", str(trilha),
        "-filter_complex",
        "[1:a]volume=0.08[bg];[0:a][bg]amix=inputs=2:duration=first:dropout_transition=2[aout]",
        "-map", "0:v",
        "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(saida),
    ]
    subprocess.run(cmd, check=True)
    return saida


def concatenar_video(corpo_path: Path) -> Path:
    intro_path = ASSETS_DIR / "intro.mp4"
    outro_path = ASSETS_DIR / "outro.mp4"
    final_path = OUTPUT_DIR / f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    lista_path = OUTPUT_DIR / "lista_concat.txt"

    partes = []
    if intro_path.exists():
        partes.append(intro_path)
    partes.append(corpo_path)
    if outro_path.exists():
        partes.append(outro_path)

    with open(lista_path, "w", encoding="utf-8") as f:
        for p in partes:
            f.write(f"file '{p.resolve()}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(lista_path),
        "-c", "copy",
        str(final_path),
    ]
    subprocess.run(cmd, check=True)
    return final_path


def montar_video(noticia: dict, audio_path: Path) -> Path:
    duracao = mutagen.mp3.MP3(str(audio_path)).info.length

    # query melhor para o Pexels
    query = noticia.get("titulo", "")
    print(f"[VIDEO] Query final de imagens: {query}")

    frames_brutos = buscar_imagens(query, quantidade=5)

    srt_texto = noticia.get("roteiro_legenda") or noticia.get("resumo") or noticia.get("titulo")
    srt_path = gerar_srt_simples(srt_texto, audio_path)

    frames_compostos = [compor_frame(img, noticia["titulo"], i) for i, img in enumerate(frames_brutos)]

    corpo = montar_slideshow(frames_compostos, audio_path, srt_path, duracao)
    corpo = adicionar_trilha(corpo)
    return concatenar_video(corpo)