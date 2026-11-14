param(
  [string]$ModelSource = "BAAI/bge-small-zh-v1.5",
  [string]$TorchIndexUrl = "https://download.pytorch.org/whl/cu128",
  [string]$TorchVersion = "2.12.0",
  [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
$VenvPython = Join-Path $Root ".venv-train\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
  $PythonCommand = Get-Command py -ErrorAction SilentlyContinue
  if ($PythonCommand) {
    & py -3.11 -m venv .venv-train
    if ($LASTEXITCODE -ne 0) { & py -3 -m venv .venv-train }
  } else {
    & python -m venv .venv-train
  }
}

if (-not (Test-Path $VenvPython)) {
  throw "Cannot create .venv-train. Install Python 3.10 or 3.11 and retry."
}

if (-not $SkipInstall) {
  & $VenvPython -m pip install --upgrade pip
  if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed" }
  & $VenvPython -m pip install "torch==$TorchVersion" --index-url $TorchIndexUrl
  if ($LASTEXITCODE -ne 0) { throw "CUDA PyTorch installation failed" }
  & $VenvPython -m pip install -r requirements-win.txt
  if ($LASTEXITCODE -ne 0) { throw "Training dependency installation failed" }
}

& $VenvPython scripts\verify_bundle.py
if ($LASTEXITCODE -ne 0) { throw "Bundle checksum verification failed" }

& $VenvPython -m unittest discover -s tests -p "test_*.py"
if ($LASTEXITCODE -ne 0) { throw "Bundle smoke tests failed" }

& $VenvPython scripts\validate_data.py --output outputs\data_validation.json
if ($LASTEXITCODE -ne 0) { throw "Data validation failed" }

New-Item -ItemType Directory -Force -Path outputs | Out-Null
& $VenvPython -m pip freeze | Out-File -Encoding utf8 outputs\requirements-resolved.txt

& $VenvPython scripts\run_experiments.py --config config\train_config.json --model-source $ModelSource --output-dir outputs
if ($LASTEXITCODE -ne 0) { throw "Training failed" }

& $VenvPython scripts\aggregate_results.py --output-dir outputs
if ($LASTEXITCODE -ne 0) { throw "Result aggregation failed" }

Write-Host "Completed. Open outputs\summary.md"
