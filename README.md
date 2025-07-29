# Observatorio de Demanda Laboral en Latinoamérica

Este repositorio contiene el código y la estructura del sistema desarrollado como parte de una tesis de maestría. El sistema permite monitorear la demanda de habilidades técnicas en el mercado laboral latinoamericano mediante la recolección, análisis y visualización de ofertas de empleo publicadas en portales web.

## Objetivo del Proyecto

Diseñar e implementar un observatorio automatizado que identifique habilidades demandadas por país, sector y ocupación, apoyado en técnicas de procesamiento de lenguaje natural, aprendizaje automático y visualización de datos.

## Arquitectura General

El sistema está conformado por los siguientes módulos:

- Scraper: Recolecta ofertas de empleo desde portales como Computrabajo, Bumeran y ElEmpleo.
- Extractor: Utiliza NER, expresiones regulares y taxonomía ESCO para identificar habilidades explícitas.
- LLM Processor: Deduplica, infiere habilidades implícitas y normaliza términos utilizando modelos de lenguaje.
- Embedder: Vectoriza habilidades y perfiles utilizando modelos multilingües (E5/SBERT).
- Analyzer: Agrupa y analiza habilidades mediante técnicas de reducción de dimensionalidad y clustering.
- Visualización: Genera reportes estáticos (PDF, PNG, CSV).
- Orquestador: Coordina la ejecución de los módulos anteriores.

## Estructura del Repositorio

```
observatorio-demanda-laboral/
├── config/
├── src/
│   ├── scraper/
│   ├── extractor/
│   ├── llm_processor/
│   ├── embedder/
│   ├── analyzer/
│   ├── database/
│   ├── utils/
│   └── orchestrator.py
├── data/
├── outputs/
├── scripts/
├── tests/
├── docs/
├── notebooks/
├── requirements.txt
├── setup.py
├── docker-compose.yml
├── .env.example
├── .gitignore
├── LICENSE
└── README.md
```

## Instalación

### Requisitos

- Python 3.10 o superior
- PostgreSQL 15 con extensión pgvector
- Git
- Docker (opcional para despliegue automatizado)

### Pasos

1. Clonar el repositorio:

   ```bash
   git clone https://github.com/usuario/observatorio-demanda-laboral.git
   cd observatorio-demanda-laboral
   ```

2. Crear un entorno virtual e instalar dependencias:

   ```bash
   python -m venv venv
   venv\Scripts\activate         # En Windows
   pip install -r requirements.txt
   ```

3. Configurar las variables de entorno:

   Copiar el archivo `.env.example` a `.env` y completar los valores según tu entorno local.

4. Inicializar la base de datos:

   ```bash
   psql -U usuario -f src/database/migrations/001_initial_schema.sql
   ```

5. Ejecutar el pipeline:

   ```bash
   python src/orchestrator.py run --country CO --portal computrabajo
   ```

## Documentación

La documentación técnica del sistema se encuentra en la carpeta `docs/`:

- architecture.md: Descripción de la arquitectura general del sistema.
- setup_guide.md: Guía de instalación y configuración.
- api_reference.md: Referencia de funciones y módulos.
- troubleshooting.md: Solución de errores comunes.

## Licencia

Este proyecto se distribuye bajo la Licencia MIT. Consulte el archivo `LICENSE` para más información.

## Autor

Desarrollado por Alejandro Pinzon Fajardo y Nicolas Francisco Camacho Alarcon como parte del trabajo de grado en Ingeniería de Sistemas.  
Pontificia Universidad Javeriana, Colombia.
