param(
    [string]$InstallDir = "",
    [string]$AppName = "App Orcamento Familiar",
    [string]$Version = "1.1.0"
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$InstallDrive = [System.IO.Path]::GetPathRoot($Root)
if ([string]::IsNullOrWhiteSpace($InstallDir)) {
    $InstallDir = Join-Path $InstallDrive "App Orcamento Familiar"
}
$SourceDir = Join-Path $Root "dist_personal"
$ExeSource = Join-Path $SourceDir "main_personal.exe"
$DbSource = Join-Path $SourceDir "budget_app.db"
$LegacyInstallDir = Join-Path $env:LOCALAPPDATA "App Orcamento Familiar"
$LegacyExeSource = Join-Path $LegacyInstallDir "AppOrcamentoFamiliar.exe"
$LegacyDbSource = Join-Path $LegacyInstallDir "budget_app.db"
$ExeDest = Join-Path $InstallDir "AppOrcamentoFamiliar.exe"
$DbDest = Join-Path $InstallDir "budget_app.db"
$BackupDir = Join-Path $InstallDir "backups"

if (!(Test-Path -LiteralPath $ExeSource)) {
    if (Test-Path -LiteralPath $LegacyExeSource) {
        $ExeSource = $LegacyExeSource
    }
    else {
        throw "Executavel nao encontrado: $ExeSource"
    }
}

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null

if (Test-Path -LiteralPath $DbDest) {
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    Copy-Item -LiteralPath $DbDest -Destination (Join-Path $BackupDir "budget_app_before_update_$stamp.db") -Force
}
elseif (Test-Path -LiteralPath $DbSource) {
    Copy-Item -LiteralPath $DbSource -Destination $DbDest -Force
}
elseif (Test-Path -LiteralPath $LegacyDbSource) {
    Copy-Item -LiteralPath $LegacyDbSource -Destination $DbDest -Force
}

Copy-Item -LiteralPath $ExeSource -Destination $ExeDest -Force

foreach ($name in @("templates", "static")) {
    $src = Join-Path $Root $name
    $dst = Join-Path $InstallDir $name
    if (Test-Path -LiteralPath $dst) {
        Remove-Item -LiteralPath $dst -Recurse -Force
    }
    Copy-Item -LiteralPath $src -Destination $dst -Recurse -Force
}

$favicon = Join-Path $Root "favicon.ico"
if (Test-Path -LiteralPath $favicon) {
    Copy-Item -LiteralPath $favicon -Destination (Join-Path $InstallDir "favicon.ico") -Force
}

$guia = Join-Path $Root "GUIA_DO_CLIENTE.html"
if (Test-Path -LiteralPath $guia) {
    Copy-Item -LiteralPath $guia -Destination (Join-Path $InstallDir "GUIA_DO_CLIENTE.html") -Force
}

$UninstallScript = Join-Path $InstallDir "desinstalar_preservando_backup.ps1"
@"
`$ErrorActionPreference = "Stop"
`$installDir = "$InstallDir"
`$backupTarget = Join-Path `$env:USERPROFILE "Documents\AppOrcamentoFamiliar_Backups"
New-Item -ItemType Directory -Force -Path `$backupTarget | Out-Null
`$db = Join-Path `$installDir "budget_app.db"
if (Test-Path -LiteralPath `$db) {
    `$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    Copy-Item -LiteralPath `$db -Destination (Join-Path `$backupTarget "budget_app_uninstall_`$stamp.db") -Force
}
Remove-Item -LiteralPath "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\AppOrcamentoFamiliar" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath `$installDir -Recurse -Force
"@ | Set-Content -LiteralPath $UninstallScript -Encoding UTF8

$Shell = New-Object -ComObject WScript.Shell
$DesktopShortcut = Join-Path ([Environment]::GetFolderPath("Desktop")) "$AppName.lnk"
$StartMenuDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\App Orcamento Familiar"
New-Item -ItemType Directory -Force -Path $StartMenuDir | Out-Null
$StartShortcut = Join-Path $StartMenuDir "$AppName.lnk"

foreach ($shortcutPath in @($DesktopShortcut, $StartShortcut)) {
    $Shortcut = $Shell.CreateShortcut($shortcutPath)
    $Shortcut.TargetPath = $ExeDest
    $Shortcut.WorkingDirectory = $InstallDir
    $Shortcut.IconLocation = $ExeDest
    $Shortcut.Description = "Controle financeiro familiar pessoal"
    $Shortcut.Save()
}

$RegPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\AppOrcamentoFamiliar"
New-Item -Path $RegPath -Force | Out-Null
New-ItemProperty -Path $RegPath -Name DisplayName -Value $AppName -PropertyType String -Force | Out-Null
New-ItemProperty -Path $RegPath -Name DisplayVersion -Value $Version -PropertyType String -Force | Out-Null
New-ItemProperty -Path $RegPath -Name Publisher -Value "GiovaniMarketing" -PropertyType String -Force | Out-Null
New-ItemProperty -Path $RegPath -Name InstallLocation -Value $InstallDir -PropertyType String -Force | Out-Null
New-ItemProperty -Path $RegPath -Name DisplayIcon -Value $ExeDest -PropertyType String -Force | Out-Null
New-ItemProperty -Path $RegPath -Name UninstallString -Value "powershell.exe -ExecutionPolicy Bypass -File `"$UninstallScript`"" -PropertyType String -Force | Out-Null
New-ItemProperty -Path $RegPath -Name NoModify -Value 1 -PropertyType DWord -Force | Out-Null
New-ItemProperty -Path $RegPath -Name NoRepair -Value 1 -PropertyType DWord -Force | Out-Null

Write-Output "Instalado em: $InstallDir"
Write-Output "Executavel: $ExeDest"
Write-Output "Banco: $DbDest"
Write-Output "Atalho Desktop: $DesktopShortcut"
