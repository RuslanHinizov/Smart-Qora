# Download the model weights that are kept out of git (see .gitignore).
# Set $env:SMART_QORA_MODELS_URL to the base URL of a release that hosts the files,
# e.g. https://github.com/<owner>/<repo>/releases/download/models-v1
$ErrorActionPreference = "Stop"

$BaseUrl = $env:SMART_QORA_MODELS_URL
$Dest = Join-Path (Split-Path -Parent $PSScriptRoot) "models"
$Files = @("best.pt", "mobileclip2_b.ts")

if ([string]::IsNullOrWhiteSpace($BaseUrl)) {
    Write-Error "Set `$env:SMART_QORA_MODELS_URL to where the weights are hosted, then re-run.`n  `$env:SMART_QORA_MODELS_URL = 'https://github.com/<owner>/<repo>/releases/download/models-v1'"
}

New-Item -ItemType Directory -Force -Path $Dest | Out-Null
foreach ($f in $Files) {
    $target = Join-Path $Dest $f
    if (Test-Path $target) { Write-Host "OK  $f already present"; continue }
    Write-Host "DL  $f"
    Invoke-WebRequest -Uri "$BaseUrl/$f" -OutFile $target
    try {
        Invoke-WebRequest -Uri "$BaseUrl/$f.sha256" -OutFile "$target.sha256"
        $expected = (Get-Content "$target.sha256").Split(" ")[0]
        $actual = (Get-FileHash $target -Algorithm SHA256).Hash.ToLower()
        if ($expected -ne $actual) { Write-Error "checksum mismatch for $f" }
        Write-Host "    checksum ok"
    } catch { }
}
Write-Host "Models ready in $Dest"
