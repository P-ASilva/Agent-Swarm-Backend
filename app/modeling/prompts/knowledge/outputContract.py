KNOWLEDGE_OUTPUT_CONTRACT = """
Return STRICT JSON with this schema:
{
  "answer": "string"
}

Formatting rules for "answer":
- 1 short paragraph + optional bullets when useful.
- Must be grounded in provided context snippets only (RAG excerpts or web-citation excerpts, as labeled).
- Must not include markdown headings.
- Must not include source URLs (sources are appended by the API layer).
""".strip()

