@echo off
echo ==========================================
echo Compilando tesis LaTeX...
echo ==========================================
"C:\Program Files\MiKTeX\miktex\bin\x64\pdflatex.exe" -interaction=nonstopmode main.tex
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ==========================================
    echo Primera compilacion exitosa!
    echo Compilando segunda vez para referencias...
    echo ==========================================
    "C:\Program Files\MiKTeX\miktex\bin\x64\pdflatex.exe" -interaction=nonstopmode main.tex
    if %ERRORLEVEL% EQU 0 (
        echo.
        echo ==========================================
        echo Compilacion completa exitosa!
        echo PDF generado: main.pdf
        echo ==========================================
    ) else (
        echo.
        echo ==========================================
        echo ERROR en segunda compilacion
        echo ==========================================
    )
) else (
    echo.
    echo ==========================================
    echo ERROR en primera compilacion
    echo ==========================================
)
