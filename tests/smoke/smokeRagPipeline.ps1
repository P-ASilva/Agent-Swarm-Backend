Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path "$PSScriptRoot\..\..").Path
Set-Location $projectRoot

Write-Host "=== RAG smoke: starting pgvector service ==="
docker compose up -d postgres

if (Test-Path ".\venv\Scripts\python.exe") {
    $python = ".\venv\Scripts\python.exe"
} elseif (Test-Path ".\.venv\Scripts\python.exe") {
    $python = ".\.venv\Scripts\python.exe"
} else {
    $python = "python"
}

$env:DATABASE_URL = if ($env:DATABASE_URL) { $env:DATABASE_URL } else { "postgresql://agent_swarm:agent_swarm@localhost:5432/agent_swarm" }
$tapPath = (Resolve-Path "tests/fixtures/rag/infinitepay_tap_to_pay.html").Path.Replace("\", "/")
$boletoPath = (Resolve-Path "tests/fixtures/rag/infinitepay_boleto.html").Path.Replace("\", "/")
$tapUrl = "file:///$tapPath"
$boletoUrl = "file:///$boletoPath"

Write-Host "=== RAG smoke: applying migrations ==="
& $python -m app.rag_pipeline.cli migrate

Write-Host "=== RAG smoke: ingesting fixture content ==="
& $python -m app.rag_pipeline.cli ingest `
  --seed-url $tapUrl `
  --seed-url $boletoUrl `
  --crawl-version smoke-v1 `
  --max-pages 2 `
  --run-label smoke-rag

Write-Host "=== RAG smoke: querying stored chunks ==="
$queryResult = & $python -m app.rag_pipeline.cli query `
  --query "phone card machine" `
  --top-k 1 `
  --pretty
Write-Host $queryResult

if (-not $queryResult -or $queryResult -notmatch "source_url") {
    throw "Expected query output to include source_url."
}

Write-Host "RAG pipeline smoke checks passed."
