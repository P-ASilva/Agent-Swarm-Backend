Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path "$PSScriptRoot\..\..").Path
Set-Location $projectRoot

$baseUrl = if ($env:BASE_URL) { $env:BASE_URL } else { "http://localhost:8000" }
$userId = if ($env:SMOKE_SUPPORT_PROFILE_USER_ID) { $env:SMOKE_SUPPORT_PROFILE_USER_ID } else { "smoke-support-profile" }

$health = Invoke-RestMethod -Uri "$baseUrl/health" -Method Get
if ($health.status -ne "ok") {
    throw "Health payload invalid: $($health | ConvertTo-Json -Compress)"
}

$message = @"
Nao consigo entrar na minha conta InfinitePay. Atualize meu perfil de suporte: nome de exibicao SmokeProfilePatch e profile_metadata com chave "smoke_tool" e valor "profile_patch".
"@

$body = @{
    message = $message
    userId  = $userId
} | ConvertTo-Json -Compress

Write-Host ""
Write-Host "=== Smoke suporte - profile_patch ($baseUrl) ==="
Write-Host "GET $baseUrl/health -> status: $($health.status)"
Write-Host "userId:  $userId"
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
    throw "Messages payload invalid (missing status, reply, or traceId)."
}
if (-not $response.reply.Trim()) {
    throw "reply must be non-empty"
}

if ($response.PSObject.Properties.Name -contains "replySource") {
    if ($response.replySource -ne "support") {
        throw "Smoke espera rota support + ferramentas; replySource=$($response.replySource)"
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
Write-Host ""
Write-Host "Reply (text):"
Write-Host $response.reply
Write-Host ""
Write-Host "Check server logs: dispatching agent=support, support tool executed kind=profile_patch"
Write-Host "Smoke OK."
