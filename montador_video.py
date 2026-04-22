import os
import base64
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List

import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
import mutagen.mp3
from openai import OpenAI


PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

OUTPUT_DIR = Path("videos_gerados")
ASSETS_DIR = Path("assets")
W, H = 1080, 1920

OUTPUT_DIR.mkdir(exist_ok=True)

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


def extrair_contexto_da_materia(url: str, max_chars: int = 1200) -> str:
    try:
        resp = requests.get(
            url,
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        paragrafos = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
        texto = " ".join(paragrafos)
        texto = " ".join(texto.split())
        return texto[:max_chars]
    except Exception as e:
        print(f"[CONTEXTO] Falha ao extrair matéria: {e}")
        return ""


def gerar_query_imagem(noticia: dict):
    titulo = (noticia.get("titulo") or "").lower()
    resumo = (noticia.get("resumo") or "").lower()
    texto = f"{titulo} {resumo}"

    if any(p in texto for p in ["governo", "lula", "bolsonaro", "presidente", "política", "congresso", "senado", "câmara"]):
        return "brazil politics protest congress government"

    if any(p in texto for p in ["crime", "polícia", "assalto", "prisão", "operação", "investigação"]):
        return "police operation arrest investigation brazil"

    if any(p in texto for p in ["guerra", "ataque", "militar", "míssil", "soldado"]):
        return "war military conflict soldiers"

    if any(p in texto for p in ["economia", "inflação", "dinheiro", "mercado", "dólar", "bolsa"]):
        return "economy money crisis finance business graph"

    if any(p in texto for p in ["protesto", "manifestação", "rua", "crise"]):
        return "protest crowd tension street demonstration"

    return "breaking news dramatic scene"


def gerar_queries_alternativas(noticia: dict) -> List[str]:
    titulo = (noticia.get("titulo") or "").strip()
    resumo = (noticia.get("resumo") or "").strip()
    base = gerar_query_imagem(noticia)

    queries = [
        base,
        titulo,
        resumo[:80] if resumo else "",
        f"{base} news",
        f"{base} brazil",
        "breaking news politics",
        "news protest crowd government",
    ]

    limpas = []
    vistos = set()
    for q in queries:
        q = " ".join((q or "").split()).strip()
        if q and q.lower() not in vistos:
            vistos.add(q.lower())
            limpas.append(q)

    return limpas


def gerar_prompt_visual(noticia: dict, contexto_extra: str) -> str:
    titulo = noticia.get("titulo", "")
    resumo = noticia.get("resumo", "")

    return f"""
Crie uma imagem em estilo fotojornalístico realista, vertical, para vídeo curto de notícias.

Tema principal:
{titulo}

Resumo:
{resumo}

Contexto adicional:
{contexto_extra}

Diretrizes visuais:
- cena coerente com notícia política ou factual
- clima jornalístico
- composição vertical forte
- elementos visuais compatíveis com o tema
- sem texto na imagem
- sem letras
- sem logos
- sem marca d'água
- aparência realista
- iluminação cinematográfica
- estilo foto de reportagem
"""


def gerar_imagem_ia_para_video(prompt: str, output_path: Path) -> Path:
    if not client:
        raise RuntimeError("OPENAI_API_KEY não configurada para geração de imagem IA.")

    print("[IMG IA] Gerando imagem contextual para o vídeo...")

    img = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size="1024x1536"
    )

    b64 = img.data[0].b64_json
    img_bytes = base64.b64decode(b64)
    output_path.write_bytes(img_bytes)

    print(f"[IMG IA] Imagem salva em: {output_path}")
    return output_path


def buscar_imagens_pexels(query: str, quantidade: int = 5, prefixo: str = "pexels") -> List[Path]:
    print(f"[IMAGENS] Query Pexels: {query}")
    print(f"[IMAGENS] PEXELS_API_KEY presente? {'SIM' if PEXELS_API_KEY else 'NAO'}")

    caminhos: List[Path] = []

    if not PEXELS_API_KEY:
        return caminhos

    try:
        url = "https://api.pexels.com/v1/search"
        headers = {"Authorization": PEXELS_API_KEY}
        params = {
            "query": query,
            "per_page": quantidade,
            "orientation": "portrait",
            "page": 1,
        }

        resp = requests.get(url, headers=headers, params=params, timeout=20)
        print(f"[IMAGENS] Status Pexels: {resp.status_code}")
        resp.raise_for_status()

        fotos = resp.json().get("photos", [])
        print(f"[IMAGENS] Fotos retornadas: {len(fotos)}")

        for i, foto in enumerate(fotos):
            img_url = foto["src"]["large2x"]
            img_path = OUTPUT_DIR / f"img_{prefixo}_{i}.jpg"

            img_resp = requests.get(img_url, timeout=20)
            img_resp.raise_for_status()
            img_path.write_bytes(img_resp.content)
            caminhos.append(img_path)

        print(f"[IMAGENS] Baixadas do Pexels: {len(caminhos)}")

    except Exception as e:
        print(f"[WARN] Falha no Pexels para query '{query}'. Detalhe: {e}")

    return caminhos


def gerar_frames_dinamicos_de_uma_imagem(base_path: Path, quantidade: int = 5) -> List[Path]:
    if not base_path.exists():
        return []

    print(f"[IMAGENS] Gerando {quantidade} frames dinâmicos a partir de: {base_path}")

    base = Image.open(base_path).convert("RGB")
    w, h = base.size

    variacoes = []
    recortes = [
        (0.00, 0.00, 1.00, 1.00),
        (0.05, 0.02, 0.95, 0.98),
        (0.00, 0.00, 0.90, 0.95),
        (0.10, 0.03, 1.00, 0.98),
        (0.03, 0.05, 0.97, 0.90),
    ]

    for i in range(min(quantidade, len(recortes))):
        x1p, y1p, x2p, y2p = recortes[i]

        x1 = int(w * x1p)
        y1 = int(h * y1p)
        x2 = int(w * x2p)
        y2 = int(h * y2p)

        img = base.crop((x1, y1, x2, y2)).resize((w, h), Image.LANCZOS)

        if i == 1:
            img = ImageEnhance.Contrast(img).enhance(1.08)
        elif i == 2:
            img = ImageEnhance.Brightness(img).enhance(0.95)
        elif i == 3:
            img = ImageEnhance.Sharpness(img).enhance(1.12)
        elif i == 4:
            img = ImageEnhance.Color(img).enhance(0.92)

        out = OUTPUT_DIR / f"img_force_{i}.jpg"
        img.save(out, quality=95)
        variacoes.append(out)

    return variacoes


def buscar_imagens_pexels_multiplas(noticia: dict, quantidade_total: int = 4) -> List[Path]:
    queries = gerar_queries_alternativas(noticia)
    coletadas: List[Path] = []
    vistos = set()

    for idx, query in enumerate(queries):
        faltam = quantidade_total - len(coletadas)
        if faltam <= 0:
            break

        resultados = buscar_imagens_pexels(
            query=query,
            quantidade=min(3, faltam),
            prefixo=f"q{idx}"
        )

        for p in resultados:
            key = str(p.resolve())
            if key not in vistos:
                vistos.add(key)
                coletadas.append(p)

        print(f"[IMAGENS] Total acumulado após query {idx + 1}: {len(coletadas)}")

    return coletadas[:quantidade_total]


def buscar_imagens_locais(quantidade: int = 5) -> List[Path]:
    locais = (
        list(ASSETS_DIR.glob("*.jpg"))
        + list(ASSETS_DIR.glob("*.png"))
        + list(ASSETS_DIR.glob("*.jpeg"))
    )
    print(f"[IMAGENS] Assets locais encontrados: {len(locais)}")
    return locais[:quantidade]


def gerar_variacoes_de_imagem(base_path: Path, quantidade: int = 4) -> List[Path]:
    if not base_path.exists():
        return []

    print(f"[IMAGENS] Gerando {quantidade} variações a partir de: {base_path}")

    base = Image.open(base_path).convert("RGB")
    variacoes: List[Path] = []

    for i in range(quantidade):
        img = base.copy()

        if i == 0:
            img = ImageEnhance.Contrast(img).enhance(1.08)
        elif i == 1:
            w, h = img.size
            img = img.crop((int(w * 0.05), int(h * 0.03), int(w * 0.95), int(h * 0.97)))
            img = img.resize((w, h), Image.LANCZOS)
        elif i == 2:
            img = ImageEnhance.Brightness(img).enhance(0.92)
        elif i == 3:
            w, h = img.size
            img = img.crop((0, int(h * 0.02), int(w * 0.92), int(h * 0.98)))
            img = img.resize((w, h), Image.LANCZOS)
            img = ImageEnhance.Sharpness(img).enhance(1.15)
        else:
            img = img.filter(ImageFilter.GaussianBlur(radius=0.3))

        path = OUTPUT_DIR / f"img_var_{i}.jpg"
        img.save(path, quality=95)
        variacoes.append(path)

    return variacoes


def obter_frames_visuais(noticia: dict, quantidade_total: int = 5) -> List[Path]:
    quantidade_total = max(3, quantidade_total)
    frames: List[Path] = []

    url = noticia.get("url", "") or noticia.get("link", "")
    contexto_extra = extrair_contexto_da_materia(url) if url else ""

    img_ia_path = OUTPUT_DIR / "img_ia_0.jpg"
    prompt_visual = gerar_prompt_visual(noticia, contexto_extra)

    try:
        gerar_imagem_ia_para_video(prompt_visual, img_ia_path)
        frames.append(img_ia_path)
    except Exception as e:
        print(f"[IMG IA] Falha ao gerar imagem IA: {e}")

    faltam = max(0, quantidade_total - len(frames))
    if faltam > 0:
        pexels = buscar_imagens_pexels_multiplas(noticia, quantidade_total=faltam)
        frames.extend(pexels)

    if len(frames) < quantidade_total:
        faltam = quantidade_total - len(frames)
        locais = buscar_imagens_locais(quantidade=faltam)
        frames.extend(locais)

    unicos: List[Path] = []
    vistos = set()
    for p in frames:
        key = str(Path(p).resolve())
        if key not in vistos:
            vistos.add(key)
            unicos.append(Path(p))

    frames = unicos

    if frames:
        if len(frames) < 3:
            print("[IMAGENS] Menos de 3 imagens encontradas. Completando com variações da principal.")
            extras = gerar_frames_dinamicos_de_uma_imagem(frames[0], quantidade=3)
            for extra in extras:
                if len(frames) >= 3:
                    break
                if extra not in frames:
                    frames.append(extra)

        if len(frames) < quantidade_total:
            print("[IMAGENS] Completando frames restantes com variações visuais.")
            extras = gerar_frames_dinamicos_de_uma_imagem(frames[0], quantidade=quantidade_total)
            for extra in extras:
                if len(frames) >= quantidade_total:
                    break
                if extra not in frames:
                    frames.append(extra)

    print(f"[IMAGENS] Total final de frames visuais: {len(frames)}")
    for i, frame in enumerate(frames, 1):
        print(f"[IMAGENS] Frame {i}: {frame}")

    return frames


def formatar_tempo_srt(segundos: float) -> str:
    h = int(segundos // 3600)
    m = int((segundos % 3600) // 60)
    s = int(segundos % 60)
    ms = int((segundos % 1) * 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def agrupar_legendas(palavras, max_palavras=2, max_chars=16):
    grupos = []
    atual = []

    for palavra in palavras:
        teste = " ".join(atual + [palavra])

        if atual and (len(atual) >= max_palavras or len(teste) > max_chars):
            grupos.append(" ".join(atual))
            atual = [palavra]
        else:
            atual.append(palavra)

    if atual:
        grupos.append(" ".join(atual))

    return grupos


def gerar_srt_simples(texto: str, audio_path: Path) -> Path:
    import re

    duracao = mutagen.mp3.MP3(str(audio_path)).info.length
    texto = re.sub(r"\s+", " ", texto).strip()
    palavras = texto.split()

    grupos = agrupar_legendas(palavras, max_palavras=2, max_chars=16)
    if not grupos:
        grupos = [texto]

    dur_por_grupo = max((duracao / len(grupos)) * 0.90, 0.55)
    adiantamento = 0.12

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

    print(f"[LEGENDA] SRT gerado em: {srt_path}")
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
    if not frames:
        raise RuntimeError("Nenhum frame disponível para montar o slideshow.")

    corpo_path = OUTPUT_DIR / "corpo.mp4"
    duracao_por_frame = duracao_audio / len(frames)

    inputs = []
    filtros = []

    for i, frame in enumerate(frames):
        inputs += ["-loop", "1", "-t", str(duracao_por_frame), "-i", str(frame)]

        if i % 2 == 0:
            filtros.append(
                f"[{i}:v]scale=2200:-1,"
                f"zoompan=z='min(zoom+0.0008,1.08)':"
                f"x='iw/2-(iw/zoom/2)':"
                f"y='ih/2-(ih/zoom/2)':"
                f"d={int(duracao_por_frame * 25)}:s={W}x{H}:fps=25,"
                f"setsar=1[v{i}]"
            )
        else:
            filtros.append(
                f"[{i}:v]scale=2200:-1,"
                f"zoompan=z='if(lte(zoom,1.0),1.08,max(zoom-0.0008,1.0))':"
                f"x='iw/2-(iw/zoom/2)':"
                f"y='ih/2-(ih/zoom/2)':"
                f"d={int(duracao_por_frame * 25)}:s={W}x{H}:fps=25,"
                f"setsar=1[v{i}]"
            )

    concat_inputs = "".join(f"[v{i}]" for i in range(len(frames)))
    filtros.append(f"{concat_inputs}concat=n={len(frames)}:v=1:a=0[vout]")

    srt_escaped = str(srt_path.resolve()).replace("\\", "/").replace(":", "\\:")
    filtros.append(
        f"[vout]drawbox=x=0:y={H-185}:w={W}:h=185:color=black@0.68:t=fill[bg]"
    )
    filtros.append(
        f"[bg]subtitles='{srt_escaped}':force_style='FontName=Arial,FontSize=15,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&H00000000,Outline=2,Shadow=0,Alignment=2,MarginV=52,Bold=1'[vfinal]"
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

    print("[FFMPEG] Montando slideshow...")
    print(f"[FFMPEG] Quantidade de entradas de imagem: {len(frames)}")
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

    print("[AUDIO] Adicionando trilha...")
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

    print("[VIDEO] Concatenando vídeo final...")
    subprocess.run(cmd, check=True)
    return final_path


def montar_video(noticia: dict, audio_path: Path) -> Path:
    duracao = mutagen.mp3.MP3(str(audio_path)).info.length

    frames_brutos = obter_frames_visuais(noticia, quantidade_total=5)
    if not frames_brutos:
        raise RuntimeError("Nenhuma imagem encontrada para montar o vídeo.")

    srt_texto = noticia.get("roteiro_legenda") or noticia.get("resumo") or noticia.get("titulo")
    srt_path = gerar_srt_simples(srt_texto, audio_path)

    frames_compostos = [
        compor_frame(img, noticia.get("titulo", "Notícia"), i)
        for i, img in enumerate(frames_brutos)
    ]

    print(f"[VIDEO] Quantidade de frames compostos: {len(frames_compostos)}")

    corpo = montar_slideshow(frames_compostos, audio_path, srt_path, duracao)
    corpo = adicionar_trilha(corpo)
    return concatenar_video(corpo)