# Script PowerShell para compilar el documento SPMP
# Navegar al directorio del documento
Set-Location "C:\Users\PcMaster\Documents\GitHub\observatorio-demanda-laboral\docs\spmp-latex"

Write-Host "============================================================"
Write-Host "Compilando SPMP - Plan de Gestion del Proyecto de Software"
Write-Host "============================================================"
Write-Host ""

# Primera compilación
Write-Host "[1/4] Primera compilacion con pdflatex..."
& "C:\Users\PcMaster\AppData\Local\Programs\MiKTeX\miktex\bin\x64\pdflatex.exe" -interaction=nonstopmode main.tex
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Primera compilacion fallo"
    exit 1
}

# Generar bibliografía con biber
Write-Host ""
Write-Host "[2/4] Generando bibliografia con biber..."
& "C:\Users\PcMaster\AppData\Local\Programs\MiKTeX\miktex\bin\x64\biber.exe" main
if ($LASTEXITCODE -ne 0) {
    Write-Host "ADVERTENCIA: biber fallo, continuando..."
}

# Segunda compilación
Write-Host ""
Write-Host "[3/4] Segunda compilacion con pdflatex..."
& "C:\Users\PcMaster\AppData\Local\Programs\MiKTeX\miktex\bin\x64\pdflatex.exe" -interaction=nonstopmode main.tex
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Segunda compilacion fallo"
    exit 1
}

# Tercera compilación para referencias cruzadas
Write-Host ""
Write-Host "[4/4] Tercera compilacion con pdflatex..."
& "C:\Users\PcMaster\AppData\Local\Programs\MiKTeX\miktex\bin\x64\pdflatex.exe" -interaction=nonstopmode main.tex
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Tercera compilacion fallo"
    exit 1
}

Write-Host ""
Write-Host "============================================================"
Write-Host "Compilacion exitosa!"
Write-Host "PDF generado: main.pdf"
Write-Host "============================================================"
Write-Host ""

# Abrir el PDF si existe
if (Test-Path "main.pdf") {
    Write-Host "Abriendo PDF..."
    Start-Process "main.pdf"
}
