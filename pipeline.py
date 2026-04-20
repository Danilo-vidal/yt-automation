from pathlib import Path
from dotenv import load_dotenv

from coletor_noticias import coletar_noticias
from gerador_roteiro import chamar_openai, salvar_resultado
from tts_google import gerar_audio_google
from montador_video import montar_video
from gerar_thumbnail import gerar_thumbnail
from youtube_uploader import upload_video

load_dotenv()

AUDIO_PATH = Path("audio.mp3")
ROTEIRO_JSON = Path("roteiro_gerado.json")
THUMB_PATH = Path("videos_gerados/thumb.jpg")


def extrair_url_noticia(resultado: dict, noticias: list) -> str:
    for chave in ["url_noticia", "url", "link", "fonte_url"]:
        valor = resultado.get(chave)
        if valor:
            return valor

    titulo_escolhido = (resultado.get("titulo_youtube") or "").strip().lower()
    resumo_escolhido = (resultado.get("resumo_noticia") or "").strip().lower()

    for noticia in noticias:
        titulo_noticia = (noticia.get("titulo") or noticia.get("title") or "").strip().lower()
        resumo_noticia = (noticia.get("resumo") or noticia.get("description") or "").strip().lower()

        if titulo_escolhido and titulo_noticia and titulo_escolhido in titulo_noticia:
            return noticia.get("url") or noticia.get("link") or ""

        if resumo_escolhido and resumo_noticia and resumo_escolhido[:80] in resumo_noticia:
            return noticia.get("url") or noticia.get("link") or ""

    return ""


def executar_pipeline():
    print("\n[PIPELINE] Iniciando execução...\n")

    noticias = coletar_noticias()
    if not noticias:
        print("[INFO] Nenhuma notícia encontrada.")
        return

    print(f"[COLETA] {len(noticias)} notícias coletadas")

    resultado = chamar_openai(noticias)
    salvar_resultado(resultado, str(ROTEIRO_JSON))

    print(
        f"[IA] Notícia escolhida (score {resultado['score_viral']}): "
        f"{resultado['titulo_youtube']}"
    )

    if resultado["score_viral"] < 5:
        print("[WARN] Score baixo, mas continuando gerando mesmo assim.")

    texto_audio = resultado["roteiro"]
    texto_audio = texto_audio.replace(".", ".\n")
    texto_audio = texto_audio.replace("!", "!\n")
    texto_audio = texto_audio.replace("?", "?\n")
    texto_audio = texto_audio.replace(":", ":\n")

    print("[TTS] Gerando áudio...")
    gerar_audio_google(texto_audio, str(AUDIO_PATH))

    if not AUDIO_PATH.exists():
        raise RuntimeError("Falha ao gerar áudio.")

    url_noticia = extrair_url_noticia(resultado, noticias)
    if url_noticia:
        print(f"[FONTE] URL da notícia identificada: {url_noticia}")
    else:
        print("[FONTE] URL da notícia não encontrada. O vídeo seguirá sem contexto externo da matéria.")

    print("[VIDEO] Montando vídeo...")
    noticia_para_video = {
        "titulo": resultado.get("titulo_youtube", ""),
        "resumo": resultado.get("resumo_noticia", ""),
        "roteiro_legenda": texto_audio,
        "url": url_noticia,
    }

    video_path = montar_video(noticia_para_video, AUDIO_PATH)

    print("[THUMB] Gerando thumbnail...")
    gerar_thumbnail(resultado["headline_capa"])

    if not THUMB_PATH.exists():
        raise RuntimeError(f"Thumbnail não foi criada em {THUMB_PATH}")

    descricao = f"""{resultado.get('resumo_noticia', '')}

#política #notícias #brasil #shorts
"""

    tags = ["política", "notícias", "brasil", "shorts"]

    print("[UPLOAD] Enviando para YouTube...")
    upload_video(
        video_file=str(video_path),
        title=resultado.get("titulo_youtube", "Notícia do dia"),
        description=descricao,
        tags=tags,
        category_id="25",
        privacy_status="private",
        thumbnail_file=str(THUMB_PATH),
    )

    print("\n[SUCESSO]")
    print(f"Vídeo gerado com sucesso em: {video_path}")
    print(f"Thumbnail gerada com sucesso em: {THUMB_PATH}")


if __name__ == "__main__":
    executar_pipeline()