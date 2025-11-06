#!/bin/bash
#
# Launch 10 parallel workers to process remaining jobs.
# Worker 0 is already running (the original process).
# This script launches workers 1-10.
#

echo "=========================================="
echo "LAUNCHING 10 PARALLEL WORKERS"
echo "=========================================="
echo ""
echo "Worker 0: Already running (original process)"
echo "Workers 1-10: Launching now..."
echo ""

# Total workers (including the one already running)
TOTAL_WORKERS=11

# Launch workers 1-10 in background
for WORKER_ID in {1..10}
do
    LOG_FILE="/tmp/pipeline_worker_${WORKER_ID}.log"

    echo "🚀 Launching Worker ${WORKER_ID}/${TOTAL_WORKERS}..."
    echo "   Log: ${LOG_FILE}"

    # Launch worker in background
    nohup venv/bin/python3 scripts/process_parallel_worker.py $((WORKER_ID)) ${TOTAL_WORKERS} \
        > "${LOG_FILE}" 2>&1 &

    WORKER_PID=$!
    echo "   PID: ${WORKER_PID}"
    echo ""

    # Small delay to avoid overwhelming the system at startup
    sleep 2
done

echo "=========================================="
echo "✅ ALL 10 WORKERS LAUNCHED"
echo "=========================================="
echo ""
echo "📊 Monitor progress:"
echo "   tail -f /tmp/pipeline_worker_*.log"
echo ""
echo "📈 Check live stats:"
echo "   python scripts/monitor_parallel_progress.py"
echo ""
echo "🛑 Stop all workers:"
echo "   pkill -f process_parallel_worker.py"
echo ""
