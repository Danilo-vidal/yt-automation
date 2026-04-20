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