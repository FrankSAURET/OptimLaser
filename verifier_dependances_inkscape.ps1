$ErrorActionPreference = 'Stop'

$pythonCandidates = @(
    'C:\Program Files\Inkscape\bin\python.exe',
    "$env:LOCALAPPDATA\Programs\Inkscape\bin\python.exe"
)

$pythonExe = $pythonCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $pythonExe) {
    Write-Host 'ERREUR: Python Inkscape introuvable.' -ForegroundColor Red
    Write-Host 'Installez/reinstallez Inkscape puis relancez ce script.' -ForegroundColor Yellow
    exit 1
}

Write-Host "Python Inkscape: $pythonExe" -ForegroundColor Cyan
& $pythonExe --version

$code = @'
import importlib.util
import sys

checks = {
    'inkex': 'required',
    'lxml': 'required',
    'tkinter': 'optional_gui',
    'json': 'stdlib',
    'gettext': 'stdlib',
}

missing_required = []
missing_optional = []

for module, kind in checks.items():
    ok = importlib.util.find_spec(module) is not None
    print(f"{module}: {'OK' if ok else 'MISSING'}")
    if not ok and kind == 'required':
        missing_required.append(module)
    if not ok and kind == 'optional_gui':
        missing_optional.append(module)

if missing_required:
    print('RESULT: FAIL required=' + ','.join(missing_required))
    sys.exit(2)

if missing_optional:
    print('RESULT: WARN optional=' + ','.join(missing_optional))
    print('OptimLaser continuera sans interface graphique (mode fallback).')
    sys.exit(0)

print('RESULT: OK all dependencies available')
'@

$tempPy = Join-Path $env:TEMP 'optimlaser_dependency_check.py'
Set-Content -Path $tempPy -Value $code -Encoding UTF8

& $pythonExe $tempPy
$exitCode = $LASTEXITCODE

Remove-Item -Path $tempPy -Force -ErrorAction SilentlyContinue
exit $exitCode
