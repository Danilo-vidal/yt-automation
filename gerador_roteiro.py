import os
import json
import re
from typing import List, Dict, Any

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

FORMATO_SHORTS = True

SYSTEM_PROMPT = """
Você é um roteirista profissional de canal de notícias curtas sobre política brasileira para YouTube.

Sua função é:
1. analisar uma lista de notícias recebidas em JSON
2. escolher APENAS a notícia com maior potencial viral
3. gerar um roteiro curto, direto e altamente envolvente para vídeo de 90 a 120 segundos
4. devolver a resposta exclusivamente em JSON válido

Critérios para escolher a notícia:
- urgência e recência
- relevância nacional
- presença de nomes fortes da política brasileira
- potencial de polêmica, conflito, tensão institucional ou impacto social
- potencial de clique e retenção
- capacidade de gerar curiosidade imediata

Evite escolher:
- pautas frias
- textos muito técnicos
- notícias sem conflito ou sem consequência prática
- temas excessivamente locais ou burocráticos

Regras do roteiro:
- português do Brasil
- tom jornalístico forte, claro e moderno
- sem enrolação
- abertura com gancho forte nos primeiros 2 segundos
- explicar o fato rapidamente
- destacar por que isso importa
- fechar com CTA curto
- não inventar fatos
- não afirmar algo que não esteja sustentado no texto da notícia
- se houver incerteza, use expressões como "segundo as informações divulgadas" ou "até o momento"
- baseie-se apenas no conteúdo fornecido
- não use conhecimento externo
- não complete lacunas com suposições
- se faltarem detalhes, admita a limitação de forma natural

Regras de estilo:
- evite sensacionalismo excessivo
- evite exageros não sustentados pelo texto
- evite caixa alta desnecessária
- evite erros ortográficos
- prefira títulos fortes, mas críveis
- mantenha urgência com credibilidade jornalística
- a headline da capa deve ser curta, forte e limpa
- o texto deve parecer locução de vídeo curto, não artigo

Formato obrigatório da resposta:
- JSON puro
- sem markdown
- sem comentários
- sem texto antes ou depois do JSON
""".strip()


SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "score_viral": {"type": "number"},
        "motivo_escolha": {"type": "string"},
        "titulo_youtube": {"type": "string"},
        "headline_capa": {"type": "string"},
        "resumo_noticia": {"type": "string"},
        "gancho_abertura": {"type": "string"},
        "roteiro": {"type": "string"},
        "descricao_youtube": {"type": "string"},
        "hashtags": {
            "type": "array",
            "items": {"type": "string"}
        },
        "palavras_chave": {
            "type": "array",
            "items": {"type": "string"}
        },
        "cta_final": {"type": "string"},
    },
    "required": [
        "score_viral",
        "motivo_escolha",
        "titulo_youtube",
        "headline_capa",
        "resumo_noticia",
        "gancho_abertura",
        "roteiro",
        "descricao_youtube",
        "hashtags",
        "palavras_chave",
        "cta_final"
    ],
}


def montar_prompt_usuario(noticias: List[Dict[str, Any]]) -> str:
    noticias_json = json.dumps(noticias[:5], ensure_ascii=False, indent=2)

    return f"""
Analise a lista de notícias abaixo e escolha a de maior potencial viral para um vídeo curto no YouTube.

Quero que você devolva um JSON com os seguintes campos:
- score_viral (0 a 10)
- motivo_escolha
- titulo_youtube
- headline_capa
- resumo_noticia
- gancho_abertura
- roteiro
- descricao_youtube
- hashtags
- palavras_chave
- cta_final

Regras:
- o título deve ter alto potencial de clique, mas soar crível
- a headline_capa deve ser curta, com no máximo 4 palavras
- o roteiro deve ter entre 70 e 120 palavras
- a descrição deve ser otimizada para YouTube SEO
- as hashtags devem ter entre 3 e 8 itens
- as palavras_chave devem ter entre 5 e 12 itens
- o CTA final deve ser curto
- responda apenas com JSON válido
- escreva frases curtas, com ritmo de locução
- evite períodos longos
- use pausas naturais
- escreva como texto para ser narrado, não como artigo
- evite títulos histéricos ou pouco confiáveis
- evite expressões como "decide tudo", "mudou o Brasil agora", "histórico" sem base textual
- se a notícia tiver poucos detalhes, mantenha sobriedade

Lista de notícias:
{noticias_json}
""".strip()


def normalizar_hashtag(tag: str) -> str:
    tag = tag.strip()
    if not tag:
        return tag
    return tag[1:] if tag.startswith("#") else tag


def limitar_lista(valores: List[str], minimo: int, maximo: int) -> List[str]:
    limpos = []
    vistos = set()
    for v in valores:
        v = " ".join(str(v).split()).strip()
        if not v:
            continue
        chave = v.lower()
        if chave not in vistos:
            vistos.add(chave)
            limpos.append(v)
    return limpos[:maximo] if len(limpos) >= minimo else limpos


def limpar_texto_basico(texto: str) -> str:
    texto = texto.strip()
    texto = re.sub(r"\s+", " ", texto)
    texto = texto.replace("queabalala", "que abala")
    texto = texto.replace("  ", " ")
    return texto


def reduzir_exagero_titulo(titulo: str) -> str:
    titulo = limpar_texto_basico(titulo)

    substituicoes = {
        "BOMBA": "Urgente",
        "DECIDE TUDO": "toma decisão",
        "AGORA!": "agora",
        "AGORA": "agora",
        "HISTÓRICA": "importante",
        "HISTORICA": "importante",
    }

    for antigo, novo in substituicoes.items():
        titulo = titulo.replace(antigo, novo)

    titulo = re.sub(r"!{2,}", "!", titulo)
    titulo = re.sub(r"\?{2,}", "?", titulo)

    if len(titulo) > 100:
        titulo = titulo[:100].rstrip()

    return titulo


def limpar_resultado(resultado: Dict[str, Any]) -> Dict[str, Any]:
    resultado["titulo_youtube"] = reduzir_exagero_titulo(
        str(resultado.get("titulo_youtube", ""))
    )

    resultado["headline_capa"] = limpar_texto_basico(
        str(resultado.get("headline_capa", ""))
    )
    resultado["headline_capa"] = " ".join(resultado["headline_capa"].split()[:4])

    resultado["motivo_escolha"] = limpar_texto_basico(
        str(resultado.get("motivo_escolha", ""))
    )
    resultado["resumo_noticia"] = limpar_texto_basico(
        str(resultado.get("resumo_noticia", ""))
    )
    resultado["gancho_abertura"] = limpar_texto_basico(
        str(resultado.get("gancho_abertura", ""))
    )
    resultado["roteiro"] = limpar_texto_basico(
        str(resultado.get("roteiro", ""))
    )
    resultado["descricao_youtube"] = limpar_texto_basico(
        str(resultado.get("descricao_youtube", ""))
    )
    resultado["cta_final"] = limpar_texto_basico(
        str(resultado.get("cta_final", ""))
    )

    hashtags = [normalizar_hashtag(h) for h in resultado.get("hashtags", [])]
    resultado["hashtags"] = limitar_lista(hashtags, 3, 8)

    palavras = [limpar_texto_basico(p) for p in resultado.get("palavras_chave", [])]
    resultado["palavras_chave"] = limitar_lista(palavras, 5, 12)

    try:
        resultado["score_viral"] = float(resultado.get("score_viral", 0))
    except Exception:
        resultado["score_viral"] = 0.0

    return resultado


def chamar_gemini(noticias: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not GEMINI_API_KEY:
        raise RuntimeError("Defina a variável de ambiente GEMINI_API_KEY.")

    client = genai.Client(api_key=GEMINI_API_KEY)

    prompt_completo = f"{SYSTEM_PROMPT}\n\n{montar_prompt_usuario(noticias)}"

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt_completo,
        config=types.GenerateContentConfig(
            temperature=0.7,
            response_mime_type="application/json",
            response_json_schema=SCHEMA,
        ),
    )

    print("MODEL:", GEMINI_MODEL)
    print("RAW RESPONSE:")
    print(response.text)

    try:
        output_text = (response.text or "").strip()
        resultado = json.loads(output_text)
        return limpar_resultado(resultado)
    except Exception as exc:
        raise RuntimeError(
            f"Não foi possível interpretar a resposta do Gemini: {exc}\n"
            f"Resposta bruta: {response}"
        )


def chamar_openai(noticias: List[Dict[str, Any]]) -> Dict[str, Any]:
    # Mantido com o mesmo nome para não quebrar o pipeline atual
    return chamar_gemini(noticias)


def salvar_resultado(resultado: Dict[str, Any], caminho: str = "roteiro_gerado.json") -> None:
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    noticias_teste = [
        {
            "fonte": "g1",
            "titulo": "Congresso discute nova proposta com impacto no orçamento federal",
            "link": "https://exemplo.com/noticia1",
            "resumo": "Parlamentares analisam os efeitos da medida e o impacto nas contas públicas.",
            "data": "2026-04-17T10:00:00",
        },
        {
            "fonte": "uol",
            "titulo": "STF toma decisão sobre tema sensível envolvendo cenário político nacional",
            "link": "https://exemplo.com/noticia2",
            "resumo": "A decisão gerou reação entre aliados e opositores e deve repercutir ao longo do dia.",
            "data": "2026-04-17T11:00:00",
        },
    ]

    resultado = chamar_gemini(noticias_teste)
    salvar_resultado(resultado)
    print("Teste concluído com sucesso.")