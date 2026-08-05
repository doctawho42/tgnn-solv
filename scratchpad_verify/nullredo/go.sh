#!/bin/bash
cd /Users/nikitapolomosnov/PycharmProjects/tgnn-solv
export KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src
D=/private/tmp/claude-501/-Users-nikitapolomosnov-PycharmProjects-tgnn-solv/d8c57c82-2aba-4a38-b6f5-83d49a35e42a/scratchpad/nullredo
~/anaconda3/envs/tgnn-solv/bin/python $D/redo_null.py 2000 > $D/run.txt 2>&1
echo "EXIT=$?" >> $D/run.txt
touch $D/DONE
