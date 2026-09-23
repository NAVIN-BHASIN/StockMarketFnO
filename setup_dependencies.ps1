# setup_dependencies.ps1
# Run this script to install missing dependencies for the StockMarketFnO application.

Write-Host "Checking for virtual environment..." -ForegroundColor Cyan
if (Test-Path ".\venv") {
    Write-Host "Activating virtual environment and installing pdfplumber..." -ForegroundColor Yellow
    .\venv\Scripts\python.exe -m pip install pdfplumber
} else {
    Write-Host "No venv found. Installing globally..." -ForegroundColor Yellow
    python -m pip install pdfplumber
}

if ($LASTEXITCODE -eq 0) {
    Write-Host "Installation successful!" -ForegroundColor Green
} else {
    Write-Host "Installation failed. Please try running 'pip install pdfplumber' manually in your terminal." -ForegroundColor Red
}

Write-Host "Press any key to exit..."
$x = $host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
