@echo off
REM ============================================================================
REM Script de compilacion para documento SAD
REM Observatorio de Demanda Laboral - Pontificia Universidad Javeriana
REM ============================================================================

setlocal

set MAIN=main
set MIKTEX_PATH=C:\Users\PcMaster\AppData\Local\Programs\MiKTeX\miktex\bin\x64
set LATEX=%MIKTEX_PATH%\pdflatex.exe
set BIBTEX=%MIKTEX_PATH%\biber.exe

echo.
echo ===============================================
echo Compilando Documento SAD
echo ===============================================
echo.

REM Primera pasada
echo [1/4] Compilando documento (primera pasada)...
%LATEX% -interaction=nonstopmode %MAIN%.tex
if %errorlevel% neq 0 (
    echo ERROR: Fallo en la primera compilacion
    pause
    exit /b 1
)

REM Generar bibliografia
echo.
echo [2/4] Generando bibliografia...
%BIBTEX% %MAIN%
if %errorlevel% neq 0 (
    echo ERROR: Fallo al generar bibliografia
    pause
    exit /b 1
)

REM Segunda pasada
echo.
echo [3/4] Compilando documento (segunda pasada)...
%LATEX% -interaction=nonstopmode %MAIN%.tex
if %errorlevel% neq 0 (
    echo ERROR: Fallo en la segunda compilacion
    pause
    exit /b 1
)

REM Tercera pasada
echo.
echo [4/4] Compilando documento (tercera pasada)...
%LATEX% -interaction=nonstopmode %MAIN%.tex
if %errorlevel% neq 0 (
    echo ERROR: Fallo en la tercera compilacion
    pause
    exit /b 1
)

echo.
echo ===============================================
echo Compilacion completada exitosamente!
echo Documento generado: %MAIN%.pdf
echo ===============================================
echo.

REM Abrir el PDF si existe
if exist %MAIN%.pdf (
    echo Abriendo PDF...
    start %MAIN%.pdf
) else (
    echo ADVERTENCIA: No se encontro el archivo PDF generado
)

endlocal
pause
