import subprocess
from pathlib import Path

OUTPUT_DIR = Path("videos_gerados")
OUTPUT_DIR.mkdir(exist_ok=True)

FPS = 30


def run(cmd):
    print("\n[FFMPEG CMD]")
    if isinstance(cmd, list):
        print(" ".join(map(str, cmd)))
    else:
        print(cmd)
    subprocess.run(cmd, check=True)


def limpar_clips_antigos():
    for pattern in ["clip_*.mp4", "video_sem_audio.mp4", "video_final.mp4", "lista.txt", "legenda.srt"]:
        for f in OUTPUT_DIR.glob(pattern):
            f.unlink(missing_ok=True)


def get_audio_duration(audio_path: Path) -> float:
    cmd = [
        "ffprobe",
        "-i", str(audio_path),
        "-show_entries", "format=duration",
        "-v", "quiet",
        "-of", "csv=p=0",
    ]
    result = subprocess.check_output(cmd).decode().strip()
    return float(result)


def criar_clipe_com_zoom(img_path: Path, duracao: float, index: int) -> Path:
    out = OUTPUT_DIR / f"clip_{index}.mp4"
    frames = max(1, int(duracao * FPS))

    vf = (
        f"scale=1080:1920:force_original_aspect_ratio=increase,"
        f"crop=1080:1920,"
        f"zoompan=z='min(zoom+0.001,1.1)':"
        f"d={frames}:"
        f"x='iw/2-(iw/zoom/2)':"
        f"y='ih/2-(ih/zoom/2)':"
        f"s=1080x1920:fps={FPS}"
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-loop", "1",
        "-i", str(img_path.resolve()),
        "-vf", vf,
        "-t", str(duracao),
        "-pix_fmt", "yuv420p",
        str(out),
    ]

    run(cmd)

    if not out.exists():
        raise RuntimeError(f"Erro ao gerar clip: {out}")

    return out


def gerar_srt(texto: str, duracao_total: float, path: Path):
    linhas = [l.strip() for l in texto.split("\n") if l.strip()]
    dur_por_linha = duracao_total / max(len(linhas), 1)

    def format_time(s):
        h = int(s // 3600)
        m = int((s % 3600) // 60)
        sec = int(s % 60)
        ms = int((s - int(s)) * 1000)
        return f"{h:02}:{m:02}:{sec:02},{ms:03}"

    atual = 0.0
    with open(path, "w", encoding="utf-8") as f:
        for i, linha in enumerate(linhas, 1):
            inicio = atual + 0.3
            fim = inicio + dur_por_linha
            f.write(f"{i}\n")
            f.write(f"{format_time(inicio)} --> {format_time(fim)}\n")
            f.write(linha + "\n\n")
            atual += dur_por_linha


def concatenar_clips(clips):
    lista = OUTPUT_DIR / "lista.txt"
    with open(lista, "w", encoding="utf-8") as f:
        for c in clips:
            f.write(f"file '{c.resolve().as_posix()}'\n")

    out = OUTPUT_DIR / "video_sem_audio.mp4"

    cmd = [
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(lista),
        "-c", "copy",
        str(out),
    ]
    run(cmd)

    if not out.exists():
        raise RuntimeError(f"Erro ao concatenar clips: {out}")

    return out


def adicionar_audio_e_legenda(video: Path, audio: Path, srt: Path) -> Path:
    final = OUTPUT_DIR / "video_final.mp4"
    srt_str = srt.resolve().as_posix().replace(":", "\\:")

    vf = (
        f"subtitles='{srt_str}':"
        f"force_style='Fontsize=80,Outline=3,Shadow=0,MarginV=50,Alignment=2,BackColour=&H80000000'"
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(video),
        "-i", str(audio),
        "-vf", vf,
        "-c:v", "libx264",
        "-c:a", "aac",
        "-shortest",
        str(final),
    ]
    run(cmd)

    if not final.exists():
        raise RuntimeError(f"Erro ao gerar vídeo final: {final}")

    return final


def buscar_imagens():
    imagens = []
    imagens.extend(sorted(OUTPUT_DIR.glob("img_*.jpg")))
    imagens.extend(sorted(OUTPUT_DIR.glob("img_*.png")))
    imagens.extend(sorted(OUTPUT_DIR.glob("*.jpg")))
    imagens.extend(sorted(OUTPUT_DIR.glob("*.png")))

    if not imagens:
        imagens.extend(sorted(Path(".").glob("img_*.jpg")))
        imagens.extend(sorted(Path(".").glob("img_*.png")))
        imagens.extend(sorted(Path(".").glob("*.jpg")))
        imagens.extend(sorted(Path(".").glob("*.png")))

    unicas = []
    vistos = set()
    for img in imagens:
        p = str(img.resolve())
        if p not in vistos:
            vistos.add(p)
            unicas.append(img)

    return unicas


def criar_fallback():
    fallback = OUTPUT_DIR / "fallback.jpg"
    cmd = [
        "ffmpeg",
        "-y",
        "-f", "lavfi",
        "-i", "color=c=black:s=1080x1920:d=1",
        "-frames:v", "1",
        str(fallback),
    ]
    run(cmd)
    return fallback


def montar_video(noticia: dict, audio_path: Path) -> Path:
    print("[VIDEO V2] Iniciando montagem com zoom...")

    limpar_clips_antigos()

    imagens = buscar_imagens()
    print(f"[DEBUG] Imagens encontradas: {[i.name for i in imagens]}")

    if not imagens:
        print("[WARN] Nenhuma imagem encontrada, criando fallback...")
        imagens = [criar_fallback()]

    duracao_total = get_audio_duration(audio_path)
    dur_por_img = duracao_total / len(imagens)

    clips = []
    for i, img in enumerate(imagens):
        print(f"[VIDEO] Criando clipe com zoom: {img.name}")
        clips.append(criar_clipe_com_zoom(img, dur_por_img, i))

    video_base = concatenar_clips(clips)

    srt_path = OUTPUT_DIR / "legenda.srt"
    gerar_srt(noticia["roteiro_legenda"], duracao_total, srt_path)

    final = adicionar_audio_e_legenda(video_base, audio_path, srt_path)

    print("[VIDEO V2] Finalizado")
    return final