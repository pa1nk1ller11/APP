$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python launcher 'py' was not found. Install Python 3.10+ from python.org and enable 'Add Python to PATH'."
}

if (-not (Test-Path ".venv")) {
    py -3 -m venv .venv
}

. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller

python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --onefile `
    --name "WindTunnelControl" `
    wind_tunnel_control_app.py

Write-Host ""
Write-Host "Built one-file Windows app: dist\WindTunnelControl.exe"
Write-Host "This is the file to download/copy to the wind tunnel computer."

$InnoSetup = Get-Command iscc -ErrorAction SilentlyContinue
if ($InnoSetup) {
    iscc installer\WindTunnelControl.iss
    Write-Host "Optional installer also built: dist\installers\WindTunnelControlSetup.exe"
} else {
    Write-Host "Inno Setup was not found. That is okay; the one-file app is ready."
}
