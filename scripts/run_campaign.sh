#!/bin/bash
# 60-run LedgerBench campaign against local qwen3-coder-128k, with the layout fix. Skips arm/seed pairs already completed.
cd "$(dirname "$0")/.."
export LEDGERBENCH_BACKEND=openai OPENAI_BASE_URL=http://localhost:11434/v1 OPENAI_API_KEY=not-needed LEDGERBENCH_MODEL=qwen3-coder-128k
unset LEDGERBENCH_TASKS
export LEDGERBENCH_SHOW_LAYOUT=1   # protocol change: expose source file names (see REPRODUCE.md)
for arm in A B C C+ D; do
  for s in $(seq 1 12); do
    d="${arm/+/plus}"   # harness names C+ run dirs "Cplus"
    if grep -lq '"run_end"' runs/run_arm${d}_seed${s}_*/log.jsonl 2>/dev/null; then
      echo "$(date '+%F %T') SKIP arm=$arm seed=$s (done)"; continue
    fi
    rm -rf runs/run_arm${d}_seed${s}_*   # remove incomplete leftovers
    echo "$(date '+%F %T') START arm=$arm seed=$s"
    .venv/bin/python -m harness.run_pilot --arm "$arm" --seed "$s" > "logs/arm${arm}_seed${s}.out" 2>&1
    echo "$(date '+%F %T') END arm=$arm seed=$s exit=$?"
  done
done
echo "$(date '+%F %T') CAMPAIGN_DONE"
.venv/bin/python -m harness.analyze > logs/analyze.out 2>&1
echo "$(date '+%F %T') ANALYZE_DONE exit=$?"
