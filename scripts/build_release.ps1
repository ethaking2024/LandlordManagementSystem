<#
.SYNOPSIS
    Builds the LMS desktop application release (PyInstaller onedir) on Windows.
.DESCRIPTION
    Runs quality gates (unit tests, Ruff, Mypy), generates the app icon if
    missing, executes the PyInstaller spec, and prepares the output folder with
    the environment template the user needs to configure.
.EXAMPLE
    .\scripts\build_release.ps1
    .\scripts\build_release.ps1 -SkipTests -SkipChecks
#>
param(
    [switch]$SkipTests,
    [switch]$SkipChecks,
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "[build] LMS release 1.0.0"

# 1. Ensure build tooling is available.
& $Python -m pip install --quiet "pyinstaller>=6.8.0" "psycopg[binary]"
if ($LASTEXITCODE -ne 0) { throw "Failed to install build tooling (PyInstaller / psycopg[binary])." }

# 2. Ensure the application icon exists.
& $Python scripts/create_icon.py
if ($LASTEXITCODE -ne 0) { throw "Failed to generate the application icon." }

# 3. Quality gates (optional but recommended).
if (-not $SkipTests) {
    Write-Host "[build] Running unit tests..."
    & $Python -m pytest tests/unit -q
    if ($LASTEXITCODE -ne 0) { throw "Unit tests failed." }
}
if (-not $SkipChecks) {
    Write-Host "[build] Running Ruff..."
    & $Python -m ruff check .
    if ($LASTEXITCODE -ne 0) { throw "Ruff checks failed." }

    Write-Host "[build] Running Mypy..."
    & $Python -m mypy app/
    if ($LASTEXITCODE -ne 0) { throw "Mypy checks failed." }
}

# 4. PyInstaller build.
Write-Host "[build] Running PyInstaller..."
Remove-Item -Recurse -Force "packaging/dist", "packaging/build" -ErrorAction SilentlyContinue
& $Python -m PyInstaller --noconfirm --clean `
    --distpath "packaging/dist" --workpath "packaging/build" "packaging/LMS.spec"
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed." }

# 5. Prepare the distribution folder with the environment template.
$dist = Join-Path $root "packaging/dist/LMS"
Copy-Item -Force ".env.example" (Join-Path $dist ".env.example")

# 6. Optional: validate the packaged executable.
$exe = Join-Path $dist "LMS.exe"
if (Test-Path $exe) {
    Write-Host "[build] Validating packaged executable..."
    $report = Join-Path $root "packaging/dist/self-check.json"
    $proc = Start-Process -FilePath $exe -ArgumentList "--self-check", "--report", $report -Wait -PassThru
    Write-Host "[build] Self-check exit code: $($proc.ExitCode) (report: $report)"
    if ($proc.ExitCode -ne 0) {
        Write-Warning "Packaged self-check failed (exit $($proc.ExitCode)). The build is complete, but check the report - the executable may need a configured .env next to it to pass."
    }
}

Write-Host "[build] Build complete: $exe"
Write-Host "[build] Copy the entire 'dist/LMS' folder to distribute the application."
