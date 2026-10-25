$ErrorActionPreference = 'Stop'

$sourceRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$installRoot = Join-Path $env:LOCALAPPDATA 'Programs\TaskBubble'
$startupFolder = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup'
$desktopLink = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Task Bubble.lnk'
$startupLink = Join-Path $startupFolder 'Task Bubble.lnk'
$releaseExe = Join-Path $sourceRoot 'TaskBubble.exe'

New-Item -ItemType Directory -Path $installRoot -Force | Out-Null

if (Test-Path -LiteralPath $releaseExe) {
    Copy-Item -LiteralPath $releaseExe -Destination (Join-Path $installRoot 'TaskBubble.exe') -Force
    $launchTarget = Join-Path $installRoot 'TaskBubble.exe'
    $launchArgs = ''
    $iconLocation = $launchTarget
} else {
    $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
    if (-not $pythonCommand) {
        throw 'Python 3.10 or newer is required for a source install. Install Python from python.org, then run this installer again.'
    }
    $pythonExe = $pythonCommand.Source
    $version = & $pythonExe -c 'import sys; print(".".join(map(str, sys.version_info[:2])))'
    $parts = $version.Trim().Split('.')
    if ([int]$parts[0] -lt 3 -or ([int]$parts[0] -eq 3 -and [int]$parts[1] -lt 10)) {
        throw "Python 3.10 or newer is required. Found Python $version."
    }
    $pythonw = Join-Path (Split-Path -Parent $pythonExe) 'pythonw.exe'
    if (-not (Test-Path -LiteralPath $pythonw)) {
        throw "Could not find pythonw.exe beside $pythonExe. Reinstall Python with the standard Windows installer."
    }

    foreach ($file in @('task_bubble.pyw', 'task_bubble.ico', 'task_bubble_icon.png', 'close.wav')) {
        $sourceFile = Join-Path $sourceRoot $file
        if (-not (Test-Path -LiteralPath $sourceFile)) {
            throw "Required app file is missing: $file"
        }
        Copy-Item -LiteralPath $sourceFile -Destination (Join-Path $installRoot $file) -Force
    }
    $launchTarget = $pythonw
    $launchArgs = '"' + (Join-Path $installRoot 'task_bubble.pyw') + '"'
    $iconLocation = Join-Path $installRoot 'task_bubble.ico'
}

New-Item -ItemType Directory -Path $startupFolder -Force | Out-Null
$shell = New-Object -ComObject WScript.Shell
foreach ($linkPath in @($desktopLink, $startupLink)) {
    $shortcut = $shell.CreateShortcut($linkPath)
    $shortcut.TargetPath = $launchTarget
    $shortcut.Arguments = $launchArgs
    $shortcut.WorkingDirectory = $installRoot
    $shortcut.IconLocation = $iconLocation
    $shortcut.Description = 'Floating task list, sorted by due date and priority'
    $shortcut.Save()
}

Write-Host "Task Bubble is installed at $installRoot"
Write-Host 'A desktop shortcut and a sign-in startup shortcut were added.'
Write-Host 'Your task data remains in %LOCALAPPDATA%\TaskBubble.'
