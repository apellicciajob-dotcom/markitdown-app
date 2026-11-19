<#
.SYNOPSIS
  Crea l'eseguibile standalone (PyInstaller --noconsole) di MarkItDown App.
.PARAMETER OneFile
  Produce un singolo .exe invece di una cartella (la cartella e' piu' veloce
  all'avvio ed e' il formato usato da build_msix.ps1).
.PARAMETER Python
  Interprete da usare (default: venv %USERPROFILE%\venvs\markitdown).
#>
param(
    [switch]$OneFile,
    [string]$Python = "$env:USERPROFILE\venvs\markitdown\Scripts\python.exe"
)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path $Python)) { throw "Python non trovato: $Python" }

# 1) Icona e asset (solo se mancanti)
& $Python make_assets.py
if ($LASTEXITCODE -ne 0) { throw "make_assets.py fallito" }

# 2) PyInstaller
$mode = if ($OneFile) { "--onefile" } else { "--onedir" }
$args = @(
    "-m", "PyInstaller", "--noconfirm", "--clean", "--noconsole", $mode,
    "--name", "MarkItDownApp",
    "--icon", "assets\icon.ico",
    "--add-data", "assets;assets",
    "--collect-all", "markitdown",
    "--collect-all", "magika",
    "--collect-all", "customtkinter",
    "--collect-all", "tkinterdnd2",
    "--collect-all", "pdfminer",
    "--collect-all", "mammoth",
    "--collect-all", "pptx",
    "--collect-all", "openpyxl",
    "--collect-submodules", "markitdown",
    "--collect-data", "onnxruntime",
    "--hidden-import", "smoke_test",
    "--hidden-import", "markdownify",
    "--hidden-import", "bs4",
    "--hidden-import", "pandas",
    "--hidden-import", "xlrd",
    "--hidden-import", "ebooklib",
    "--copy-metadata", "markitdown",
    "--copy-metadata", "magika",
    "--copy-metadata", "pdfminer.six",
    "--copy-metadata", "python-pptx",
    "--copy-metadata", "openpyxl",
    "app.py"
)
& $Python @args
if ($LASTEXITCODE -ne 0) { throw "PyInstaller fallito" }

if ($OneFile) { Write-Host "`nOK -> dist\MarkItDownApp.exe" }
else          { Write-Host "`nOK -> dist\MarkItDownApp\MarkItDownApp.exe" }
