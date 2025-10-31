# Política de Tratamiento de Datos Personales

Este directorio contiene la Política de Tratamiento de Datos Personales del **Observatorio de Demanda Laboral en América Latina**.

## Descripción

La política establece los principios, procedimientos y derechos de los titulares de datos personales que puedan ser recolectados y tratados por el sistema del Observatorio. Este documento es fundamental para garantizar el cumplimiento de la normativa colombiana vigente en materia de protección de datos personales (Ley 1581 de 2012).

## Contenido del Documento

La política cubre los siguientes aspectos:

1. **Introducción**
   - Presentación del Observatorio
   - Objetivo de la política
   - Ámbito de aplicación
   - Responsable del tratamiento

2. **Marco Legal**
   - Legislación aplicable (Ley 1581/2012, Decreto 1377/2013)
   - Principios rectores del tratamiento de datos

3. **Responsable y Tipos de Datos**
   - Datos recopilados de ofertas de empleo públicas
   - Datos derivados del procesamiento (NLP, ESCO, embeddings)
   - Tratamiento de datos sensibles

4. **Finalidades y Derechos**
   - Análisis del mercado laboral
   - Investigación académica
   - Derechos de los titulares (ARCO)

5. **Seguridad y Transferencia**
   - Medidas de seguridad técnicas y administrativas
   - Política de transferencia de datos
   - Anonimización y agregación

6. **Revocatoria y Supresión**
   - Procedimientos de solicitud
   - Tiempos de respuesta

7. **Consultas y Reclamos**
   - Canales de contacto
   - Procedimientos de atención

8. **Vigencia y Almacenamiento**
   - Vigencia de la política
   - Periodo de conservación de datos
   - Procedimientos de eliminación segura

## Compilación

Para compilar el documento PDF desde el código LaTeX:

```bash
cd docs/politica-datos
pdflatex main.tex
pdflatex main.tex  # Segunda compilación para generar índice
```

## Archivos Generados

- `main.tex` - Código fuente LaTeX
- `main.pdf` - Documento PDF compilado
- `main.aux`, `main.log`, `main.out`, `main.toc` - Archivos auxiliares de compilación

## Información de Contacto

**Responsables:**
- Alejandro Pinzón Fajardo
- Nicolás Francisco Camacho Alarcón

**Institución:** Pontificia Universidad Javeriana
**Emails:** alejandro_pinzon@javeriana.edu.co | camachoa.nicolas@javeriana.edu.co
**Ubicación:** Bogotá D.C., Colombia

## Versión

- **Versión:** 1.0
- **Fecha:** Octubre 2025
- **Estado:** Documento activo

## Notas Importantes

- Este documento está adaptado específicamente para el proyecto del Observatorio
- Se basa en la normativa colombiana de protección de datos personales
- El sistema procesa principalmente información pública de ofertas de empleo
- Se implementan medidas de anonimización y agregación para proteger la privacidad
- El enfoque es exclusivamente académico y de investigación

## Actualizaciones

La política puede ser actualizada cuando sea necesario para adaptarse a:
- Cambios en la legislación vigente
- Nuevas funcionalidades del sistema
- Mejoras en las medidas de seguridad
- Modificaciones en las finalidades del proyecto
