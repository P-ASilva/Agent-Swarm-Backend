Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path "$PSScriptRoot\..\..").Path
Set-Location $projectRoot

$baseUrl = if ($env:BASE_URL) { $env:BASE_URL } else { "http://localhost:8000" }
$userId = if ($env:SMOKE_WEB_SEARCH_USER_ID) { $env:SMOKE_WEB_SEARCH_USER_ID } else { "smoke-web-search" }

$health = Invoke-RestMethod -Uri "$baseUrl/health" -Method Get
if ($health.status -ne "ok") {
    throw "Health payload invalid: $($health | ConvertTo-Json -Compress)"
}

$payload = @{
    message = "What is the current Selic rate in Brazil?"
    userId  = $userId
}

$response = Invoke-RestMethod `
    -Uri "$baseUrl/messages" `
    -Method Post `
    -ContentType "application/json" `
    -Body ($payload | ConvertTo-Json -Compress)

if (-not $response.status -or -not $response.reply -or -not $response.traceId) {
    throw "Messages payload invalid: $($response | ConvertTo-Json -Compress)"
}
if (-not $response.reply.Trim()) {
    throw "reply must be non-empty"
}

Write-Host ""
Write-Host "=== Web search smoke ($baseUrl) ==="
Write-Host "Question: $($payload.message)"
Write-Host "status:   $($response.status)"
Write-Host "traceId:  $($response.traceId)"
Write-Host ""
Write-Host "Answer:"
Write-Host $response.reply
Write-Host ""
Write-Host "Smoke finished (inspect API logs for web search lines if routed to knowledge)."
