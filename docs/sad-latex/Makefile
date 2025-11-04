# Makefile para compilar el documento SAD
# Observatorio de Demanda Laboral - Pontificia Universidad Javeriana

# Archivo principal (sin extensión .tex)
MAIN = main

# Compilador LaTeX
LATEX = pdflatex
BIBTEX = biber

# Opciones del compilador
LATEX_OPTS = -interaction=nonstopmode -halt-on-error

# Visor de PDF
PDF_VIEWER = evince  # Cambiar según tu sistema (okular, xdg-open, open en macOS)

# ============================================================================
# Reglas principales
# ============================================================================

# Regla por defecto: compilar el documento completo
all: $(MAIN).pdf

# Compilar el documento PDF
$(MAIN).pdf: $(MAIN).tex sections/*.tex portada.tex bibliografia.bib
	@echo "==> Compilando documento (primera pasada)..."
	$(LATEX) $(LATEX_OPTS) $(MAIN).tex
	@echo ""
	@echo "==> Generando bibliografía..."
	$(BIBTEX) $(MAIN)
	@echo ""
	@echo "==> Compilando documento (segunda pasada)..."
	$(LATEX) $(LATEX_OPTS) $(MAIN).tex
	@echo ""
	@echo "==> Compilando documento (tercera pasada)..."
	$(LATEX) $(LATEX_OPTS) $(MAIN).tex
	@echo ""
	@echo "✓ Compilación completada: $(MAIN).pdf"

# Compilación rápida (sin bibliografía)
fast: $(MAIN).tex
	@echo "==> Compilación rápida (sin bibliografía)..."
	$(LATEX) $(LATEX_OPTS) $(MAIN).tex
	@echo "✓ Compilación rápida completada"

# Limpiar archivos auxiliares
clean:
	@echo "==> Limpiando archivos auxiliares..."
	rm -f *.aux *.log *.out *.toc *.bbl *.blg *.bcf *.run.xml *.fls *.fdb_latexmk
	rm -f sections/*.aux
	@echo "✓ Archivos auxiliares eliminados"

# Limpiar todo (incluyendo el PDF)
cleanall: clean
	@echo "==> Eliminando PDF generado..."
	rm -f $(MAIN).pdf
	@echo "✓ Limpieza completa"

# Compilar y abrir el PDF
view: all
	@echo "==> Abriendo PDF..."
	$(PDF_VIEWER) $(MAIN).pdf &

# Compilar continuamente (watch mode)
watch:
	@echo "==> Modo watch activado (Ctrl+C para salir)..."
	@while true; do \
		make --no-print-directory fast; \
		inotifywait -qre close_write .; \
	done

# Verificar instalación de dependencias
check:
	@echo "==> Verificando instalación de LaTeX..."
	@which $(LATEX) > /dev/null && echo "✓ pdflatex instalado" || echo "✗ pdflatex NO instalado"
	@which $(BIBTEX) > /dev/null && echo "✓ biber instalado" || echo "✗ biber NO instalado"
	@echo ""
	@echo "==> Verificando paquetes LaTeX requeridos..."
	@kpsewhich babel.sty > /dev/null && echo "✓ babel" || echo "✗ babel NO instalado"
	@kpsewhich biblatex.sty > /dev/null && echo "✓ biblatex" || echo "✗ biblatex NO instalado"
	@kpsewhich tikz.sty > /dev/null && echo "✓ tikz" || echo "✗ tikz NO instalado"
	@kpsewhich fancyhdr.sty > /dev/null && echo "✓ fancyhdr" || echo "✗ fancyhdr NO instalado"
	@kpsewhich geometry.sty > /dev/null && echo "✓ geometry" || echo "✗ geometry NO instalado"

# Mostrar ayuda
help:
	@echo "Makefile para documento SAD - Observatorio de Demanda Laboral"
	@echo ""
	@echo "Uso: make [target]"
	@echo ""
	@echo "Targets disponibles:"
	@echo "  all        - Compilar el documento completo (default)"
	@echo "  fast       - Compilación rápida sin bibliografía"
	@echo "  clean      - Limpiar archivos auxiliares"
	@echo "  cleanall   - Limpiar todo (incluyendo PDF)"
	@echo "  view       - Compilar y abrir el PDF"
	@echo "  watch      - Compilar automáticamente al detectar cambios"
	@echo "  check      - Verificar instalación de dependencias"
	@echo "  help       - Mostrar esta ayuda"
	@echo ""
	@echo "Ejemplos:"
	@echo "  make           # Compilar documento completo"
	@echo "  make clean     # Limpiar archivos auxiliares"
	@echo "  make view      # Compilar y ver el PDF"

# Declarar targets que no son archivos
.PHONY: all fast clean cleanall view watch check help
