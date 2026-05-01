Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path "$PSScriptRoot\..\..").Path
Set-Location $projectRoot

$baseUrl = if ($env:BASE_URL) { $env:BASE_URL } else { "http://localhost:8000" }

$health = Invoke-RestMethod -Uri "$baseUrl/health" -Method Get
if ($health.status -ne "ok") {
    throw "Health payload invalid: $($health | ConvertTo-Json -Compress)"
}

$payload = @{
    message = "Como usar o celular como maquininha de cartão?"
    userId = "client789"
}

$response = Invoke-RestMethod `
    -Uri "$baseUrl/messages" `
    -Method Post `
    -ContentType "application/json" `
    -Body ($payload | ConvertTo-Json -Compress)

if (-not $response.status -or -not $response.reply -or -not $response.traceId) {
    throw "Messages payload invalid: $($response | ConvertTo-Json -Compress)"
}

try {
    Invoke-RestMethod `
        -Uri "$baseUrl/messages" `
        -Method Post `
        -ContentType "application/json" `
        -Body "{}" | Out-Null
    throw "Expected invalid payload to return HTTP 422."
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    if ($statusCode -ne 422) {
        throw "Expected HTTP 422 for invalid payload, got: $statusCode"
    }
}

Write-Host "Smoke Docker concluído: /health e /messages respondem em $baseUrl."
