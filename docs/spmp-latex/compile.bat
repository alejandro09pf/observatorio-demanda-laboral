@echo off
REM Script de compilacion automatica para el SPMP LaTeX
REM Ejecuta el proceso completo: pdflatex -> biber -> pdflatex -> pdflatex

echo ====================================
echo Compilacion de SPMP LaTeX
echo ====================================
echo.

set MIKTEX_PATH=C:\Users\PcMaster\AppData\Local\Programs\MiKTeX\miktex\bin\x64
set PDFLATEX=%MIKTEX_PATH%\pdflatex.exe
set BIBER=%MIKTEX_PATH%\biber.exe

echo [1/5] Primera compilacion con pdflatex...
"%PDFLATEX%" -interaction=nonstopmode main.tex
if not exist main.pdf (
    echo ERROR CRITICO: No se pudo generar el PDF
    echo Mostrando ultimas 50 lineas del log:
    powershell -Command "Get-Content main.log -Tail 50"
    pause
    exit /b 1
)

echo.
echo [2/5] Procesando bibliografia con biber...
"%BIBER%" main 2>&1

echo.
echo [3/5] Segunda compilacion con pdflatex...
"%PDFLATEX%" -interaction=nonstopmode main.tex > nul

echo.
echo [4/5] Tercera compilacion con pdflatex (referencias cruzadas)...
"%PDFLATEX%" -interaction=nonstopmode main.tex > nul

echo.
echo [5/5] Limpiando archivos temporales...
del /Q *.aux *.log *.out *.toc *.bcf *.blg *.run.xml *.bbl 2>nul

echo.
echo ====================================
echo Compilacion completada exitosamente!
echo PDF generado: main.pdf
for %%A in (main.pdf) do echo Tamanio: %%~zA bytes
echo ====================================
echo.
