# Instala o salvamento automatico das conversas do Claude Code no Obsidian.
# Uso (PowerShell, na pasta onde baixou este arquivo):
#   powershell -NoProfile -ExecutionPolicy Bypass -File .\instalar-obsidian.ps1
#
# O que faz:
#   1. Cria  %USERPROFILE%\.claude\hooks\save-to-obsidian.ps1
#   2. Adiciona um hook "Stop" em %USERPROFILE%\.claude\settings.json (faz backup antes)
#   3. Exporta as conversas que ja existem em %USERPROFILE%\.claude\projects

param(
    [string]$Vault = 'C:\Users\claud\ObsidianVault',
    [string]$Subpasta = 'Claude'
)

$ErrorActionPreference = 'Stop'

$hookScript = @'
param([string]$TranscriptPath, [string]$SessionId)

$Vault  = '__VAULT__'
$Folder = Join-Path $Vault '__SUBPASTA__'
$ErrorActionPreference = 'Stop'

function Clean-Name([string]$s) {
    $s = ($s -replace '[\r\n\t]+', ' ') -replace '[\\/:*?"<>|#^\[\]]', ' '
    $s = ($s -replace '\s+', ' ').Trim()
    if ($s.Length -gt 60) { $s = $s.Substring(0, 60).Trim() }
    if (-not $s) { $s = 'conversa' }
    return $s
}

try {
    if (-not $TranscriptPath) {
        $in = [Console]::In.ReadToEnd() | ConvertFrom-Json
        $TranscriptPath = [string]$in.transcript_path
        $SessionId = [string]$in.session_id
    }
    if (-not $TranscriptPath -or -not (Test-Path -LiteralPath $TranscriptPath)) { exit 0 }
    if (-not $SessionId) { $SessionId = [IO.Path]::GetFileNameWithoutExtension($TranscriptPath) }

    $msgs  = New-Object System.Collections.Generic.List[object]
    $first = $null
    $start = $null
    $cwd   = $null

    foreach ($line in [IO.File]::ReadAllLines($TranscriptPath, [Text.Encoding]::UTF8)) {
        if (-not $line.Trim()) { continue }
        try { $d = $line | ConvertFrom-Json } catch { continue }
        if ($d.type -ne 'user' -and $d.type -ne 'assistant') { continue }
        if ($d.isMeta -or $d.isSidechain) { continue }
        if (-not $cwd -and $d.cwd) { $cwd = [string]$d.cwd }

        $c = $d.message.content
        if ($c -is [string]) {
            $text = $c
        } else {
            $parts = @()
            foreach ($b in @($c)) { if ($b.type -eq 'text' -and $b.text) { $parts += [string]$b.text } }
            $text = $parts -join "`n`n"
        }
        $text = $text.Trim()
        if (-not $text) { continue }
        # ignora mensagens internas (<command-...>, <system-reminder> etc.)
        if ($d.type -eq 'user' -and $text.StartsWith('<')) { continue }

        if (-not $start -and $d.timestamp) { try { $start = ([datetime]$d.timestamp).ToLocalTime() } catch {} }
        if ($d.type -eq 'user' -and -not $first) { $first = $text }

        # junta respostas seguidas do mesmo autor
        if ($msgs.Count -gt 0 -and $msgs[$msgs.Count - 1].role -eq $d.type) {
            $msgs[$msgs.Count - 1].text += "`n`n" + $text
        } else {
            $msgs.Add([pscustomobject]@{ role = [string]$d.type; text = $text })
        }
    }

    if ($msgs.Count -eq 0) { exit 0 }
    if (-not $start) { $start = (Get-Item -LiteralPath $TranscriptPath).CreationTime }

    $title = Clean-Name $first
    $short = if ($SessionId.Length -ge 8) { $SessionId.Substring(0, 8) } else { $SessionId }
    $file  = '{0} {1} ({2}).md' -f $start.ToString('yyyy-MM-dd HHmm'), $title, $short

    New-Item -ItemType Directory -Force -Path $Folder | Out-Null

    $sb = New-Object System.Text.StringBuilder
    [void]$sb.AppendLine('---')
    [void]$sb.AppendLine("date: $($start.ToString('yyyy-MM-dd HH:mm'))")
    [void]$sb.AppendLine("session_id: $SessionId")
    if ($cwd) { [void]$sb.AppendLine("cwd: '" + ($cwd -replace "'", "''") + "'") }
    [void]$sb.AppendLine('tags: [claude, conversa]')
    [void]$sb.AppendLine('---')
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine("# $title")
    [void]$sb.AppendLine('')
    foreach ($m in $msgs) {
        $who = if ($m.role -eq 'user') { '## Você' } else { '## Claude' }
        [void]$sb.AppendLine($who)
        [void]$sb.AppendLine('')
        [void]$sb.AppendLine($m.text)
        [void]$sb.AppendLine('')
    }

    [IO.File]::WriteAllText((Join-Path $Folder $file), $sb.ToString(), (New-Object Text.UTF8Encoding $false))
} catch {
    try {
        New-Item -ItemType Directory -Force -Path $Folder | Out-Null
        Add-Content -LiteralPath (Join-Path $Folder '_erros-hook.log') -Value ("{0}  {1}" -f (Get-Date), $_)
    } catch {}
}
exit 0
'@

$hookScript = $hookScript.Replace('__VAULT__', $Vault.Replace("'", "''")).Replace('__SUBPASTA__', $Subpasta.Replace("'", "''"))

# 1. grava o script do hook (UTF-8 com BOM para o Windows PowerShell ler os acentos)
$claudeDir  = Join-Path $env:USERPROFILE '.claude'
$hooksDir   = Join-Path $claudeDir 'hooks'
New-Item -ItemType Directory -Force -Path $hooksDir | Out-Null
$scriptPath = Join-Path $hooksDir 'save-to-obsidian.ps1'
[IO.File]::WriteAllText($scriptPath, $hookScript, (New-Object Text.UTF8Encoding $true))
Write-Host "Script criado: $scriptPath"

# 2. adiciona o hook Stop no settings.json, preservando o que ja existe
$settingsPath = Join-Path $claudeDir 'settings.json'
$cmd = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "' + ($scriptPath -replace '\\', '/') + '"'

if (Test-Path -LiteralPath $settingsPath) {
    $backup = "$settingsPath.bak-" + (Get-Date -Format 'yyyyMMdd-HHmmss')
    Copy-Item -LiteralPath $settingsPath -Destination $backup
    Write-Host "Backup: $backup"
    $raw = [IO.File]::ReadAllText($settingsPath, [Text.Encoding]::UTF8)
    if ($raw.Trim()) { $settings = $raw | ConvertFrom-Json } else { $settings = New-Object psobject }
} else {
    $settings = New-Object psobject
}

if (-not ($settings.PSObject.Properties.Name -contains 'hooks')) {
    $settings | Add-Member -NotePropertyName hooks -NotePropertyValue (New-Object psobject)
}
$hooks = $settings.hooks
$stop = @()
if ($hooks.PSObject.Properties.Name -contains 'Stop') { $stop = @($hooks.Stop) }

$already = $false
foreach ($group in $stop) { foreach ($h in @($group.hooks)) { if ([string]$h.command -like '*save-to-obsidian*') { $already = $true } } }

if ($already) {
    Write-Host 'O hook ja estava configurado; settings.json nao foi alterado.'
} else {
    $entry = [pscustomobject]@{
        hooks = @([pscustomobject]@{ type = 'command'; command = $cmd; timeout = 30 })
    }
    $stop += $entry
    if ($hooks.PSObject.Properties.Name -contains 'Stop') { $hooks.Stop = $stop }
    else { $hooks | Add-Member -NotePropertyName Stop -NotePropertyValue $stop }
    $json = ConvertTo-Json -InputObject $settings -Depth 32
    [IO.File]::WriteAllText($settingsPath, $json, (New-Object Text.UTF8Encoding $false))
    Write-Host "Hook adicionado em: $settingsPath"
}

# 3. exporta as conversas que ja existem
$projects = Join-Path $claudeDir 'projects'
$n = 0
if (Test-Path -LiteralPath $projects) {
    Get-ChildItem -LiteralPath $projects -Recurse -Filter '*.jsonl' |
        Where-Object { $_.FullName -notmatch '\\subagents\\' } |
        ForEach-Object {
            & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $scriptPath -TranscriptPath $_.FullName
            $n++
        }
}
Write-Host "Conversas antigas processadas: $n"
Write-Host "Pronto. As notas ficam em: $(Join-Path $Vault $Subpasta)"
Write-Host 'Reinicie o Claude Code (ou abra /hooks) para o hook comecar a valer.'
