from __future__ import annotations

KNOWLEDGE_OUTPUT_CONTRACT = """
Retorne JSON ESTRITO com este esquema:
{
  "answer": "string"
}

Regras de formatação do campo "answer":
- 1 parágrafo curto + marcadores opcionais quando forem úteis.
- Deve estar fundamentado apenas nos trechos de contexto fornecidos (trechos RAG ou de citação web, conforme indicado).
- Não inclua títulos em markdown.
- Não inclua URLs de fontes (a camada da API acrescenta as fontes).
""".strip()
