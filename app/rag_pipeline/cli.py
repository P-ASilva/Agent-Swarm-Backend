from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, UTC

from app.rag_pipeline.embed import buildEmbeddingProviderFromEnv
from app.rag_pipeline.service import RagIngestionService
from app.rag_pipeline.store import PgvectorStore


def _buildParser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="RAG pipeline CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    defaultManifestPath = os.getenv("RAG_SEED_URLS_PATH", "app/rag_pipeline/seedUrls.json")

    for commandName, helpText in (
        ("ingest", "Run ingestion pipeline."),
        ("reindex", "Run ingestion pipeline using reindex run type."),
    ):
        sub = subparsers.add_parser(commandName, help=helpText)
        sub.add_argument("--context-path", default=None)
        sub.add_argument("--manifest-path", default=defaultManifestPath)
        sub.add_argument("--seed-url", action="append", default=None)
        sub.add_argument("--crawl-version", default=datetime.now(UTC).strftime("%Y%m%d"))
        sub.add_argument("--max-pages", type=int, default=None)
        sub.add_argument("--chunk-size", type=int, default=1200)
        sub.add_argument("--chunk-overlap", type=int, default=150)
        sub.add_argument("--run-label", default=None)

    addUrl = subparsers.add_parser(
        "add-url",
        help="Ingest one or more explicit URLs into the RAG store.",
    )
    addUrl.add_argument("--url", action="append", required=True)
    addUrl.add_argument("--crawl-version", default=datetime.now(UTC).strftime("%Y%m%d"))
    addUrl.add_argument("--max-pages", type=int, default=None)
    addUrl.add_argument("--chunk-size", type=int, default=1200)
    addUrl.add_argument("--chunk-overlap", type=int, default=150)
    addUrl.add_argument("--run-label", default=None)

    migrate = subparsers.add_parser("migrate", help="Apply SQL migrations.")
    migrate.add_argument("--migrations-dir", default="infra/sql")

    query = subparsers.add_parser("query", help="Run similarity query against stored chunks.")
    query.add_argument("--query", required=True)
    query.add_argument("--top-k", type=int, default=5)
    query.add_argument("--embedding-model", default=None)
    query.add_argument("--pretty", action="store_true")

    return parser


def _runIngestion(args: argparse.Namespace, *, runType: str) -> int:
    explicitUrls = list(args.seed_url or [])
    if hasattr(args, "url") and args.url:
        explicitUrls.extend(args.url)
    explicitUrls = explicitUrls or None

    service = RagIngestionService.fromEnv()
    result = service.run(
        runType=runType,
        contextPath=args.context_path,
        explicitUrls=explicitUrls,
        manifestPath=args.manifest_path,
        crawlVersion=args.crawl_version,
        maxPages=args.max_pages,
        chunkSize=args.chunk_size,
        chunkOverlap=args.chunk_overlap,
        runLabel=args.run_label,
    )
    print(
        json.dumps(
            {
                "run_id": result.runId,
                "status": result.status,
                "stats": {
                    "documents_processed": result.documentsProcessed,
                    "chunks_written": result.chunksWritten,
                    "embedding_model": service.embeddingProvider.modelName,
                    "embedding_dim": service.embeddingProvider.embeddingDim,
                    "seed_url_count": result.seedUrlCount,
                },
            },
            indent=2,
        )
    )
    return 0


def _runQuery(args: argparse.Namespace) -> int:
    embeddingProvider = buildEmbeddingProviderFromEnv()
    store = PgvectorStore()
    queryEmbedding = embeddingProvider.embedTexts([args.query])[0]
    result = store.querySimilarChunks(
        queryEmbedding=queryEmbedding,
        topK=args.top_k,
        embeddingModel=args.embedding_model or embeddingProvider.modelName,
    )
    print(json.dumps(result, indent=2 if args.pretty else None))
    return 0


def main() -> int:
    parser = _buildParser()
    args = parser.parse_args()

    if args.command == "migrate":
        store = PgvectorStore()
        store.applyMigrations(migrationsDir=args.migrations_dir)
        print("Migrations applied successfully.")
        return 0

    if args.command == "ingest":
        return _runIngestion(args, runType="ingest")

    if args.command == "reindex":
        return _runIngestion(args, runType="reindex")

    if args.command == "query":
        return _runQuery(args)

    if args.command == "add-url":
        args.seed_url = args.url
        args.context_path = None
        args.manifest_path = None
        return _runIngestion(args, runType="add-url")

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
