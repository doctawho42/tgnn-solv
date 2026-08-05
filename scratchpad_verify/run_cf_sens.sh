#!/bin/bash
cd /Users/nikitapolomosnov/PycharmProjects/tgnn-solv
export KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src
SP=/tmp/claude-501/-Users-nikitapolomosnov-PycharmProjects-tgnn-solv/d8c57c82-2aba-4a38-b6f5-83d49a35e42a/scratchpad
~/anaconda3/envs/tgnn-solv/bin/python scripts/analysis/run_b_insuff_crossfit_scoring.py --stage sens > $SP/cf_sens.txt 2>&1
echo "EXIT=$?" >> $SP/cf_sens.txt
