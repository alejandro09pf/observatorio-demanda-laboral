@echo off
REM Script de compilación para SRS - Especificación de Requerimientos de Software
REM Observatorio de Demanda Laboral en Tecnología en Latinoamérica
REM
REM Uso: compile.bat

echo ============================================================
echo Compilando SRS - Especificacion de Requerimientos de Software
echo ============================================================
echo.

REM Primera compilación
echo [1/4] Primera compilacion con pdflatex...
pdflatex -interaction=nonstopmode main.tex
if errorlevel 1 (
    echo ERROR: Primera compilacion fallo
    pause
    exit /b 1
)

REM Generar bibliografía con biber
echo.
echo [2/4] Generando bibliografia con biber...
biber main
if errorlevel 1 (
    echo ADVERTENCIA: biber fallo, continuando...
)

REM Segunda compilación
echo.
echo [3/4] Segunda compilacion con pdflatex...
pdflatex -interaction=nonstopmode main.tex
if errorlevel 1 (
    echo ERROR: Segunda compilacion fallo
    pause
    exit /b 1
)

REM Tercera compilación para referencias cruzadas
echo.
echo [4/4] Tercera compilacion con pdflatex...
pdflatex -interaction=nonstopmode main.tex
if errorlevel 1 (
    echo ERROR: Tercera compilacion fallo
    pause
    exit /b 1
)

echo.
echo ============================================================
echo Compilacion exitosa!
echo PDF generado: main.pdf
echo ============================================================
echo.

REM Abrir el PDF si existe
if exist main.pdf (
    echo Abriendo PDF...
    start main.pdf
)

pause
