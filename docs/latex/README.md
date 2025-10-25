# Tesis en LaTeX - Observatorio de Demanda Laboral

Estructura del documento LaTeX para la tesis de grado de la Pontificia Universidad Javeriana.

## Estructura de Archivos

```
latex/
├── main.tex                    # Documento principal
├── bibliografia.bib            # Referencias bibliográficas
├── README.md                   # Este archivo
├── front/                      # Páginas preliminares
│   ├── portada.tex
│   ├── portada-interna.tex
│   ├── autoridades.tex
│   ├── articulo23.tex
│   ├── gratitude.tex
│   └── abstract.tex
├── chapters/                   # Capítulos principales
│   ├── 01-introduccion.tex
│   ├── 02-descripcion-general.tex
│   ├── 03-contexto.tex
│   ├── 04-analisis-problema.tex
│   ├── 05-diseno-solucion.tex
│   ├── 06-desarrollo.tex
│   ├── 07-resultados.tex
│   └── 08-conclusiones.tex
├── figures/                    # Figuras e imágenes
└── tables/                     # Tablas complejas
```

## Requisitos

### Opción 1: Overleaf (Recomendado)
1. Crear cuenta en [Overleaf](https://www.overleaf.com)
2. New Project → Upload Project
3. Subir todos los archivos de la carpeta `latex/`
4. Compilar (Ctrl+S o botón Recompile)

### Opción 2: Instalación Local

#### Windows:
```bash
# Instalar MiKTeX
winget install MiKTeX.MiKTeX

# O descargar de: https://miktex.org/download
```

#### Mac:
```bash
brew install --cask mactex
```

#### Linux (Ubuntu/Debian):
```bash
sudo apt-get update
sudo apt-get install texlive-full
```

## Compilación

### Desde Overleaf:
- Click en "Recompile" o presiona Ctrl+S
- Descargar PDF desde el botón "Download PDF"

### Desde línea de comandos:
```bash
cd docs/latex

# Compilación completa (con bibliografía)
pdflatex main.tex
biber main
pdflatex main.tex
pdflatex main.tex
```

### Usando latexmk (recomendado):
```bash
latexmk -pdf -pvc main.tex
```

## Personalización

### Información del proyecto:
Edita las siguientes líneas en `main.tex` (líneas 47-57):
```latex
\newcommand{\proyectoTitulo}{Observatorio de demanda laboral en América Latina}
\newcommand{\proyectoCodigo}{<CODE>}
\newcommand{\autorUno}{Nicolas Francisco Camacho Alarcón}
\newcommand{\autorDos}{Alejandro Pinzón Fajardo}
\newcommand{\director}{Ing. Luis Gabriel Moreno Sandoval}
\newcommand{\juradoUno}{Ing. <Name of the jury>}
\newcommand{\juradoDos}{Ing. <Name of the jury>}
\newcommand{\anio}{2025}
\newcommand{\mes}{<Month>}
```

### Agregar figuras:
```latex
\begin{figure}[H]
    \centering
    \includegraphics[width=0.8\textwidth]{figures/mi-imagen.png}
    \caption{Descripción de la imagen}
    \label{fig:mi-etiqueta}
\end{figure}
```

### Agregar código:
```latex
\begin{lstlisting}[language=Python, caption=Mi código]
def hello_world():
    print("Hello, World!")
\end{lstlisting}
```

### Referencias cruzadas:
```latex
Como se muestra en la Figura \ref{fig:mi-etiqueta}...
Según el Capítulo \ref{chap:introduccion}...
```

## Bibliografía

Las referencias están en `bibliografia.bib` en formato BibTeX.

### Agregar nueva referencia:
```bibtex
@article{autor2025,
    author = {Apellido, Nombre},
    title = {Título del artículo},
    journal = {Nombre de la revista},
    year = {2025},
    volume = {10},
    pages = {1--20}
}
```

### Citar en el texto:
```latex
\cite{autor2025}                    % (Autor, 2025)
\textcite{autor2025}                % Autor (2025)
\parencite{autor2025}               % (Autor, 2025)
\cite{autor1,autor2,autor3}         % Múltiples citas
```

## Capítulos Completados

- ✅ **Introducción** - Completamente transcrito del PDF
- ✅ **Descripción General** - Completamente transcrito del PDF
- ✅ **Contexto del Proyecto** - Completamente transcrito del PDF
- ⏳ **Análisis del Problema** - Plantilla básica
- ⏳ **Diseño de la Solución** - Plantilla básica
- ⏳ **Desarrollo** - Plantilla básica
- ⏳ **Resultados** - Plantilla básica
- ⏳ **Conclusiones** - Plantilla básica

## Próximos Pasos

1. **Completar información de autoridades** en `front/autoridades.tex`
2. **Escribir agradecimientos** en `front/gratitude.tex`
3. **Desarrollar capítulos 4-8** con el contenido de tu proyecto
4. **Agregar diagramas** en `figures/`:
   - Arquitectura del sistema
   - Diagrama de flujo de datos
   - Diagramas UML/BPMN
   - Gráficos de resultados
5. **Expandir bibliografía** en `bibliografia.bib`
6. **Revisar formato** y numeración de páginas

## Troubleshooting

### Error: "Package babel: Unknown language"
```bash
# Instalar paquete de idiomas
# En MiKTeX: MiKTeX Console → Packages → Buscar "babel-spanish"
# En TeX Live: Ya incluido por defecto
```

### Error: "File not found: bibliografia.bib"
- Verificar que `bibliografia.bib` está en la misma carpeta que `main.tex`
- Usar rutas relativas correctas

### Error de compilación de bibliografía:
```bash
# Asegurarse de usar biber (no bibtex)
biber main
pdflatex main.tex
```

## Contacto y Soporte

- **Overleaf Documentation**: https://www.overleaf.com/learn
- **LaTeX Stack Exchange**: https://tex.stackexchange.com/
- **Plantilla Javeriana**: Basada en template oficial PUJ

## Notas

- El documento sigue el formato oficial de la Pontificia Universidad Javeriana
- La estructura está basada en el template "Proyecto de Grado 2025-3.pdf"
- Capítulos 1-3 transcritos fielmente del documento original
- Usar interlineado 1.5 (ya configurado)
- Máximo 80 páginas para el cuerpo principal
- Referencias y apéndices no cuentan para el límite de páginas
