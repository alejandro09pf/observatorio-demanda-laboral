# src/scraper/settings.py

# Identifica tu scraper con un User-Agent legítimo y educativo
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AcademicResearchBot/1.0"

# Obedecer o no el archivo robots.txt
ROBOTSTXT_OBEY = False

# Descanso entre peticiones (en segundos)
DOWNLOAD_DELAY = 1.0

# Número máximo de peticiones concurrentes
CONCURRENT_REQUESTS = 16

# Codificación del archivo de salida
FEED_EXPORT_ENCODING = "utf-8"

# Tiempo máximo de espera para cada petición
DOWNLOAD_TIMEOUT = 20

# Activa el pipeline para almacenar en la base de datos (cuando lo configures)
ITEM_PIPELINES = {
    "scraper.pipelines.JobPostgresPipeline": 300,  # Ruta completa del pipeline
}

# Opcional: limitar profundidad (para evitar scraping infinito)
DEPTH_LIMIT = 10

# Configuración de logs
LOG_ENABLED = True
LOG_LEVEL = "INFO"

# Configuración de base de datos (reemplaza con tus credenciales)
DB_PARAMS = {
    "dbname": "labor_observatory",
    "user": "labor_user",
    "password": "your_password",
    "host": "localhost",
    "port": 5432,
}

# Configuración de Selenium (si luego lo usas)
SELENIUM_DRIVER_NAME = "chrome"
SELENIUM_DRIVER_EXECUTABLE_PATH = "drivers/chromedriver.exe"
SELENIUM_DRIVER_ARGUMENTS = ["--headless"]
