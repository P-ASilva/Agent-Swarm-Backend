Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path "$PSScriptRoot\..\..").Path
Set-Location $projectRoot

$baseUrl = if ($env:BASE_URL) { $env:BASE_URL } else { "http://localhost:8000" }
$userId = if ($env:SMOKE_SUPPORT_PROFILE_FLOW_USER_ID) {
    $env:SMOKE_SUPPORT_PROFILE_FLOW_USER_ID
} else {
    "smoke-pf-{0}" -f ([Guid]::NewGuid().ToString("n").Substring(0, 12))
}

function Assert-Envelope {
    param([string]$Label, $Resp)
    if (-not $Resp.status -or -not $Resp.reply -or -not $Resp.traceId) {
        throw "${Label}: envelope invalido (status, reply ou traceId)."
    }
    if (-not $Resp.reply.Trim()) {
        throw "${Label}: resposta vazia."
    }
    if ($Resp.PSObject.Properties.Name -contains "replySource") {
        if ($Resp.replySource -ne "support") {
            throw "${Label}: esperado replySource=support; obtido=$($Resp.replySource)"
        }
    }
}

function Invoke-Messages {
    param([string]$Msg)
    $body = @{
        message = $Msg.Trim()
        userId  = $userId
    } | ConvertTo-Json -Compress
    Write-Host "POST $baseUrl/messages"
    Write-Host "Request JSON:"
    Write-Host $body
    Write-Host ""
    $r = Invoke-RestMethod `
        -Uri "$baseUrl/messages" `
        -Method Post `
        -ContentType "application/json; charset=utf-8" `
        -Body $body
    Write-Host "Response JSON:"
    Write-Host ($r | ConvertTo-Json -Depth 10 -Compress)
    Write-Host ""
    return $r
}

$health = Invoke-RestMethod -Uri "$baseUrl/health" -Method Get
if ($health.status -ne "ok") {
    throw "Health invalid: $($health | ConvertTo-Json -Compress)"
}

Write-Host ""
Write-Host "=== Smoke suporte - fluxo perfil (pergunta / dados / confirmacao) ($baseUrl) ==="
Write-Host "GET $baseUrl/health -> status: $($health.status)"
Write-Host "userId: $userId"
Write-Host ""

# 1) Pergunta apenas o que ha guardado; orientacao de campos vem do prompt de suporte (modeling).
$q1 = "Quais informacoes do meu perfil de suporte estao salvas nesta conta?"
Write-Host "--- Passo 1: consultar perfil ---"
$r1 = Invoke-Messages $q1
Assert-Envelope "Passo 1" $r1
if ($r1.reply -notmatch "Dados confirmados") {
    throw "Passo 1: resposta deveria incluir bloco de perfil confirmado (SupportAgent)."
}
$lower1 = $r1.reply.ToLowerInvariant()
if ($lower1 -notmatch "vazio" -and $lower1 -notmatch "nao definido" -and $lower1 -notmatch "não definido") {
    throw "Passo 1: esperado perfil vazio no bloco confirmado (use userId unico ou limpe a sessao)."
}
if ($lower1 -notmatch "nome" -or ($lower1 -notmatch "metadado" -and $lower1 -notmatch "metadata")) {
    throw "Passo 1: com perfil vazio, o system prompt de suporte deve orientar nome de exibicao e metadados."
}
Write-Host "Reply (text):"
Write-Host $r1.reply
Write-Host ""

# 2) Utilizador envia dados; bot aplica profile_patch no banco.
$q2 = @"
Atualize meu perfil de suporte agora: nome de exibicao SmokeProfileFlow e profile_metadata com chaves ""empresa"" valor ""InfinitePayFlow"" e ""funcao"" valor ""teste-smoke"".
"@
Write-Host "--- Passo 2: enviar dados para gravar ---"
$r2 = Invoke-Messages $q2
Assert-Envelope "Passo 2" $r2
if ($r2.reply -notmatch "SmokeProfileFlow") {
    throw "Passo 2: resposta deveria refletir nome gravado SmokeProfileFlow (verifique profile_patch e DB)."
}
if ($r2.reply -notmatch "InfinitePayFlow" -or $r2.reply -notmatch "teste-smoke") {
    throw "Passo 2: resposta deveria incluir metadados empresa/funcao gravados."
}
Write-Host "Reply (text):"
Write-Host $r2.reply
Write-Host ""

# 3) Confirmacao a partir do estado persistido.
$q3 = "Confirme novamente: qual o nome de exibicao e os metadados empresa e funcao gravados no meu perfil (como no banco)?"
Write-Host "--- Passo 3: confirmar leitura do banco ---"
$r3 = Invoke-Messages $q3
Assert-Envelope "Passo 3" $r3
if ($r3.reply -notmatch "SmokeProfileFlow") {
    throw "Passo 3: modelo deveria ler nome persistido SmokeProfileFlow."
}
if ($r3.reply -notmatch "InfinitePayFlow" -or $r3.reply -notmatch "teste-smoke") {
    throw "Passo 3: modelo deveria citar metadados persistidos."
}
Write-Host "Reply (text):"
Write-Host $r3.reply
Write-Host ""

Write-Host "Check logs: passo 2 com support tool profile_patch; passo 3 PERFIL_ATUAL do banco."
Write-Host "Smoke OK."
