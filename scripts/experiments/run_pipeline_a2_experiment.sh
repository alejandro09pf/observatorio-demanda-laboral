#!/bin/bash
# ==============================================================================
# Pipeline A.2 - Script Maestro de Ejecución
# ==============================================================================
#
# Este script ejecuta el experimento completo de N-gram matching:
# 1. Genera diccionario de n-gramas desde ESCO
# 2. Evalúa extractor contra gold standard (300 ofertas)
# 3. Genera reporte comparativo con Pipeline A y B
#
# Uso:
#   bash scripts/experiments/run_pipeline_a2_experiment.sh
#
# ==============================================================================

set -e  # Exit on error

echo "======================================================================"
echo "PIPELINE A.2 - EXPERIMENTO N-GRAM EXTRACTOR"
echo "======================================================================"
echo ""

# Configurar PYTHONPATH y usar venv
export PYTHONPATH="/Users/nicocamacho/Documents/Tesis/observatorio-demanda-laboral:$PYTHONPATH"
PYTHON="venv/bin/python3"

# Crear directorios necesarios
mkdir -p data/processed
mkdir -p outputs/evaluation

# ==============================================================================
# PASO 1: Generar Diccionario de N-gramas
# ==============================================================================

echo "📋 PASO 1/3: Generando diccionario de n-gramas desde ESCO..."
echo ""

$PYTHON scripts/experiments/generate_ngram_dictionary.py

if [ $? -ne 0 ]; then
    echo "❌ Error al generar diccionario de n-gramas"
    exit 1
fi

echo ""
echo "✅ Diccionario de n-gramas generado exitosamente"
echo ""
echo "----------------------------------------------------------------------"
echo ""

# ==============================================================================
# PASO 2: Probar Extractor con Ejemplo
# ==============================================================================

echo "📋 PASO 2/3: Probando extractor con ejemplo..."
echo ""

$PYTHON scripts/experiments/pipeline_a2_ngram_extractor.py

if [ $? -ne 0 ]; then
    echo "❌ Error al probar extractor"
    exit 1
fi

echo ""
echo "----------------------------------------------------------------------"
echo ""

# ==============================================================================
# PASO 3: Evaluar contra Gold Standard
# ==============================================================================

echo "📋 PASO 3/3: Evaluando contra gold standard (300 ofertas)..."
echo ""

$PYTHON scripts/experiments/evaluate_pipeline_a2.py

if [ $? -ne 0 ]; then
    echo "❌ Error al evaluar pipeline"
    exit 1
fi

echo ""
echo "======================================================================"
echo "✅ EXPERIMENTO COMPLETADO EXITOSAMENTE"
echo "======================================================================"
echo ""
echo "📂 Archivos generados:"
echo "   - data/processed/ngram_skill_dictionary.json"
echo "   - data/processed/ngram_dictionary_stats.json"
echo "   - outputs/evaluation/pipeline_a2_results.json"
echo "   - docs/PIPELINE_A2_NGRAMS_EXPERIMENT.md"
echo ""
echo "📖 Para ver el reporte completo:"
echo "   cat docs/PIPELINE_A2_NGRAMS_EXPERIMENT.md"
echo ""
