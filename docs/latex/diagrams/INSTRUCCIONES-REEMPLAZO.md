# 📋 Instrucciones para Reemplazar Diagramas TikZ con Imágenes Mermaid

## 🎯 Objetivo

Reemplazar los 3 diagramas TikZ (que tienen problemas de superposición) con imágenes PNG generadas desde Mermaid.

---

## 📝 Paso 1: Generar las Imágenes en Mermaid

### 1.1 Abrir Mermaid Live Editor
```
https://mermaid.live/
```

### 1.2 Generar Diagrama 1 (Arquitectura Completa)

1. Abre el archivo `MERMAID-PARA-USAR.md`
2. Copia el código del **Diagrama 1** (empieza con `%%{init:` y termina con las líneas `style M8...`)
3. Pégalo en mermaid.live
4. Click en **"Download PNG"** o **"Download SVG"**
5. Configuración recomendada:
   - Escala: **2x** o **3x** (alta resolución)
   - Fondo: **Blanco** (o transparent si prefieres)
6. Guarda el archivo como: `arquitectura-completa.png`

### 1.3 Generar Diagrama 2 (Arquitectura por Capas)

1. Copia el código del **Diagrama 2** desde `MERMAID-PARA-USAR.md`
2. Pégalo en mermaid.live (reemplaza el código anterior)
3. Download PNG (escala 2x-3x)
4. Guarda como: `arquitectura-capas.png`

### 1.4 Generar Diagrama 3 (Flujo de Transformación)

1. Copia el código del **Diagrama 3** desde `MERMAID-PARA-USAR.md`
2. Pégalo en mermaid.live
3. Download PNG (escala 2x-3x, este es horizontal así que puede ser más ancho)
4. Guarda como: `flujo-transformacion.png`

---

## 📂 Paso 2: Copiar las Imágenes al Proyecto

Coloca las 3 imágenes PNG en:
```
C:\Users\PcMaster\Documents\GitHub\observatorio-demanda-laboral\docs\latex\diagrams\
```

Deberías tener:
```
diagrams/
├── arquitectura-completa.png     ← NUEVA
├── arquitectura-capas.png         ← NUEVA
├── flujo-transformacion.png       ← NUEVA
├── arquitectura-completa.tex      (ya no se usará)
├── arquitectura-capas.tex         (ya no se usará)
└── flujo-transformacion.tex       (ya no se usará)
```

---

## ✏️ Paso 3: Actualizar el Capítulo 5

### 3.1 Abrir el archivo del capítulo
```
docs/latex/chapters/05-diseno-solucion.tex
```

### 3.2 Buscar y reemplazar las 3 secciones

#### REEMPLAZO 1: Vista Modular

**BUSCAR** (líneas ~30):
```latex
\input{diagrams/arquitectura-completa}
```

**REEMPLAZAR CON**:
```latex
\begin{figure}[p]
\centering
\includegraphics[width=0.95\textwidth]{diagrams/arquitectura-completa.png}
\caption{Arquitectura Modular Completa del Observatorio - Pipeline de 8 Etapas}
\label{fig:arquitectura-completa}
\end{figure}
```

---

#### REEMPLAZO 2: Vista por Capas

**BUSCAR** (líneas ~38):
```latex
\input{diagrams/arquitectura-capas}
```

**REEMPLAZAR CON**:
```latex
\begin{figure}[H]
\centering
\includegraphics[width=0.95\textwidth]{diagrams/arquitectura-capas.png}
\caption{Arquitectura en Capas del Sistema - Vista de Separación de Responsabilidades}
\label{fig:arquitectura-capas}
\end{figure}
```

---

#### REEMPLAZO 3: Vista de Transformación

**BUSCAR** (líneas ~46):
```latex
\input{diagrams/flujo-transformacion}
```

**REEMPLAZAR CON**:
```latex
\begin{figure}[H]
\centering
\includegraphics[width=0.98\textwidth]{diagrams/flujo-transformacion.png}
\caption{Flujo de Transformación de Datos a través del Pipeline}
\label{fig:flujo-transformacion}
\end{figure}
```

---

## 🔧 Paso 4: Verificar que graphicx está configurado

Abre `main.tex` y verifica que esta línea existe (debería estar alrededor de la línea 15):

```latex
\usepackage{graphicx}
```

Si ya existe, ¡perfecto! Si no, agrégala en la sección de paquetes.

---

## ⚙️ Paso 5: Compilar el Documento

### Opción 1: Script automático
```bash
cd docs/latex
./compile.bat
```

### Opción 2: Manual
```bash
cd docs/latex
pdflatex main.tex
biber main
pdflatex main.tex
pdflatex main.tex
```

---

## ✅ Paso 6: Verificar el Resultado

1. Abre `main.pdf`
2. Ve al Capítulo 5 (Diseño de la Solución)
3. Verifica que los 3 diagramas se vean correctamente:
   - ✅ Sin superposiciones
   - ✅ Texto legible
   - ✅ Colores correctos
   - ✅ Buena resolución

---

## 🎨 Ajustes Opcionales

### Si las imágenes se ven muy grandes:

Ajusta el `width` en el `\includegraphics`:

```latex
% Más pequeño
\includegraphics[width=0.85\textwidth]{...}

% Más grande
\includegraphics[width=1.0\textwidth]{...}

% Tamaño específico
\includegraphics[width=12cm]{...}
```

### Si quieres rotar una imagen:

```latex
\includegraphics[width=0.95\textwidth, angle=90]{diagrams/nombre.png}
```

### Si quieres que ocupe página completa:

Cambia `[H]` por `[p]` en el environment figure:

```latex
\begin{figure}[p]  % p = página completa dedicada
```

---

## 🐛 Solución de Problemas

### Problema: "File not found: arquitectura-completa.png"

**Solución**: Verifica que la ruta sea correcta. El archivo debe estar en:
```
docs/latex/diagrams/arquitectura-completa.png
```

Y en el código LaTeX debe ser:
```latex
\includegraphics{diagrams/arquitectura-completa.png}
```

---

### Problema: "Package pdftex.def Error: unknown image type"

**Solución**: Asegúrate de exportar como PNG desde mermaid.live, no como JPEG o WebP.

---

### Problema: Las imágenes se ven pixeladas

**Solución**: Re-exporta desde mermaid.live con mayor escala:
- En vez de escala 1x, usa 2x o 3x
- O exporta como SVG y convierte a PNG de alta resolución

---

### Problema: Las imágenes se salen del margen

**Solución**: Reduce el `width`:
```latex
\includegraphics[width=0.85\textwidth]{...}  % En vez de 0.95
```

---

## 📊 Comparación: TikZ vs Mermaid+PNG

| Aspecto | TikZ | Mermaid + PNG |
|---------|------|---------------|
| **Superposiciones** | ❌ Frecuentes | ✅ Ninguna |
| **Facilidad de edición** | ⚠️ Código complejo | ✅ Código simple |
| **Compilación LaTeX** | ⚠️ Lenta | ✅ Rápida |
| **Portabilidad** | ⚠️ Solo LaTeX | ✅ Cualquier documento |
| **Calidad visual** | ✅ Vectorial | ✅ Alta resolución PNG |
| **Debugging** | ❌ Difícil | ✅ Fácil (preview en vivo) |
| **Tiempo de creación** | ⚠️ 1-2 horas | ✅ 10-15 minutos |

---

## 📝 Resumen del Proceso

1. ✅ Generar 3 imágenes PNG en mermaid.live
2. ✅ Guardarlas en `docs/latex/diagrams/`
3. ✅ Editar `05-diseno-solucion.tex`
4. ✅ Reemplazar `\input{...}` por `\includegraphics{...}`
5. ✅ Compilar LaTeX
6. ✅ Verificar PDF

**Tiempo estimado**: 15-20 minutos

---

## 🎯 Resultado Esperado

Después de seguir estos pasos, tendrás:

✅ Capítulo 5 con 3 diagramas profesionales
✅ Sin problemas de superposición
✅ Alta calidad visual
✅ Fácil de modificar en el futuro
✅ Compilación LaTeX más rápida
✅ Portable (puedes usar las imágenes en presentaciones)

---

**¿Necesitas ayuda?**

Si encuentras algún problema siguiendo estos pasos, avísame y te ayudo a resolverlo.
