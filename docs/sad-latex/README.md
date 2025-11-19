# Documento SAD en LaTeX

Este directorio contiene el **Software Architecture Document (SAD)** del proyecto "Observatorio de Demanda Laboral en América Latina" en formato LaTeX.

## Estructura del Proyecto

```
sad-latex/
├── main.tex                    # Documento principal
├── portada.tex                 # Portada del documento
├── bibliografia.bib            # Referencias bibliográficas
├── sections/                   # Secciones del documento
│   ├── 01-objetivo.tex
│   ├── 02-atributos-calidad.tex
│   ├── 03-arquitectura.tex
│   ├── 04-riesgos.tex
│   └── 05-restricciones.tex
└── README.md                   # Este archivo
```

## Requisitos

Para compilar el documento necesitas tener instalado:

- **LaTeX Distribution**:
  - Windows: [MiKTeX](https://miktex.org/) o [TeX Live](https://www.tug.org/texlive/)
  - macOS: [MacTeX](https://www.tug.org/mactex/)
  - Linux: `sudo apt-get install texlive-full` (Debian/Ubuntu)

- **Paquetes LaTeX requeridos**:
  - babel (español)
  - biblatex (bibliografía)
  - tikz (diagramas)
  - fancyhdr (encabezados)
  - geometry (márgenes)
  - hyperref (enlaces)
  - listings (código)
  - booktabs (tablas)
  - float (posicionamiento de figuras)

## Compilación

### Opción 1: Línea de comandos (recomendado)

```bash
# Navegar al directorio del documento
cd docs/sad-latex

# Compilar con pdflatex (primera pasada)
pdflatex main.tex

# Generar bibliografía con biber
biber main

# Compilar dos veces más para resolver referencias cruzadas
pdflatex main.tex
pdflatex main.tex
```

### Opción 2: Editor LaTeX

Si usas un editor como **TeXstudio**, **Overleaf**, o **TeXmaker**:

1. Abre `main.tex` en tu editor
2. Configura el compilador a **pdfLaTeX**
3. Configura la bibliografía a **Biber** (no BibTeX)
4. Presiona "Build & View" o F5

### Opción 3: Makefile (Linux/macOS)

```bash
make          # Compilar el documento
make clean    # Limpiar archivos auxiliares
make view     # Compilar y abrir el PDF
```

## Archivo de Salida

El documento compilado se generará como:
```
main.pdf
```

## Notas Importantes

### Logo de la Universidad

El documento hace referencia a un logo de la universidad:
```latex
\includegraphics[width=0.4\textwidth]{../latex/figures/logo-javeriana.png}
```

**Asegúrate de que exista el archivo:**
```
docs/latex/figures/logo-javeriana.png
```

Si no tienes el logo, puedes:
1. Comentar la línea del logo en `portada.tex`
2. Agregar el logo PNG en la ruta especificada

### Fechas y Versiones

Actualiza las siguientes variables en `main.tex` según sea necesario:

```latex
\newcommand{\mes}{Enero}              % Mes actual
\newcommand{\anio}{2025}              % Año actual
\newcommand{\versionDocumento}{1.0}   % Versión del documento
```

### Tabla de Control de Cambios

Actualiza la tabla de control de cambios en la sección inicial del documento con las fechas reales de modificación.

## Solución de Problemas

### Error: "Package babel Warning: No hyphenation patterns"

**Solución**: Instala el paquete de idioma español:
```bash
# MiKTeX
mpm --install=babel-spanish

# TeX Live
tlmgr install babel-spanish
```

### Error: "File `tikz.sty' not found"

**Solución**: Instala el paquete TikZ/PGF:
```bash
# MiKTeX (automático al compilar)

# TeX Live
tlmgr install pgf
```

### Error: "Biber not found"

**Solución**: Asegúrate de que biber esté instalado:
```bash
# Verificar instalación
biber --version

# Instalar si es necesario (TeX Live)
tlmgr install biber
```

### Advertencias de "Overfull \hbox"

Esto es normal y generalmente no afecta la salida final. Si quieres eliminarlas:
- Ajusta el tamaño de figuras/tablas
- Usa `\linebreak` o `\newline` en textos largos
- Reduce el tamaño de fuente en tablas con `\small`

## Personalización

### Modificar Márgenes

Edita en `main.tex`:
```latex
\usepackage[letterpaper,top=2.5cm,bottom=2.5cm,left=2.5cm,right=2.5cm]{geometry}
```

### Cambiar Interlineado

Edita en `main.tex`:
```latex
\onehalfspacing    % Actual: 1.5 líneas
% \doublespacing   % Alternativa: doble espacio
% \singlespacing   % Alternativa: espacio simple
```

### Agregar Nuevas Secciones

1. Crea un archivo en `sections/` (ej. `06-conclusiones.tex`)
2. Agrega `\input{sections/06-conclusiones}` en `main.tex`

## Contacto

**Autores:**
- Nicolás Francisco Camacho Alarcón
- Alejandro Pinzón Fajardo

**Director:**
- Ing. Luis Gabriel Moreno Sandoval

**Código del Proyecto:** CIS2025CP08

**Institución:**
Pontificia Universidad Javeriana
Facultad de Ingeniería - Carrera de Ingeniería de Sistemas
Bogotá D.C., Colombia

---

**Versión del README:** 1.0
**Última actualización:** Noviembre 2025
