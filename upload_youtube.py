import os
import json
import time
import random
from pathlib import Path
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
load_dotenv()

import google.auth.transport.requests
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CLIENT_SECRET_FILE = os.getenv("YOUTUBE_CLIENT_SECRET_FILE", "client_secret.json")
TOKEN_FILE = os.getenv("YOUTUBE_TOKEN_FILE", "youtube_token.json")
DEFAULT_CATEGORY_ID = "25"

def autenticar_youtube():
    creds = None
    if Path(TOKEN_FILE).exists():
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(google.auth.transport.requests.Request())

    if not creds or not creds.valid:
        if not Path(CLIENT_SECRET_FILE).exists():
            raise FileNotFoundError(f"Arquivo OAuth não encontrado: {CLIENT_SECRET_FILE}")
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
        creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

    return build("youtube", "v3", credentials=creds)

def carregar_metadata(json_path: str) -> Dict[str, Any]:
    caminho = Path(json_path)
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo de metadata não encontrado: {json_path}")
    with open(caminho, "r", encoding="utf-8") as f:
        return json.load(f)

def normalizar_tags(tags: Optional[List[str]]) -> List[str]:
    if not tags:
        return []
    return [str(t).strip() for t in tags if str(t).strip()]

def montar_descricao(metadata: Dict[str, Any]) -> str:
    descricao_base = metadata.get("descricao_youtube", "").strip()
    hashtags = " ".join(normalizar_tags(metadata.get("hashtags", [])))
    blocos = [descricao_base]
    if metadata.get("palavras_chave"):
        blocos.append("Palavras-chave: " + ", ".join(normalizar_tags(metadata["palavras_chave"])))
    if hashtags:
        blocos.append(hashtags)
    return "\n\n".join([b for b in blocos if b])

def upload_resumable(request, max_retries: int = 10) -> Dict[str, Any]:
    response = None
    retry = 0
    retriable_status_codes = [500, 502, 503, 504]

    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                progresso = int(status.progress() * 100)
                print(f"[UPLOAD] Progresso: {progresso}%")
        except HttpError as e:
            if e.resp.status in retriable_status_codes:
                retry += 1
                if retry > max_retries:
                    raise RuntimeError("Limite de tentativas excedido no upload.") from e
                sleep_seconds = random.uniform(1, 2 ** retry)
                print(f"[RETRY] Erro HTTP {e.resp.status}. Nova tentativa em {sleep_seconds:.1f}s")
                time.sleep(sleep_seconds)
            else:
                raise
        except Exception as e:
            retry += 1
            if retry > max_retries:
                raise RuntimeError("Limite de tentativas excedido no upload.") from e
            sleep_seconds = random.uniform(1, 2 ** retry)
            print(f"[RETRY] Erro inesperado: {e}. Nova tentativa em {sleep_seconds:.1f}s")
            time.sleep(sleep_seconds)
    return response

def enviar_video(youtube, video_path: str, titulo: str, descricao: str, tags: Optional[List[str]] = None,
                 category_id: str = DEFAULT_CATEGORY_ID, privacy_status: str = "private",
                 publish_at: Optional[str] = None, self_declared_made_for_kids: bool = False) -> str:
    caminho_video = Path(video_path)
    if not caminho_video.exists():
        raise FileNotFoundError(f"Vídeo não encontrado: {video_path}")

    body = {
        "snippet": {
            "title": titulo[:100],
            "description": descricao[:5000],
            "tags": normalizar_tags(tags),
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": self_declared_made_for_kids,
        },
    }

    if publish_at and privacy_status == "private":
        body["status"]["publishAt"] = publish_at

    media = MediaFileUpload(
        filename=str(caminho_video),
        chunksize=-1,
        resumable=True,
        mimetype="video/*",
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    print("[YOUTUBE] Iniciando upload do vídeo...")
    response = upload_resumable(request)
    video_id = response["id"]
    print(f"[YOUTUBE] Upload concluído. Video ID: {video_id}")
    return video_id

def enviar_thumbnail(youtube, video_id: str, thumbnail_path: str) -> None:
    caminho_thumb = Path(thumbnail_path)
    if not caminho_thumb.exists():
        raise FileNotFoundError(f"Thumbnail não encontrada: {thumbnail_path}")

    media = MediaFileUpload(
        filename=str(caminho_thumb),
        mimetype="image/jpeg" if caminho_thumb.suffix.lower() in [".jpg", ".jpeg"] else "image/png",
        resumable=False,
    )

    youtube.thumbnails().set(videoId=video_id, media_body=media).execute()
    print("[YOUTUBE] Thumbnail aplicada com sucesso.")

def publicar_do_json(video_path: str, metadata_json: str = "roteiro_gerado.json",
                     thumbnail_path: Optional[str] = None, privacy_status: str = "private",
                     publish_at: Optional[str] = None) -> str:
    youtube = autenticar_youtube()
    metadata = carregar_metadata(metadata_json)

    titulo = metadata.get("titulo_youtube", "Últimas notícias de política")
    descricao = montar_descricao(metadata)
    tags = metadata.get("hashtags", []) + metadata.get("palavras_chave", [])

    video_id = enviar_video(
        youtube=youtube,
        video_path=video_path,
        titulo=titulo,
        descricao=descricao,
        tags=tags,
        privacy_status=privacy_status,
        publish_at=publish_at,
        self_declared_made_for_kids=False,
    )

    if thumbnail_path:
        try:
            enviar_thumbnail(youtube, video_id, thumbnail_path)
        except Exception as e:
            print(f"[WARN] Vídeo subiu, mas a thumbnail falhou: {e}")

    return video_id
