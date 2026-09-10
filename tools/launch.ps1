# Windows launcher: resolve Python without machine-specific paths in the repo.
param([switch]$CheckOnly)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$savedPath = Join-Path $projectRoot 'local\python-path.txt'
$candidates = [System.Collections.Generic.List[string]]::new()
if (Test-Path -LiteralPath $savedPath) {
    $candidates.Add((Get-Content -LiteralPath $savedPath -Raw).Trim())
}
$candidates.Add((Join-Path $projectRoot '.venv\Scripts\python.exe'))
if ($env:CONDA_PREFIX) { $candidates.Add((Join-Path $env:CONDA_PREFIX 'python.exe')) }
foreach ($name in @('python.exe', 'python3.exe')) {
    $command = Get-Command $name -ErrorAction SilentlyContinue
    if ($command -and $command.Source -notlike '*\WindowsApps\*') { $candidates.Add($command.Source) }
}
$launcher = Get-Command py.exe -ErrorAction SilentlyContinue
if ($launcher) {
    $found = & $launcher.Source -3 -c 'import sys; print(sys.executable)' 2>$null
    if ($LASTEXITCODE -eq 0 -and $found) { $candidates.Add(($found | Select-Object -Last 1).Trim()) }
}
foreach ($registry in @('HKCU:\Software\Python\PythonCore', 'HKLM:\Software\Python\PythonCore')) {
    if (Test-Path $registry) {
        foreach ($version in Get-ChildItem $registry) {
            $install = Join-Path $version.PSPath 'InstallPath'
            if (Test-Path $install) {
                $base = (Get-Item $install).GetValue('')
                if ($base) { $candidates.Add((Join-Path $base 'python.exe')) }
            }
        }
    }
}
function Test-UsablePython([string]$candidate) {
    if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) { return $false }
    try {
        & $candidate -c 'import sys, tkinter; assert sys.version_info >= (3,10)' 2>$null | Out-Null
        return $LASTEXITCODE -eq 0
    } catch { return $false }
}
$pythonExecutable = $null
foreach ($candidate in $candidates) {
    if (Test-UsablePython $candidate) { $pythonExecutable = $candidate; break }
}
if (-not $pythonExecutable) {
    if ($CheckOnly) { throw 'No usable Python 3.10+ with Tkinter found.' }
    Add-Type -AssemblyName System.Windows.Forms
    $picker = New-Object System.Windows.Forms.OpenFileDialog
    $picker.Title = 'Select installed Python 3.10+ (python.exe, with Tkinter)'
    $picker.Filter = 'Python interpreter (python.exe)|python.exe'
    if ($picker.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) { exit 1 }
    if (-not (Test-UsablePython $picker.FileName)) { throw 'Python must be version 3.10+ with Tkinter installed.' }
    $pythonExecutable = $picker.FileName
}
if ($CheckOnly) { Write-Output $pythonExecutable; exit 0 }
New-Item -ItemType Directory -Force (Split-Path $savedPath -Parent) | Out-Null
Set-Content -LiteralPath $savedPath -Value $pythonExecutable -Encoding UTF8
Set-Location -LiteralPath $projectRoot
& $pythonExecutable (Join-Path $PSScriptRoot 'control_panel.py')
exit $LASTEXITCODE
