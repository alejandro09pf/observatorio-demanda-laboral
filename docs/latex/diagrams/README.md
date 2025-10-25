# Diagramas del Observatorio de Demanda Laboral

Este directorio contiene los diagramas profesionales para la tesis.

## Archivos Disponibles

### 1. TikZ (Integración directa en LaTeX) ✅ RECOMENDADO

#### `pipeline-architecture.tex`
- **Uso**: Diagrama completo del pipeline de 8 etapas
- **Estado**: ✅ Funcionando e integrado en el Capítulo 5
- **Características**:
  - Compatible con babel español
  - Nodos coloreados (azul=módulos, verde=bases de datos, amarillo=entrada, naranja=salida)
  - Flechas sólidas para flujo de procesamiento
  - Flechas punteadas para lectura/escritura de BD

**Cómo usar**:
```latex
\input{diagrams/pipeline-architecture}
```

#### `data-flow-simple.tex`
- **Uso**: Versión compacta del flujo de datos
- **Estado**: Disponible pero no integrado
- **Características**:
  - Más compacto que pipeline-architecture
  - Enfoque en flujo de datos más que en arquitectura completa

**Cómo usar**:
```latex
\input{diagrams/data-flow-simple}
```

### 2. Mermaid (Generar imágenes externamente)

#### `mermaid-diagrams.md`
- **Contiene**: 7 diagramas diferentes en código Mermaid
- **Diagramas incluidos**:
  1. Arquitectura del Pipeline (Vertical) - **RECOMENDADO**
  2. Arquitectura con Capas (Horizontal)
  3. Flujo de Datos Detallado
  4. Arquitectura de Módulos (Componentes C4)
  5. Diagrama de Secuencia (Flujo Completo)
  6. Diagrama de Estados del Job
  7. Diagrama ER Simplificado

**Cómo generar imágenes**:

1. Ve a https://mermaid.live/
2. Copia el código de un diagrama
3. Personaliza colores y estilos (opcional)
4. Exporta como PNG o SVG (alta resolución)
5. Guarda la imagen en `diagrams/`
6. Incluye en LaTeX:

```latex
\begin{figure}[H]
\centering
\includegraphics[width=0.8\textwidth]{diagrams/mi-diagrama.png}
\caption{Título del diagrama}
\label{fig:mi-diagrama}
\end{figure}
```

## Solución de Problemas TikZ

### Problema: Errores con babel español y TikZ

**Síntoma**: Errores como `I do not know the key '\par'` o problemas con `>` y `<`

**Solución**: Ya implementada en los archivos `.tex`:
```latex
\shorthandoff{>}\shorthandoff{<}
\begin{tikzpicture}
    % código del diagrama
\end{tikzpicture}
\shorthandon{>}\shorthandon{<}
```

### Problema: Librerías TikZ faltantes

**Solución**: Asegúrate de que `main.tex` incluye:
```latex
\usepackage{tikz}
\usetikzlibrary{shapes.geometric, arrows.meta, positioning, shadows, fit, shapes.multipart}
```

## Recomendaciones

### Para la tesis (documento formal):
✅ **Usar TikZ** - Los diagramas ya están integrados y compilando correctamente

### Para presentaciones o documentos externos:
✅ **Usar Mermaid** - Más fácil de modificar y generar rápidamente

### Para documentación técnica:
✅ **Usar Mermaid Diagrama 3** (Flujo de Datos Detallado) - Muestra los subprocesos

### Para arquitectura de software:
✅ **Usar Mermaid Diagrama 4** (C4 Components) - Vista de componentes clara

### Para explicar secuencia temporal:
✅ **Usar Mermaid Diagrama 5** (Secuencia) - Muestra el orden de ejecución

## Estado Actual

- ✅ TikZ compilando correctamente
- ✅ Integrado en Capítulo 5 (Diseño de la Solución)
- ✅ Compatible con babel español
- ✅ PDF generándose sin errores (62 páginas, 320KB)
- ✅ 7 diagramas Mermaid listos para usar

## Próximos Pasos (Opcional)

Si deseas agregar más diagramas profesionales al documento:

1. **Para módulos específicos**: Crear diagramas TikZ individuales para cada módulo (scraper, extractor, etc.)
2. **Para resultados**: Generar gráficos de resultados con matplotlib y exportar como PDF para incluir
3. **Para base de datos**: Usar el diagrama ER de Mermaid y exportar como imagen

## Créditos

- TikZ: Diagramas vectoriales nativos de LaTeX
- Mermaid: https://mermaid.live/
- Generados para: Observatorio de Demanda Laboral en América Latina
- Universidad: Pontificia Universidad Javeriana
