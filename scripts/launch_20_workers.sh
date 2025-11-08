#!/bin/bash
# Launch 15 parallel workers to reprocess 30k jobs with Pipeline A Iter 9.1
# Reduced from 20 to 15 to avoid PostgreSQL connection pool exhaustion

echo "🚀 Launching 15 workers..."

for i in {0..14}; do
    venv/bin/python3 scripts/process_remaining_jobs.py $i 15 > /tmp/worker_${i}_final.log 2>&1 &
    echo "  Worker $((i+1))/15 launched (PID: $!)"
done

echo ""
echo "✅ All 15 workers launched!"
echo "📊 Est. time: ~40 minutes"
echo ""
echo "Monitor progress:"
echo "  tail -f /tmp/worker_0_final.log"
echo "  tail -f /tmp/worker_14_final.log"
echo ""
echo "Check running:"
echo "  ps aux | grep process_remaining_jobs.py | grep -v grep"
