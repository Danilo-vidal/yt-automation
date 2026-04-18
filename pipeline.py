from pathlib import Path
from dotenv import load_dotenv

from coletor_noticias import coletar_noticias
from gerador_roteiro import chamar_openai, salvar_resultado
from tts_google import gerar_audio_google
from montador_video import montar_video
from gerar_thumbnail import gerar_thumbnail

load_dotenv()

AUDIO_PATH = Path("audio.mp3")
ROTEIRO_JSON = Path("roteiro_gerado.json")

def executar_pipeline():
    print("\n[PIPELINE] Iniciando execução...\n")

    noticias = coletar_noticias()
    print("[WARN] Nenhuma nova. Reutilizando últimas.")
    from coletor_noticias import carregar_noticias_antigas
    noticias = carregar_noticias_antigas()

    print(f"[COLETA] {len(noticias)} notícias coletadas")

    resultado = chamar_openai(noticias)
    salvar_resultado(resultado, str(ROTEIRO_JSON))

    print(f"[IA] Notícia escolhida (score {resultado['score_viral']}): {resultado['titulo_youtube']}")

    if resultado["score_viral"] < 7:
     print("[WARN] Score baixo, mas gerando mesmo assim.")
    return

    print("[THUMB] Gerando thumbnail...")
    gerar_thumbnail(resultado["headline_capa"])

    texto_audio = resultado["roteiro"]
    texto_audio = texto_audio.replace(".", ".\n")
    texto_audio = texto_audio.replace("!", "!\n")
    texto_audio = texto_audio.replace("?", "?\n")
    texto_audio = texto_audio.replace(":", ":\n")

    print("[TTS] Gerando áudio...")
    gerar_audio_google(texto_audio, str(AUDIO_PATH))

    if not AUDIO_PATH.exists():
        raise RuntimeError("Falha ao gerar áudio.")

    print("[VIDEO] Montando vídeo...")
    noticia_para_video = {
        "titulo": resultado["titulo_youtube"],
        "resumo": resultado["resumo_noticia"],
    }

    video_path = montar_video(noticia_para_video, AUDIO_PATH)

    print("\n[SUCESSO]")
    print(f"Vídeo gerado com sucesso em: {video_path}")

if __name__ == "__main__":
    executar_pipeline()