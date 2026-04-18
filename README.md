# YouTube AI Pipeline

Pipeline em Python para:

1. coletar notícias políticas por RSS
2. escolher a melhor pauta com IA
3. gerar roteiro
4. gerar narração TTS
5. montar vídeo
6. subir no YouTube

## Status
Este pacote já vem com código **real de integração** para:
- coleta RSS
- OpenAI API
- Google Cloud TTS
- YouTube Data API

A montagem de vídeo está pronta com FFmpeg, mas depende de:
- `ffmpeg` instalado
- `openai-whisper` opcional para gerar legendas
- chave do Pexels opcional para imagens

## Estrutura
- `pipeline.py` → orquestra tudo
- `coletor_noticias.py` → RSS
- `gerador_roteiro.py` → OpenAI
- `tts_google.py` → Google Cloud TTS
- `montador_video.py` → slideshow + legenda + concat
- `upload_youtube.py` → upload para YouTube
- `.env.example` → variáveis de ambiente
- `requirements.txt` → dependências Python

## Instalação

### 1) Crie e ative um ambiente virtual
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2) Instale dependências
```powershell
pip install -r requirements.txt
```

### 3) Instale FFmpeg
Baixe e instale FFmpeg no Windows e garanta que `ffmpeg` esteja no PATH.

### 4) Configure variáveis de ambiente
Copie `.env.example` para `.env` e preencha os valores.

No PowerShell, para testar rápido:
```powershell
$env:OPENAI_API_KEY="SUA_CHAVE"
$env:GOOGLE_APPLICATION_CREDENTIALS="C:\caminho\google-tts.json"
$env:YOUTUBE_CLIENT_SECRET_FILE="C:\caminho\client_secret.json"
$env:PEXELS_API_KEY="SUA_CHAVE_PEXELS"
```

## Teste por etapa

### Coleta
```powershell
python coletor_noticias.py
```

### Geração de roteiro
```powershell
python gerador_roteiro.py
```

### Pipeline completo
```powershell
python pipeline.py
```

## Observações
- O upload no YouTube é configurado como `private` por padrão.
- A categoria padrão é `25` (News & Politics).
- O pipeline pula publicação se o score viral for abaixo de 7.
- Se o Pexels não estiver configurado, o montador usa imagens locais em `assets/`.

## Pasta esperada
```text
youtube_pipeline_real/
├── assets/
│   ├── thumb.jpg
│   ├── intro.mp4         # opcional
│   ├── outro.mp4         # opcional
│   ├── logo.png          # opcional
│   └── fonte.ttf         # opcional
├── videos_gerados/
├── .env.example
├── coletor_noticias.py
├── gerador_roteiro.py
├── montador_video.py
├── pipeline.py
├── requirements.txt
├── tts_google.py
└── upload_youtube.py
```
