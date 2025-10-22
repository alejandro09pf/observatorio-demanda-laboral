#!/bin/bash
# Quick test of all scrapers (2 pages, 10 items each)

echo "====================================================================="
echo "TESTING ALL SCRAPERS - Quick Test (2 pages, 10-20 items each)"
echo "====================================================================="
echo ""

# Test Elempleo CO
echo "[1/6] Testing Elempleo CO..."
python -m src.orchestrator run-once elempleo -c CO -p 2 --limit 20 -v 2>&1 | tail -5
echo ""

# Test Bumeran AR
echo "[2/6] Testing Bumeran AR..."
python -m src.orchestrator run-once bumeran -c AR -p 2 --limit 10 -v 2>&1 | tail -5
echo ""

# Test ZonaJobs AR
echo "[3/6] Testing ZonaJobs AR..."
python -m src.orchestrator run-once zonajobs -c AR -p 2 --limit 10 -v 2>&1 | tail -5
echo ""

# Test Magneto CO
echo "[4/6] Testing Magneto CO..."
python -m src.orchestrator run-once magneto -c CO -p 2 --limit 10 -v 2>&1 | tail -5
echo ""

# Test Hiring Cafe MX
echo "[5/6] Testing Hiring Cafe MX..."
python -m src.orchestrator run-once hiring_cafe -c MX -p 2 --limit 10 -v 2>&1 | tail -5
echo ""

# Test Indeed MX
echo "[6/6] Testing Indeed MX..."
python -m src.orchestrator run-once indeed -c MX -p 1 --limit 5 -v 2>&1 | tail -5
echo ""

echo "====================================================================="
echo "ALL TESTS COMPLETED"
echo "====================================================================="
