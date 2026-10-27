$ErrorActionPreference = 'Stop'
$careerProject = Join-Path $PSScriptRoot 'AI-Resume-Analyzer'
$careerPython = Join-Path $careerProject 'venv\Scripts\python.exe'
Push-Location (Join-Path $careerProject 'App')
try {
    & $careerPython -m streamlit run App.py --server.address 127.0.0.1 --server.port 8501
} finally {
    Pop-Location
}
