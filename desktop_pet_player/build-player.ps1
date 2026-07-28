param(
    [switch]$VisualTest,
    [switch]$SelfTest
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$compiler = 'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe'
$outputDirectory = Join-Path $root 'dist'
$outputName = -join @([char]0x684C, [char]0x5BA0, [char]0x64AD, [char]0x653E, [char]0x5668)
$outputFile = if ($SelfTest) {
    Join-Path $outputDirectory 'DesktopPetPlayerSelfTest.exe'
} elseif ($VisualTest) {
    Join-Path $outputDirectory 'DesktopPetPlayerVisualTest.exe'
} else {
    Join-Path $outputDirectory ($outputName + '.exe')
}
$sourceFile = Join-Path $root 'player\Program.cs'
$iconFile = Join-Path $root 'assets\app.ico'

if (-not (Test-Path -LiteralPath $compiler)) {
    throw 'Windows C# compiler was not found.'
}

New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null

$arguments = @(
    '/nologo'
    $(if ($SelfTest) { '/target:exe' } else { '/target:winexe' })
    '/optimize+'
    '/platform:anycpu'
    '/codepage:65001'
    ('/out:' + $outputFile)
    ('/win32icon:' + $iconFile)
    ('/reference:C:\Windows\Microsoft.NET\Framework64\v4.0.30319\System.Drawing.dll')
    ('/reference:C:\Windows\Microsoft.NET\Framework64\v4.0.30319\System.Windows.Forms.dll')
    ('/reference:C:\Windows\Microsoft.NET\Framework64\v4.0.30319\System.IO.Compression.dll')
    ('/reference:C:\Windows\Microsoft.NET\Framework64\v4.0.30319\System.Runtime.Serialization.dll')
    $sourceFile
)

if ($VisualTest) {
    $arguments += '/define:VISUAL_TEST'
}

if ($SelfTest) {
    $arguments += '/define:SELF_TEST'
}

& $compiler @arguments
if ($LASTEXITCODE -ne 0) {
    throw "Compilation failed with exit code $LASTEXITCODE"
}

Write-Host "Built: $outputFile"
