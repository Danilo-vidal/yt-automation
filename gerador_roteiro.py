import os
import json
from typing import List, Dict, Any
import requests

from dotenv import load_dotenv
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


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
- Baseie-se apenas no conteúdo fornecido
- Não use conhecimento externo
- Não complete lacunas com suposições
- Se faltarem detalhes, admita a limitação de forma natural

Formato obrigatório da resposta:
- JSON puro
- sem markdown
- sem comentários
- sem texto antes ou depois do JSON
""".strip()

def montar_prompt_usuario(noticias: List[Dict[str, Any]]) -> str:
    noticias_json = json.dumps(noticias, ensure_ascii=False, indent=2)
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
- o título deve ter alto potencial de clique
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

Lista de notícias:
{noticias_json}
""".strip()

def chamar_openai(noticias: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not OPENAI_API_KEY:
        raise RuntimeError("Defina a variável de ambiente OPENAI_API_KEY.")

    url = "https://api.openai.com/v1/responses"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": OPENAI_MODEL,
        "input": [
            {"role": "system", "content": [{"type": "input_text", "text": SYSTEM_PROMPT}]},
            {"role": "user", "content": [{"type": "input_text", "text": montar_prompt_usuario(noticias)}]},
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "roteiro_politico",
                "schema": {
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
                        "hashtags": {"type": "array", "items": {"type": "string"}},
                        "palavras_chave": {"type": "array", "items": {"type": "string"}},
                        "cta_final": {"type": "string"},
                    },
                    "required": [
                        "score_viral", "motivo_escolha", "titulo_youtube", "headline_capa",
                        "resumo_noticia", "gancho_abertura", "roteiro", "descricao_youtube",
                        "hashtags", "palavras_chave", "cta_final"
                    ],
                },
            }
        },
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=90)

    print("URL:", url)
    print("STATUS:", resp.status_code)
    print("BODY:", resp.text)

    resp.raise_for_status()
    data = resp.json()

    try:
        output_text = data["output"][0]["content"][0]["text"]
        return json.loads(output_text)
    except Exception as exc:
        raise RuntimeError(f"Não foi possível interpretar a resposta da API: {exc}\nResposta bruta: {data}")

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
    resultado = chamar_openai(noticias_teste)
    salvar_resultado(resultado)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
