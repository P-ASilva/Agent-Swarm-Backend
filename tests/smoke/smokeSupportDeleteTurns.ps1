Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path "$PSScriptRoot\..\..").Path
Set-Location $projectRoot

$baseUrl = if ($env:BASE_URL) { $env:BASE_URL } else { "http://localhost:8000" }
$userId = if ($env:SMOKE_SUPPORT_DELETE_USER_ID) { $env:SMOKE_SUPPORT_DELETE_USER_ID } else { "smoke-support-delete" }

$health = Invoke-RestMethod -Uri "$baseUrl/health" -Method Get
if ($health.status -ne "ok") {
    throw "Health payload invalid: $($health | ConvertTo-Json -Compress)"
}

$steps = @(
    "Nao consigo fazer transferencias na minha conta InfinitePay.",
    "Ainda nao consigo concluir uma transferencia; nada funciona.",
    @"
Apague todo o meu historico de chat armazenado de hoje usando suas ferramentas de suporte (delete_turns com escopo "all"). Confirme em portugues brasileiro.
"@
)

Write-Host ""
Write-Host "=== Smoke suporte - delete_turns ($baseUrl) ==="
Write-Host "GET $baseUrl/health -> status: $($health.status)"
Write-Host "userId: $userId"
Write-Host ""

$stepNum = 0
foreach ($msg in $steps) {
    $stepNum++
    Write-Host "--- Etapa ${stepNum} ---"
    Write-Host "message: $($msg.Trim())"

    $body = @{
        message = $msg.Trim()
        userId  = $userId
    } | ConvertTo-Json -Compress

    Write-Host "POST $baseUrl/messages"
    Write-Host "Request JSON:"
    Write-Host $body
    Write-Host ""

    $response = Invoke-RestMethod `
        -Uri "$baseUrl/messages" `
        -Method Post `
        -ContentType "application/json; charset=utf-8" `
        -Body $body

    $responseJson = $response | ConvertTo-Json -Depth 10 -Compress
    Write-Host "Response JSON:"
    Write-Host $responseJson
    Write-Host ""

    if (-not $response.status -or -not $response.reply -or -not $response.traceId) {
        throw "Etapa ${stepNum} envelope invalido (falta status, reply ou traceId)."
    }
    if (-not $response.reply.Trim()) {
        throw "Etapa ${stepNum} resposta vazia."
    }

    if ($response.PSObject.Properties.Name -contains "replySource") {
        if ($response.replySource -ne "support") {
            throw "Etapa ${stepNum}: esperado replySource=support; obtido=$($response.replySource)"
        }
    }

    Write-Host "status:   $($response.status)"
    Write-Host "traceId:  $($response.traceId)"
    if ($null -ne $response.PSObject.Properties["route"]) {
        Write-Host "route:    $($response.route)"
    }
    if ($null -ne $response.PSObject.Properties["replySource"]) {
        Write-Host "replySource: $($response.replySource)"
    }
    Write-Host "Reply (text):"
    Write-Host $response.reply
    Write-Host ""
}

Write-Host "Check server logs: support tool executed kind=delete_turns scope=all"
Write-Host "Smoke OK."
