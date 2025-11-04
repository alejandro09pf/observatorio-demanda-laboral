# SRS - Especificación de Requerimientos de Software

Este directorio contiene el documento de **Especificación de Requerimientos de Software (SRS)** del proyecto "Observatorio de Demanda Laboral en Tecnología en Latinoamérica".

## Estructura del Proyecto

```
srs-latex/
├── main.tex              # Documento principal LaTeX
├── portada.tex           # Portada del documento
├── bibliografia.bib      # Referencias bibliográficas
├── compile.bat           # Script de compilación para Windows
├── .gitignore           # Archivos ignorados por git
├── README.md            # Este archivo
├── sections/            # Secciones del documento
│   ├── 01-introduccion.tex
│   ├── 02-descripcion-general.tex
│   └── 03-requerimientos-especificos.tex
├── figures/             # Figuras e imágenes
├── diagrams/            # Diagramas del sistema
└── logo-javeriana.png   # Logo de la universidad
```

## Requisitos

Para compilar este documento necesitas:

- **MiKTeX** (o cualquier distribución de LaTeX)
- **Biber** (para bibliografía, incluido en MiKTeX)

### Paquetes LaTeX Requeridos

Los siguientes paquetes serán instalados automáticamente por MiKTeX:

- `inputenc`, `babel` (español)
- `geometry` (márgenes)
- `graphicx` (imágenes)
- `hyperref` (hipervínculos)
- `biblatex` (bibliografía estilo IEEE)
- `tikz` (diagramas)
- `longtable`, `multirow`, `array`, `booktabs` (tablas)
- `listings`, `xcolor` (código fuente)
- `fancyhdr` (encabezados y pies de página)
- `titlesec` (formato de títulos)

## Compilación

### Método 1: Script Automático (Recomendado)

En Windows, simplemente ejecuta:

```cmd
compile.bat
```

Este script:
1. Compila el documento con `pdflatex`
2. Genera la bibliografía con `biber`
3. Recompila dos veces para referencias cruzadas
4. Abre automáticamente el PDF generado

### Método 2: Compilación Manual

```cmd
pdflatex main.tex
biber main
pdflatex main.tex
pdflatex main.tex
```

## Contenido del Documento

El SRS incluye:

1. **Introducción**
   - Propósito del sistema
   - Alcance geográfico y tecnológico
   - Definiciones, acrónimos y abreviaciones
   - Estado actual de implementación

2. **Descripción General**
   - Perspectiva del producto
   - Funciones principales
   - Características de usuarios
   - Restricciones de software y hardware
   - Supuestos y dependencias

3. **Requerimientos Específicos**
   - Requerimientos funcionales (RF-01 a RF-06)
   - Requerimientos de mapeo ESCO (RF-04.1 a RF-04.5)
   - Requerimientos de desempeño (RD-01 a RD-06)
   - Restricciones de diseño
   - Atributos no funcionales

## Información del Proyecto

- **Título:** Observatorio de Demanda Laboral en Tecnología en Latinoamérica
- **Código:** CIS2025CP08
- **Autores:**
  - Nicolás Francisco Camacho Alarcón
  - Alejandro Pinzón Fajardo
- **Director:** Ing. Luis Gabriel Moreno Sandoval
- **Versión:** 2.1 - Fase 0 Implementada
- **Fecha:** Noviembre 2025

## Datos Técnicos del Sistema

- **Taxonomía de skills:** 14,174 totales (ESCO: 13,939 + O*NET: 152 + Manual: 83)
- **Alcance geográfico:** Colombia, México, Argentina
- **Portales de empleo:** 11 fuentes
- **Stack tecnológico:** Python 3.10+, Scrapy, spaCy, PostgreSQL, FAISS, E5 embeddings (768D)
- **Jobs scraped:** 23,352 (99.5% usables)
- **Performance FAISS:** 30,147 queries/segundo

## Notas

- El archivo PDF generado (`main.pdf`) NO se incluye en el repositorio git (.gitignore)
- Los archivos auxiliares de LaTeX (.aux, .log, .toc, etc.) tampoco se versionan
- Asegúrate de tener MiKTeX actualizado para evitar problemas de paquetes faltantes

## Soporte

Para problemas de compilación, verifica:

1. Que MiKTeX esté en el PATH del sistema
2. Que todos los paquetes estén actualizados
3. Que no haya errores de sintaxis en los archivos .tex

Si encuentras errores, revisa el archivo `main.log` para más detalles.
