from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psycopg

from app.infra.rag_pipeline.chunk import TextChunk
from app.infra.rag_pipeline.fetch import FetchedDocument


def _defaultDatabaseUrl() -> str:
    return os.getenv(
        "DATABASE_URL",
        "postgresql://agent_swarm:agent_swarm@localhost:5432/agent_swarm",
    )


def _vectorLiteral(values: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in values) + "]"


@dataclass
class PgvectorStore:
    databaseUrl: str = _defaultDatabaseUrl()
    schemaVersion: str = "v1"

    def applyMigrations(self, migrationsDir: str | Path = "infra/sql") -> None:
        path = Path(migrationsDir)
        migrationFiles = sorted(path.glob("*.sql"))
        if not migrationFiles:
            raise FileNotFoundError(f"No SQL migrations found in {path}")

        with psycopg.connect(self.databaseUrl, autocommit=True) as connection:
            with connection.cursor() as cursor:
                for migration in migrationFiles:
                    sql = migration.read_text(encoding="utf-8")
                    cursor.execute(sql)

    def startIngestionRun(
        self,
        *,
        runLabel: str,
        runType: str,
        seedManifestHash: str,
        contextPath: str | None,
    ) -> str:
        runId = str(uuid.uuid4())
        with psycopg.connect(self.databaseUrl, autocommit=True) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO rag_ingestion_runs (
                        id,
                        run_label,
                        run_type,
                        status,
                        seed_manifest_hash,
                        context_path
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (runId, runLabel, runType, "running", seedManifestHash, contextPath),
                )
        return runId

    def finishIngestionRun(self, *, runId: str, status: str, stats: dict[str, Any]) -> None:
        with psycopg.connect(self.databaseUrl, autocommit=True) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE rag_ingestion_runs
                    SET status = %s,
                        finished_at = NOW(),
                        stats_json = %s::jsonb
                    WHERE id = %s
                    """,
                    (status, json.dumps(stats), runId),
                )

    def upsertDocumentAndChunks(
        self,
        *,
        document: FetchedDocument,
        chunks: list[TextChunk],
        embeddings: list[list[float]],
        crawlVersion: str,
        embeddingModel: str,
        embeddingDim: int,
        runId: str,
    ) -> tuple[str, int]:
        if len(chunks) != len(embeddings):
            raise ValueError("Number of chunks and embeddings must match.")

        with psycopg.connect(self.databaseUrl, autocommit=False) as connection:
            with connection.cursor() as cursor:
                documentId = str(uuid.uuid4())
                cursor.execute(
                    """
                    INSERT INTO rag_source_documents (
                        id,
                        source_url,
                        canonical_url,
                        title,
                        content_hash,
                        crawl_version,
                        metadata_json
                    )
                    VALUES (
                        %s, %s, %s, %s, md5(%s), %s, %s::jsonb
                    )
                    ON CONFLICT (canonical_url, crawl_version)
                    DO UPDATE SET
                        source_url = EXCLUDED.source_url,
                        title = EXCLUDED.title,
                        content_hash = EXCLUDED.content_hash,
                        fetched_at = NOW(),
                        is_active = TRUE,
                        metadata_json = EXCLUDED.metadata_json
                    RETURNING id
                    """,
                    (
                        documentId,
                        document.sourceUrl,
                        document.canonicalUrl,
                        document.title,
                        document.text,
                        crawlVersion,
                        json.dumps({**document.metadata, "run_id": runId}),
                    ),
                )
                persistedDocumentId = str(cursor.fetchone()[0])

                cursor.execute(
                    """
                    UPDATE rag_chunks
                    SET is_active = FALSE
                    WHERE document_id = %s
                      AND embedding_model = %s
                      AND schema_version = %s
                    """,
                    (persistedDocumentId, embeddingModel, self.schemaVersion),
                )

                inserted = 0
                for chunk, embedding in zip(chunks, embeddings):
                    chunkId = str(uuid.uuid4())
                    cursor.execute(
                        """
                        INSERT INTO rag_chunks (
                            id,
                            document_id,
                            chunk_index,
                            chunk_text,
                            token_count,
                            chunk_hash,
                            embedding_model,
                            embedding_dim,
                            embedding,
                            schema_version
                        )
                        VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s::vector, %s
                        )
                        ON CONFLICT (document_id, chunk_index, schema_version, embedding_model)
                        DO UPDATE SET
                            chunk_text = EXCLUDED.chunk_text,
                            token_count = EXCLUDED.token_count,
                            chunk_hash = EXCLUDED.chunk_hash,
                            embedding_dim = EXCLUDED.embedding_dim,
                            embedding = EXCLUDED.embedding,
                            is_active = TRUE,
                            created_at = NOW()
                        """,
                        (
                            chunkId,
                            persistedDocumentId,
                            chunk.chunkIndex,
                            chunk.text,
                            chunk.tokenCount,
                            chunk.chunkHash,
                            embeddingModel,
                            embeddingDim,
                            _vectorLiteral(embedding),
                            self.schemaVersion,
                        ),
                    )
                    inserted += 1

            connection.commit()
        return persistedDocumentId, inserted

    def querySimilarChunks(
        self,
        *,
        queryEmbedding: list[float],
        topK: int = 5,
        embeddingModel: str | None = None,
    ) -> list[dict[str, Any]]:
        queryVector = _vectorLiteral(queryEmbedding)
        whereClauses = [
            "c.is_active = TRUE",
            "d.is_active = TRUE",
            "c.schema_version = %s",
        ]
        params: list[Any] = [self.schemaVersion]

        if embeddingModel:
            whereClauses.append("c.embedding_model = %s")
            params.append(embeddingModel)

        whereSql = " AND ".join(whereClauses)

        with psycopg.connect(self.databaseUrl, autocommit=True) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT
                        c.id::text,
                        c.chunk_text,
                        c.chunk_index,
                        d.canonical_url,
                        d.title,
                        d.crawl_version,
                        (1 - (c.embedding <=> %s::vector)) AS score
                    FROM rag_chunks c
                    JOIN rag_source_documents d ON d.id = c.document_id
                    WHERE {whereSql}
                    ORDER BY c.embedding <=> %s::vector
                    LIMIT %s
                    """,
                    [queryVector, *params, queryVector, topK],
                )
                rows = cursor.fetchall()

        return [
            {
                "chunk_id": row[0],
                "text": row[1],
                "chunk_index": row[2],
                "source_url": row[3],
                "title": row[4],
                "document_version": row[5],
                "score": float(row[6]),
            }
            for row in rows
        ]
