import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any
import feedparser
from dotenv import load_dotenv
load_dotenv()

FEEDS_RSS = {
    "g1": "https://g1.globo.com/rss/g1/politica/",
    "uol": "https://rss.uol.com.br/feed/noticias.xml",
    "poder360": "https://www.poder360.com.br/feed/",
    "agencia_brasil": "https://agenciabrasil.ebc.com.br/rss/politica/feed.xml",
    "metropoles": "https://www.metropoles.com/brasil/politica-brasil/feed",
    "senado": "https://www12.senado.leg.br/noticias/rss",
    "google_news": "https://news.google.com/rss/search?q=pol%C3%ADtica+brasil&hl=pt-BR&gl=BR&ceid=BR:pt-419",
}

CACHE_FILE = Path("noticias_vistas.json")
MAX_HORAS = 3

PALAVRAS_POLITICAS = [
    "presidente", "congresso", "senado", "câmara", "camara", "ministro",
    "governo", "eleição", "eleicao", "partido", "deputado", "senador",
    "lula", "bolsonaro", "stf", "tribunal", "voto", "lei", "reforma",
    "pec", "emenda", "medida provisória", "medida provisoria",
    "orçamento", "orcamento", "impeachment", "cpi", "brasília", "brasilia",
]

def carregar_cache() -> Dict[str, str]:
    if CACHE_FILE.exists():
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    return {}

def salvar_cache(cache: Dict[str, str]) -> None:
    CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")

def hash_titulo(titulo: str) -> str:
    return hashlib.md5(titulo.lower().strip().encode()).hexdigest()

def e_recente(data_str: str, horas: int = MAX_HORAS) -> bool:
    try:
        import email.utils
        ts = email.utils.parsedate_to_datetime(data_str)
        return datetime.now(ts.tzinfo) - ts < timedelta(hours=horas)
    except Exception:
        return True

def filtrar_politicas(noticias: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    resultado = []
    for n in noticias:
        texto = f"{n.get('titulo', '')} {n.get('resumo', '')}".lower()
        if any(p in texto for p in PALAVRAS_POLITICAS):
            resultado.append(n)
    return resultado

def coletar_rss(cache: dict) -> list[dict]:
    noticias = []
    for fonte, url in FEEDS_RSS.items():
        print(f"[RSS] Lendo {fonte}: {url}", flush=True)
        try:
            feed = feedparser.parse(url, request_headers={"User-Agent": "Mozilla/5.0"})
            print(f"[RSS] {fonte}: {len(feed.entries)} entradas", flush=True)

            for entry in feed.entries[:10]:
                titulo = entry.get("title", "").strip()
                link = entry.get("link", "")
                data = entry.get("published", "")
                resumo = entry.get("summary", "")[:400]

                if not titulo or not link:
                    continue
                if not e_recente(data):
                    continue

                chave = hash_titulo(titulo)
                if chave in cache:
                    continue

                noticias.append({
                    "fonte": fonte,
                    "titulo": titulo,
                    "link": link,
                    "resumo": resumo,
                    "data": data,
                    "hash": chave,
                })
        except Exception as e:
            print(f"[ERRO RSS] {fonte}: {e}", flush=True)

    return noticias

def coletar_noticias() -> List[Dict[str, Any]]:
    cache = carregar_cache()
    todas = coletar_rss(cache)
    filtradas = filtrar_politicas(todas)

    vistas = {}
    for n in filtradas:
        if n["hash"] not in vistas:
            vistas[n["hash"]] = n

    noticias_unicas = list(vistas.values())

    for n in noticias_unicas:
        cache[n["hash"]] = datetime.now().isoformat()
    cache = dict(list(cache.items())[-500:])
    salvar_cache(cache)

    print(f"[OK] {len(noticias_unicas)} notícias novas coletadas")
    return noticias_unicas

if __name__ == "__main__":
    noticias = coletar_noticias()
    for n in noticias[:5]:
        print(f"\n[{n['fonte'].upper()}] {n['titulo']}")
        print(f"  {n['link']}")
