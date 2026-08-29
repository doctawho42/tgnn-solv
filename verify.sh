#!/usr/bin/env bash
# Certify the repository in one command: the package, the manuscript, and every gate that binds a
# printed number to the artifact it came from.
#
# WHY THIS EXISTS.  These checks were run one at a time, from memory, in whatever order the last
# change suggested -- which is how the repository ended up with a public site five months stale, a
# retirement allowlist that had not parsed in weeks, and eight gates nobody ran together.  A check
# that has to be remembered is a check that is skipped.
#
#     ./verify.sh            everything
#     ./verify.sh fast       skip the test suite and the LaTeX builds (~10 s)
#
# Exit status is 0 only if every stage passes.  Each stage prints its own verdict; the summary at
# the end names what failed, because a wall of green with one red line in it reads as green.
set -uo pipefail
cd "$(dirname "$0")"

MODE="${1:-full}"
export KMP_DUPLICATE_LIB_OK=TRUE          # rdkit + torch + sklearn each ship their own libomp
export PYTHONPATH="src:${PYTHONPATH:-}"
PY="${PY:-python}"

FAILED=()
stage() {                                  # stage <name> <command...>
  local name="$1"; shift
  printf '%-46s' "  $name"
  if "$@" >/tmp/tgnn_verify_stage.out 2>&1; then
    echo "ok"
  else
    echo "FAIL"
    FAILED+=("$name")
    sed 's/^/      /' /tmp/tgnn_verify_stage.out | tail -12
  fi
}

echo "== package"
stage "imports" "$PY" -c "import tgnn_solv, tgnn_solv.model, tgnn_solv.layers, tgnn_solv.solver"
# BROKEN, NOT UNTIDY.  `ruff check` at its defaults reports 430 findings here, 98% of them style
# (semicolons, import position, lambda assignment) on working code, so gating on the total means a
# gate that is red forever and therefore never read.  F821 is the class that means the file cannot
# run: it found two live NameErrors on the UNIFAC-prior path that two committed configs enable, and
# it would have caught the missing `import signal` in the Kaggle runner the same day.  Widen this
# list when the style debt is actually paid, not before.
# Notebooks are excluded from F811 on purpose: a cell that re-imports json is normal notebook
# style, not a redefinition bug, and the only hit in this tree is exactly that.
stage "lint: undefined names (F821/F811)" \
      ruff check src tests scripts --select F821,F811 --exclude "*.ipynb"
# ONE INTERPRETER, NOT ONE PER FILE.  The first version spawned python once per tracked module and
# took over two minutes, which is long enough that the check gets skipped, which is the same as not
# having it.
stage "lint: syntax" "$PY" -c '
import subprocess, sys, py_compile, tempfile
files = subprocess.run(["git","ls-files","*.py"], capture_output=True, text=True).stdout.split()
bad = []
with tempfile.TemporaryDirectory() as d:
    for f in files:
        try:
            py_compile.compile(f, cfile=d+"/x.pyc", doraise=True)
        except py_compile.PyCompileError as e:
            bad.append(str(e))
print(f"{len(files)} modules compiled")
if bad:
    print("\n".join(bad[:10])); sys.exit(1)'
[ "$MODE" = fast ] || stage "test suite" "$PY" -m pytest tests/ -q --no-header

echo "== manuscript gates"
for g in check_hand_transcribed_displays check_deviation_paragraph check_vt2005_leverage_counts \
         check_donor_window_caption check_split_refs check_cross_document_attributions \
         check_no_scored_self_pairs; do
  stage "$g" "$PY" "scripts/analysis/$g.py"
done
stage "check_number_conservation" "$PY" scripts/analysis/check_number_conservation.py \
      --allowlist paper/retired_numbers.txt

echo "== documentation"
stage "check_doc_paths" "$PY" scripts/analysis/check_doc_paths.py
stage "check_site_abstract (title + abstract)" "$PY" scripts/analysis/check_site_abstract.py

echo "== figures"
# The journal's graphics specification, read off the produced PDFs. Not off the scripts:
# savefig(bbox="tight") is how a script that sets a width emits a different one, and that is
# exactly what six of these figures were doing.
stage "check_figure_spec" "$PY" scripts/analysis/check_figure_spec.py

if [ "$MODE" != fast ]; then
  echo "== manuscript builds"
  # TWICE EACH, AND SI FIRST.  The two documents cite each other through xr-hyper, which reads the
  # OTHER document's .aux at compile time, so a single pass in the wrong order prints a stale
  # cross-document number without warning -- and that is a table pointer nobody would re-check.
  stage "latex (SI, article, twice, xr fixed point)" bash -c '
    cd paper
    for pass in 1 2; do
      for f in grounding_paradox_si grounding_paradox; do
        xelatex -interaction=nonstopmode "$f.tex" >/dev/null 2>&1
      done
    done
    for f in grounding_paradox grounding_paradox_si; do
      grep -q "Rerun to get" "paper/$f.log" 2>/dev/null && { echo "$f: needs another pass"; exit 1; }
      n=$(grep -c "Reference .* undefined" "$f.log" 2>/dev/null || true)
      [ "${n:-0}" -gt 0 ] && { echo "$f: $n undefined references"; exit 1; }
    done
    exit 0'
fi

echo
if [ ${#FAILED[@]} -eq 0 ]; then
  echo "VERIFIED (${MODE})"
  exit 0
fi
echo "FAILED (${#FAILED[@]}): ${FAILED[*]}"
exit 1
