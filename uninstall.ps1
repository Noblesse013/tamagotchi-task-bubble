$ErrorActionPreference = 'Stop'

$installRoot = Join-Path $env:LOCALAPPDATA 'Programs\TaskBubble'
$desktopLink = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Task Bubble.lnk'
$startupLink = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup\Task Bubble.lnk'

foreach ($linkPath in @($desktopLink, $startupLink)) {
    if (Test-Path -LiteralPath $linkPath) {
        Remove-Item -LiteralPath $linkPath -Force
    }
}

if (Test-Path -LiteralPath $installRoot) {
    Remove-Item -LiteralPath $installRoot -Recurse -Force
}

Write-Host 'Task Bubble and its shortcuts were removed. Your saved tasks were kept.'
