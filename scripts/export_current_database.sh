#!/bin/bash
# Script para exportar la base de datos completa actualizada

set -e

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="data/backups"
BACKUP_FILE="${BACKUP_DIR}/labor_observatory_backup_${TIMESTAMP}.sql.gz"
EXPORT_DIR="data/exports"
EXPORT_CSV="${EXPORT_DIR}/ofertas_trabajo_${TIMESTAMP}.csv"
ZIP_FILE="${EXPORT_DIR}/ofertas_completas_${TIMESTAMP}.zip"

echo "============================================================"
echo "EXPORTADOR COMPLETO DE BASE DE DATOS"
echo "============================================================"
echo ""

# Crear directorios si no existen
mkdir -p "$BACKUP_DIR"
mkdir -p "$EXPORT_DIR"

# Opción 1: Backup completo de la base de datos
echo "Opción 1: Crear backup completo de PostgreSQL (.sql.gz)"
echo "Opción 2: Exportar solo tabla raw_jobs a CSV"
echo "Opción 3: Ambos (recomendado)"
echo ""
read -p "Selecciona opción (1/2/3): " OPTION

# Función para hacer backup completo
do_full_backup() {
    echo ""
    echo "📦 Creando backup completo de la base de datos..."

    docker exec observatorio-demanda-laboral-postgres-1 \
        pg_dump -U labor_user -d labor_observatory | gzip > "$BACKUP_FILE"

    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "✅ Backup completo creado: $BACKUP_FILE ($BACKUP_SIZE)"

    # Contar registros
    echo ""
    echo "📊 Contenido del backup:"
    docker exec observatorio-demanda-laboral-postgres-1 \
        psql -U labor_user -d labor_observatory -t -c "
        SELECT
            'raw_jobs: ' || COUNT(*) FROM raw_jobs
        UNION ALL
        SELECT 'cleaned_jobs: ' || COUNT(*) FROM cleaned_jobs
        UNION ALL
        SELECT 'esco_skills: ' || COUNT(*) FROM esco_skills
        UNION ALL
        SELECT 'extracted_skills: ' || COUNT(*) FROM extracted_skills;
    "
}

# Función para exportar CSV
do_csv_export() {
    echo ""
    echo "📄 Exportando ofertas de trabajo a CSV..."

    docker exec observatorio-demanda-laboral-postgres-1 \
        psql -U labor_user -d labor_observatory -c "\COPY (
            SELECT
                job_id,
                portal,
                country,
                title,
                company,
                location,
                job_type,
                salary,
                description,
                requirements,
                url,
                posted_date,
                scraped_at,
                metadata
            FROM raw_jobs
            ORDER BY scraped_at DESC
        ) TO STDOUT WITH CSV HEADER" > "$EXPORT_CSV"

    CSV_SIZE=$(du -h "$EXPORT_CSV" | cut -f1)
    CSV_LINES=$(wc -l < "$EXPORT_CSV")
    JOBS_COUNT=$((CSV_LINES - 1))  # Restar encabezado

    echo "✅ CSV creado: $EXPORT_CSV ($CSV_SIZE)"
    echo "   Ofertas exportadas: $JOBS_COUNT"
}

# Ejecutar según la opción seleccionada
case $OPTION in
    1)
        do_full_backup
        FILE_TO_ZIP="$BACKUP_FILE"
        ;;
    2)
        do_csv_export
        FILE_TO_ZIP="$EXPORT_CSV"
        ;;
    3)
        do_full_backup
        do_csv_export
        FILE_TO_ZIP="$BACKUP_FILE $EXPORT_CSV"
        ;;
    *)
        echo "Opción inválida. Saliendo..."
        exit 1
        ;;
esac

# Comprimir en ZIP
echo ""
echo "🗜️  Comprimiendo archivos en ZIP..."
cd "$(dirname "$ZIP_FILE")"
zip -j "$(basename "$ZIP_FILE")" $FILE_TO_ZIP
cd - > /dev/null

ZIP_SIZE=$(du -h "$ZIP_FILE" | cut -f1)

echo ""
echo "============================================================"
echo "✅ EXPORTACIÓN COMPLETA"
echo "============================================================"
echo "Archivo ZIP: $ZIP_FILE"
echo "Tamaño: $ZIP_SIZE"
echo ""
echo "Contenido:"
unzip -l "$ZIP_FILE"
echo ""
echo "🎉 Listo para enviar a tu compañero!"
echo "============================================================"
